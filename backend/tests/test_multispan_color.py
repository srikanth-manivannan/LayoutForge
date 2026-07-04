from pathlib import Path

from app.pipeline.stages.extract_text import ExtractTextStage
from app.pipeline.stages.generate_css import GenerateCssStage
from app.pipeline.stages.generate_html import GenerateHtmlStage
from app.pipeline.stages.normalize_idm import NormalizeIdmStage
from tests.conftest import make_multicolor_line_pdf_bytes
from tests.test_extraction import make_context_with_metadata


def test_extract_text_preserves_per_span_color_within_one_line(db_session, tmp_path: Path) -> None:
    pdf_path = tmp_path / "multicolor.pdf"
    pdf_path.write_bytes(make_multicolor_line_pdf_bytes())
    context, storage, *_ = make_context_with_metadata(db_session, tmp_path, pdf_path)

    ExtractTextStage().run(context)

    page_one = context.document.get_page(1)
    assert len(page_one.text_blocks) == 1
    block = page_one.text_blocks[0]

    # The whole line's concatenated text is preserved at the block level...
    assert block.text == "Blue Black Orange"
    # ...but the real bug was collapsing every span's color to the first
    # span's color. Each run's own color must survive independently.
    assert len(block.spans) == 3
    colors = [span.color for span in block.spans]
    assert colors == ["#0000ff", "#000000", "#ff8000"]
    assert [span.text for span in block.spans] == ["Blue ", "Black ", "Orange"]


def test_generated_html_renders_one_span_per_color_run(db_session, tmp_path: Path) -> None:
    pdf_path = tmp_path / "multicolor.pdf"
    pdf_path.write_bytes(make_multicolor_line_pdf_bytes())
    context, storage, page_repo, _ = make_context_with_metadata(db_session, tmp_path, pdf_path)

    ExtractTextStage().run(context)
    NormalizeIdmStage().run(context)
    GenerateCssStage(page_repo, storage).run(context)
    GenerateHtmlStage(page_repo, storage).run(context)

    html = (storage.project_dir(context.project_id) / "pages" / "page_0001.html").read_text(encoding="utf-8")

    assert html.count("<span") == 3
    assert 'color: #0000ff' in html
    assert 'color: #000000' in html
    assert 'color: #ff8000' in html
    # All three colors must appear inside the SAME <p> (one TextBlock),
    # not collapsed to a single color for the whole line.
    p_start = html.index("<p ")
    p_end = html.index("</p>") + len("</p>")
    paragraph = html[p_start:p_end]
    assert paragraph.count("<span") == 3
