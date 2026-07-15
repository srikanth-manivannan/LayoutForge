from pathlib import Path

from app.core.config import Settings
from app.pipeline.stages.extract_fonts import ExtractFontsStage
from app.pipeline.stages.extract_images import ExtractImagesStage
from app.pipeline.stages.extract_text import ExtractTextStage
from app.pipeline.stages.generate_css import GenerateCssStage
from app.pipeline.stages.normalize_idm import NormalizeIdmStage
from app.pipeline.stages.reconstruct_tree import ReconstructTreeStage
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
    ReconstructTreeStage().run(context)  # RIL consumes the Rich IDM tree


def test_css_output_writes_common_and_per_page_files(db_session, tmp_path: Path, rich_pdf_path: Path) -> None:
    context, storage, page_repo, _ = make_context_with_metadata(db_session, tmp_path, rich_pdf_path)
    run_extraction(context, storage)

    GenerateCssStage(page_repo, storage).run(context)

    css_dir = storage.project_dir(context.project_id) / "resources" / "css"
    assert (css_dir / "common.css").exists()
    assert (css_dir / "page_0001.css").exists()
    assert (css_dir / "page_0002.css").exists()

    common_css = (css_dir / "common.css").read_text(encoding="utf-8")
    assert ".lf-page {" in common_css
    # RIL DOM base rules replace the legacy .lf-text-block.
    assert ".lf-paragraph {" in common_css
    assert ".lf-line {" in common_css  # Line Layout Engine (2026-07-15): lines are their own DOM element
    assert ".lf-text-block" not in common_css

    # Text geometry/styles moved to the Render Tree (inline geometry +
    # registry classes) — per-block #tb rules are retired.
    page_css = (css_dir / "page_0001.css").read_text(encoding="utf-8")
    assert "#tb-" not in page_css

    page_one = context.document.get_page(1)
    image = page_one.images[0]
    assert f"#img-{image.id}" in page_css

    # The CSS plugin built + validated the Render Trees and left them in
    # scratch for the HTML compiler. Rendering Stabilization phase: no
    # Style Registry — every element gets a complete inline style instead.
    assert set(context.scratch["ril_trees"].keys()) == {1, 2}
    assert "ril_style_registry" not in context.scratch


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


def test_paragraph_white_space_never_lets_the_browser_add_its_own_wrap() -> None:
    """2026-07-14: `.lf-paragraph` must be `white-space: pre`, not
    `pre-wrap`. Every real line break is now an explicit `\\n` placed at the
    PDF's own line boundary (render_tree.py); `pre-wrap` additionally let
    the browser introduce an UNINTENDED extra wrap whenever a line's actual
    glyph advances came out even slightly wider than its PDF-measured box
    (found on a real book: a single-line cover title wrapped into two lines
    from a ~2px font-hinting difference). `pre` preserves the same spacing/
    breaks but can never add a wrap point of its own."""
    from app.pipeline.document import Document
    from app.pipeline.outputs.css_output import _build_common_css

    css = _build_common_css(Document(project_id="p1"))
    assert "white-space: pre;" in css
    assert "pre-wrap" not in css


def test_no_typography_registry_classes_land_in_common_css(db_session, tmp_path: Path) -> None:
    """Rendering Stabilization phase (temporary, 2026-07-13): the Style
    Registry is bypassed — common.css carries only structural rules
    (page/region/paragraph mechanics, @font-face), never per-style dedup
    classes. Every element's typography is inline (see test_ril.py)."""
    from tests.conftest import make_multicolor_line_pdf_bytes

    pdf_path = tmp_path / "multicolor.pdf"
    pdf_path.write_bytes(make_multicolor_line_pdf_bytes())
    context, storage, page_repo, _ = make_context_with_metadata(db_session, tmp_path, pdf_path)
    run_extraction(context, storage)

    GenerateCssStage(page_repo, storage).run(context)

    common_css = (storage.project_dir(context.project_id) / "resources" / "css" / "common.css").read_text(encoding="utf-8")
    assert "Style Registry" not in common_css
    assert ".lf-p0" not in common_css
    assert ".lf-r0" not in common_css and ".lf-r1" not in common_css


def test_rotated_line_gets_rotation_transform(db_session, tmp_path: Path) -> None:
    from tests.conftest import make_rich_pdf_bytes

    pdf_path = tmp_path / "rotated.pdf"
    pdf_path.write_bytes(make_rich_pdf_bytes(pages=1, with_image=False, rotation=90))
    context, storage, page_repo, _ = make_context_with_metadata(db_session, tmp_path, pdf_path)
    run_extraction(context, storage)

    GenerateCssStage(page_repo, storage).run(context)

    page_one = context.document.get_page(1)
    rotated_block = next((b for b in page_one.text_blocks if b.rotation), None)
    if rotated_block is not None:
        # Rotation now lives on the Render Tree's line geometry (decided in
        # the Instruction Builder, emitted inline by the compiler) — every
        # line is absolute now, rotated or not, so this is just an
        # alternate geometry dict on the same node (2026-07-15b).
        tree = context.scratch["ril_trees"][1]  # page -> region -> paragraph -> line
        rotated = [
            line
            for region in tree.children
            for para in region.children
            for line in para.children
            if "transform" in line.geometry
        ]
        assert rotated, "rotated line must carry a rotate() transform in its geometry"
        assert any("rotate(" in line.geometry["transform"] for line in rotated)
