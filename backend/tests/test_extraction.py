from pathlib import Path
from unittest.mock import patch

import fitz
import pytest

from app.core.config import Settings
from app.pipeline.context import PipelineContext
from app.pipeline.stages.extract_fonts import ExtractFontsStage
from app.pipeline.stages.extract_images import ExtractImagesStage
from app.pipeline.stages.extract_text import ExtractTextStage
from app.pipeline.stages.metadata import MetadataStage
from app.pipeline.stages.normalize_idm import NormalizeIdmStage
from app.pipeline.stages.persist_assets import PersistAssetsStage
from app.pipeline.stages.render_backgrounds import RenderBackgroundsStage
from app.repositories.sqlite.asset_repository import SQLiteAssetRepository
from app.repositories.sqlite.page_repository import SQLitePageRepository
from app.repositories.sqlite.project_repository import SQLiteProjectRepository
from app.services.storage_service import StorageService
from tests.conftest import make_empty_page_pdf_bytes, make_rich_pdf_bytes


def make_context_with_metadata(db_session, tmp_path: Path, pdf_path: Path, project_id: str = "proj-1"):
    settings = Settings(storage_root=tmp_path)
    storage = StorageService(settings)
    storage.ensure_project_dirs(project_id)
    page_repo = SQLitePageRepository(db_session)
    project_repo = SQLiteProjectRepository(db_session)
    from app.models.project import Project

    project_repo.create(Project(id=project_id, name="Test", filename="test.pdf", page_count=0))

    context = PipelineContext(
        job_id="job-1", project_id=project_id, source_pdf_path=pdf_path, output_dir=storage.project_dir(project_id)
    )
    MetadataStage(page_repo, project_repo).run(context)
    return context, storage, page_repo, project_repo


def test_render_backgrounds_writes_png_per_page(db_session, tmp_path: Path, rich_pdf_path: Path) -> None:
    context, storage, *_ = make_context_with_metadata(db_session, tmp_path, rich_pdf_path)

    RenderBackgroundsStage(storage, dpi=72).run(context)

    assert len(context.document.assets) == 2
    for page in context.document.pages:
        assert page.background_image is not None
        assert (storage.project_dir(context.project_id) / page.background_image).exists()


def test_extract_fonts_finds_used_fonts(db_session, tmp_path: Path, rich_pdf_path: Path) -> None:
    context, storage, *_ = make_context_with_metadata(db_session, tmp_path, rich_pdf_path)

    ExtractFontsStage(storage).run(context)

    assert len(context.document.fonts) >= 1
    assert all(font.family for font in context.document.fonts)
    page_one = context.document.get_page(1)
    assert len(page_one.fonts_used) >= 1
    assert "font_id_by_name" in context.scratch


def test_extract_images_dedupes_by_hash_across_pages(db_session, tmp_path: Path) -> None:
    # The same image is inserted on both pages, so it must collapse to a
    # single AssetResource referenced by both page numbers.
    pdf_path = tmp_path / "shared_image.pdf"
    pdf_path.write_bytes(make_rich_pdf_bytes(pages=2, with_image=True))
    context, storage, *_ = make_context_with_metadata(db_session, tmp_path, pdf_path)

    ExtractImagesStage(storage).run(context)

    image_assets = [a for a in context.document.assets if a.type == "image"]
    assert len(image_assets) == 1
    assert sorted(image_assets[0].referenced_pages) == [1, 2]
    assert len(context.document.get_page(1).images) == 1
    assert len(context.document.get_page(2).images) == 1


def test_extract_text_produces_text_blocks_with_geometry(db_session, tmp_path: Path, rich_pdf_path: Path) -> None:
    context, storage, *_ = make_context_with_metadata(db_session, tmp_path, rich_pdf_path)
    ExtractFontsStage(storage).run(context)  # populates font_id_by_name used for resolution

    ExtractTextStage().run(context)

    page_one = context.document.get_page(1)
    assert len(page_one.text_blocks) == 2
    texts = {block.text for block in page_one.text_blocks}
    assert "Page 1 heading" in texts
    assert any(block.bbox.width > 0 and block.bbox.height > 0 for block in page_one.text_blocks)
    assert all(block.color.startswith("#") for block in page_one.text_blocks)
    assert all(block.font_id is not None for block in page_one.text_blocks)
    # origin/ascender/descender are required to position text by baseline
    # rather than box-top alone (see Layout Accuracy investigation) — must
    # be the real PyMuPDF span values, not the dataclass defaults.
    heading = next(b for b in page_one.text_blocks if b.text == "Page 1 heading")
    assert heading.origin_x > 0
    assert heading.origin_y > 0
    assert heading.ascender > 0
    assert heading.descender < 0


def test_extract_text_on_empty_page_yields_no_blocks(db_session, tmp_path: Path) -> None:
    pdf_path = tmp_path / "empty.pdf"
    pdf_path.write_bytes(make_empty_page_pdf_bytes(pages=1))
    context, storage, *_ = make_context_with_metadata(db_session, tmp_path, pdf_path)

    ExtractTextStage().run(context)

    assert context.document.get_page(1).text_blocks == []


