from pathlib import Path

import pytest

from app.pipeline.outputs.html_output import HtmlOutputPlugin
from app.pipeline.outputs.html_validator import HtmlValidationError, HtmlValidator
from app.pipeline.stages.extract_fonts import ExtractFontsStage
from app.pipeline.stages.extract_images import ExtractImagesStage
from app.pipeline.stages.extract_text import ExtractTextStage
from app.pipeline.stages.generate_css import GenerateCssStage
from app.pipeline.stages.generate_html import GenerateHtmlStage
from app.pipeline.stages.normalize_idm import NormalizeIdmStage
from app.pipeline.stages.render_backgrounds import RenderBackgroundsStage
from tests.test_extraction import make_context_with_metadata


def run_full_extraction_and_css(context, storage, page_repo) -> None:
    RenderBackgroundsStage(storage, dpi=72).run(context)
    ExtractFontsStage(storage).run(context)
    ExtractImagesStage(storage).run(context)
    ExtractTextStage().run(context)
    NormalizeIdmStage().run(context)
    GenerateCssStage(page_repo, storage).run(context)


def test_html_output_writes_semantic_layered_pages(db_session, tmp_path: Path, rich_pdf_path: Path) -> None:
    context, storage, page_repo, _ = make_context_with_metadata(db_session, tmp_path, rich_pdf_path)
    run_full_extraction_and_css(context, storage, page_repo)

    generated = HtmlOutputPlugin(storage).generate(context)

    assert generated == [(1, "pages/page_0001.html"), (2, "pages/page_0002.html")]

    pages_dir = storage.project_dir(context.project_id) / "pages"
    html = (pages_dir / "page_0001.html").read_text(encoding="utf-8")

    # URLs are relative (../resources/...) so the project is self-contained
    # and renders identically from disk, served, or in an iframe.
    assert 'href="../resources/css/common.css"' in html
    assert 'href="../resources/css/page_0001.css"' in html
    assert 'class="lf-layer lf-layer-background"' in html
    assert 'class="lf-layer lf-layer-images"' in html
    assert 'class="lf-layer lf-layer-text"' in html
    assert 'data-type="background"' in html

    page_one = context.document.get_page(1)
    heading = next(b for b in page_one.text_blocks if b.text == "Page 1 heading")
    assert f'id="tb-{heading.id}"' in html
    # data-font is now the human-readable family name, not the UUID
    font = context.document.fonts[0] if context.document.fonts else None
    if font and heading.font_id == font.id:
        assert f'data-font="{font.family}"' in html
    else:
        assert 'data-font=' in html  # attribute exists; family name varies by fixture font
    # LTR text is word-pinned (typography Milestone 1): each word is its
    # own absolutely-placed <span class="lf-word"> rather than one inline
    # run — so the words appear individually, not as one "Page 1 heading".
    assert 'class="lf-word"' in html
    assert ">heading</span>" in html

    image = page_one.images[0]
    assert f'id="img-{image.id}"' in html
    assert f'data-asset="{image.asset_id}"' in html


def test_html_output_escapes_text_content(db_session, tmp_path: Path) -> None:
    from tests.conftest import make_rich_pdf_bytes

    pdf_path = tmp_path / "plain.pdf"
    pdf_path.write_bytes(make_rich_pdf_bytes(pages=1, with_image=False))
    context, storage, page_repo, _ = make_context_with_metadata(db_session, tmp_path, pdf_path)
    run_full_extraction_and_css(context, storage, page_repo)

    # Inject a value that would break the markup if not escaped. Rendering
    # reads from words (word-pinned) or spans (fallback) — set the payload
    # on whichever path this block will render through.
    malicious = '<script>alert("x")</script> & "quotes"'
    block = context.document.get_page(1).text_blocks[0]
    block.text = malicious
    if block.words:
        block.words[0].text = malicious
    else:
        block.spans[0].text = malicious

    HtmlOutputPlugin(storage).generate(context)

    html = (storage.project_dir(context.project_id) / "pages" / "page_0001.html").read_text(encoding="utf-8")
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_generate_html_stage_persists_page_html_path(db_session, tmp_path: Path, rich_pdf_path: Path) -> None:
    context, storage, page_repo, _ = make_context_with_metadata(db_session, tmp_path, rich_pdf_path)
    run_full_extraction_and_css(context, storage, page_repo)

    GenerateHtmlStage(page_repo, storage).run(context)

    pages = {p.page_number: p for p in page_repo.list_by_project(context.project_id)}
    assert pages[1].html_path == "pages/page_0001.html"
    assert pages[2].html_path == "pages/page_0002.html"


def test_html_validator_catches_duplicate_ids(tmp_path: Path) -> None:
    html = '<div id="dup">a</div><div id="dup">b</div>'
    with pytest.raises(HtmlValidationError, match="Duplicate element ids"):
        HtmlValidator().validate(html, tmp_path)


def test_html_validator_catches_missing_referenced_file(tmp_path: Path) -> None:
    html = '<img src="does-not-exist.png" alt="">'
    with pytest.raises(HtmlValidationError, match="Missing referenced file"):
        HtmlValidator().validate(html, tmp_path)


def test_html_validator_passes_clean_html(tmp_path: Path) -> None:
    (tmp_path / "exists.png").write_bytes(b"fake")
    html = '<div id="a">x</div><img src="exists.png" alt="">'
    HtmlValidator().validate(html, tmp_path)  # should not raise
