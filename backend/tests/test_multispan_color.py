from pathlib import Path

from app.pipeline.stages.extract_text import ExtractTextStage
from app.pipeline.stages.generate_css import GenerateCssStage
from app.pipeline.stages.generate_html import GenerateHtmlStage
from app.pipeline.stages.normalize_idm import NormalizeIdmStage
from app.pipeline.stages.reconstruct_tree import ReconstructTreeStage
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
    ReconstructTreeStage().run(context)
    GenerateCssStage(page_repo, storage).run(context)
    GenerateHtmlStage(page_repo, storage).run(context)

    project_dir = storage.project_dir(context.project_id)
    html = (project_dir / "pages" / "page_0001.html").read_text(encoding="utf-8")

    # RIL contract: the base run (dominant style) is PLAIN TEXT styled by the
    # paragraph's own inline style; only the two runs whose color genuinely
    # differs become styled spans — each with its OWN complete inline style
    # (Rendering Stabilization phase: Style Registry bypassed, no classes).
    start = html.index('<p class="lf-paragraph')
    end = html.index("</p>", start) + len("</p>")
    fragment = html[start:end]
    assert fragment.count("<span style=") == 2
    assert 'class="lf-s' not in fragment
    assert "Blue" in fragment and "Black" in fragment and "Orange" in fragment
    colors_in_fragment = sum(c in fragment for c in ("#0000ff", "#000000", "#ff8000"))
    assert colors_in_fragment == 3