def test_extract_handles_rotated_page(db_session, tmp_path: Path) -> None:
    pdf_path = tmp_path / "rotated.pdf"
    pdf_path.write_bytes(make_rich_pdf_bytes(pages=1, with_image=False, rotation=90))
    context, storage, *_ = make_context_with_metadata(db_session, tmp_path, pdf_path)

    assert context.document.get_page(1).rotation == 90

    ExtractFontsStage(storage).run(context)
    ExtractTextStage().run(context)

    assert len(context.document.get_page(1).text_blocks) == 2


def test_normalize_idm_assigns_reading_order_and_line_height(db_session, tmp_path: Path, rich_pdf_path: Path) -> None:
    context, storage, *_ = make_context_with_metadata(db_session, tmp_path, rich_pdf_path)
    ExtractFontsStage(storage).run(context)
    ExtractTextStage().run(context)

    NormalizeIdmStage().run(context)

    page_one = context.document.get_page(1)
    orders = [block.reading_order for block in page_one.text_blocks]
    assert orders == sorted(orders)
    assert all(block.line_height > 0 for block in page_one.text_blocks)
    # heading (inserted at y=80) must read before body copy (inserted at y=120)
    sorted_texts = [b.text for b in sorted(page_one.text_blocks, key=lambda b: b.reading_order)]
    assert sorted_texts[0] == "Page 1 heading"

    # line_height must come from the font's real ascender/descender metrics
    # (not the flat font_size*1.2 guess) whenever they're available.
    heading = next(b for b in page_one.text_blocks if b.text == "Page 1 heading")
    expected = round((heading.ascender - heading.descender) * heading.font_size, 2)
    assert heading.line_height == expected


def test_persist_assets_deduplicates_against_existing_db_row(db_session, tmp_path: Path, rich_pdf_path: Path) -> None:
    context, storage, page_repo, project_repo = make_context_with_metadata(db_session, tmp_path, rich_pdf_path)
    asset_repo = SQLiteAssetRepository(db_session)

    RenderBackgroundsStage(storage, dpi=72).run(context)
    ExtractFontsStage(storage).run(context)
    ExtractImagesStage(storage).run(context)
    ExtractTextStage().run(context)
    NormalizeIdmStage().run(context)
    PersistAssetsStage(asset_repo, page_repo, storage).run(context)

    assets = asset_repo.list_by_project(context.project_id)
    image_assets = [a for a in assets if a.type.value == "image"]
    # 2 page backgrounds + 1 deduplicated embedded image
    assert len(image_assets) == 3

    shared_image = next(a for a in image_assets if a.original_object_id is not None)
    assert sorted(asset_repo.list_pages_for_asset(shared_image.id)) == [1, 2]

    # The IDM must be loadable from disk without the PDF.
    reloaded = storage.load_idm(context.project_id)
    assert len(reloaded.pages) == 2
    assert reloaded.get_page(1).text_blocks[0].text


def test_extract_fonts_registers_both_subset_and_stripped_name(db_session, tmp_path: Path, rich_pdf_path: Path) -> None:
    # PyMuPDF's get_fonts() returns the subset-prefixed basefont (e.g.
    # "ABCDEF+SomeFont"), but get_text("dict") span names strip that prefix
    # (e.g. "SomeFont") -- the registry must resolve either form, or
    # ExtractTextStage can never match a real-world subsetted/embedded font.
    context, storage, *_ = make_context_with_metadata(db_session, tmp_path, rich_pdf_path)

    fake_font_tuple = (999, "ttf", "TrueType", "ABCDEF+SomeFont", "TT0", "WinAnsiEncoding")

    with patch.object(fitz.Page, "get_fonts", return_value=[fake_font_tuple]):
        with patch.object(fitz.Document, "extract_font", return_value=("SomeFont", "ttf", "TrueType", b"")):
            ExtractFontsStage(storage).run(context)

    registry = context.scratch["font_id_by_name"]
    assert "ABCDEF+SomeFont" in registry
    assert "SomeFont" in registry
    assert registry["ABCDEF+SomeFont"] == registry["SomeFont"]


def test_corrupt_page_in_text_extraction_does_not_abort_other_pages(
    db_session, tmp_path: Path, rich_pdf_path: Path
) -> None:
    context, storage, *_ = make_context_with_metadata(db_session, tmp_path, rich_pdf_path)

    real_get_text = fitz.Page.get_text
    call_count = {"n": 0}

    def flaky_get_text(self, *args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated corrupt page")
        return real_get_text(self, *args, **kwargs)

    with patch.object(fitz.Page, "get_text", flaky_get_text):
        ExtractTextStage().run(context)

    # Page 1's extraction blew up and was skipped; page 2 still got processed.
    assert context.document.get_page(1).text_blocks == []
    assert len(context.document.get_page(2).text_blocks) == 2
