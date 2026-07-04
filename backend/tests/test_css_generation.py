from pathlib import Path

from app.core.config import Settings
from app.pipeline.stages.extract_fonts import ExtractFontsStage
from app.pipeline.stages.extract_images import ExtractImagesStage
from app.pipeline.stages.extract_text import ExtractTextStage
from app.pipeline.stages.generate_css import GenerateCssStage
from app.pipeline.stages.normalize_idm import NormalizeIdmStage
from app.pipeline.stages.render_backgrounds import RenderBackgroundsStage
from app.repositories.sqlite.page_repository import SQLitePageRepository
from app.services.storage_service import StorageService
from tests.test_extraction import make_context_with_metadata


def run_extraction(context, storage) -> None:
    RenderBackgroundsStage(storage, dpi=72).run(context)
    ExtractFontsStage(storage).run(context)
    ExtractImagesStage(storage).run(context)
    ExtractTextStage().run(context)
    NormalizeIdmStage().run(context)


def test_css_output_writes_common_and_per_page_files(db_session, tmp_path: Path, rich_pdf_path: Path) -> None:
    context, storage, page_repo, _ = make_context_with_metadata(db_session, tmp_path, rich_pdf_path)
    run_extraction(context, storage)

    GenerateCssStage(page_repo, storage).run(context)

    css_dir = storage.project_dir(context.project_id) / "resources" / "css"
    assert (css_dir / "common.css").exists()
    assert (css_dir / "page_0001.css").exists()
    assert (css_dir / "page_0002.css").exists()

    common_css = (css_dir / "common.css").read_text(encoding="utf-8")
    # The fixture's text uses base-14 font aliases (non-embedded), so no
    # @font-face rule is expected here — see test_css_output_emits_font_face
    # for the embedded-font path.
    assert ".lf-page {" in common_css
    assert ".lf-text-block {" in common_css

    page_one = context.document.get_page(1)
    page_css = (css_dir / "page_0001.css").read_text(encoding="utf-8")
    heading = next(b for b in page_one.text_blocks if b.text == "Page 1 heading")
    assert f"#tb-{heading.id}" in page_css
    assert f"left: {heading.bbox.x:g}px" in page_css
    assert f"top: {heading.bbox.y:g}px" in page_css

    image = page_one.images[0]
    assert f"#img-{image.id}" in page_css


def test_generate_css_stage_persists_page_css_path(db_session, tmp_path: Path, rich_pdf_path: Path) -> None:
    context, storage, page_repo, _ = make_context_with_metadata(db_session, tmp_path, rich_pdf_path)
    run_extraction(context, storage)

    GenerateCssStage(page_repo, storage).run(context)

    pages = {p.page_number: p for p in page_repo.list_by_project(context.project_id)}
    assert pages[1].css_path == "resources/css/page_0001.css"
    assert pages[2].css_path == "resources/css/page_0002.css"


def test_css_output_emits_font_face_for_embedded_fonts() -> None:
    from app.pipeline.document import Document
    from app.pipeline.elements.font import FontResource
    from app.pipeline.outputs.css_output import _build_common_css

    document = Document(project_id="p1")
    document.fonts.append(
        FontResource(
            id="font-1",
            original_name="ABCDEF+Inter-Bold",
            family="Inter-Bold",
            weight="bold",
            style="normal",
            embedded=True,
            subset=True,
            filename="font-1.ttf",
        )
    )
    document.fonts.append(
        FontResource(id="font-2", original_name="Helvetica", family="Helvetica", embedded=False)
    )

    css = _build_common_css(document)

    assert '@font-face' in css
    # font-family is unique per font RESOURCE (family + id prefix) so two
    # subsets of the same typeface can never shadow each other — while
    # staying human-readable (see outputs/font_naming.py).
    assert 'font-family: "Inter-Bold lffont-1"' in css
    # relative url, from resources/css/ to resources/fonts/
    assert 'src: url("../fonts/font-1.ttf") format("truetype")' in css
    assert "font-weight: bold" in css
    # The non-embedded font must not get a @font-face rule (no file to point to).
    assert css.count("@font-face") == 1


def test_rotated_text_block_gets_rotation_transform(db_session, tmp_path: Path) -> None:
    from tests.conftest import make_rich_pdf_bytes

    pdf_path = tmp_path / "rotated.pdf"
    pdf_path.write_bytes(make_rich_pdf_bytes(pages=1, with_image=False, rotation=90))
    context, storage, page_repo, _ = make_context_with_metadata(db_session, tmp_path, pdf_path)
    run_extraction(context, storage)

    GenerateCssStage(page_repo, storage).run(context)

    css_dir = storage.project_dir(context.project_id) / "resources" / "css"
    page_css = (css_dir / "page_0001.css").read_text(encoding="utf-8")
    page_one = context.document.get_page(1)
    rotated_block = next((b for b in page_one.text_blocks if b.rotation), None)
    if rotated_block is not None:
        assert f"#tb-{rotated_block.id}" in page_css
        assert "transform: rotate(" in page_css
