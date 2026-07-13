"""ReconstructTreeStage (Phase 2): builds page.regions in parallel with the
legacy text_blocks and guarantees no character is lost model→model."""

import pytest

from app.pipeline.context import PipelineContext
from app.pipeline.document import Document
from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.page import Page
from app.pipeline.elements.textbox import TextBlock, TextSpan
from app.pipeline.stages.reconstruct_tree import ReconstructTreeStage


def _context_with_page(blocks: list[TextBlock], fonts: list[FontResource]) -> PipelineContext:
    page = Page(number=1, width=600.0, height=800.0, text_blocks=blocks)
    doc = Document(project_id="p1", pages=[page], fonts=fonts)
    ctx = PipelineContext(job_id="j1", project_id="p1", source_pdf_path=None, output_dir=None)
    ctx.document = doc
    return ctx


def _block(text: str, y: float, spans: list[TextSpan]) -> TextBlock:
    return TextBlock(
        id=f"b-{y}",
        page=1,
        bbox=BoundingBox(x=50.0, y=y, width=300.0, height=12.0),
        text=text,
        origin_y=y + 10.0,
        line_height=14.0,
        font_size=12.0,
        spans=spans,
    )


def test_stage_populates_regions_and_preserves_characters() -> None:
    fonts = [FontResource(id="f1", original_name="Arial", family="Arial")]
    blocks = [
        _block("Hello world", 100.0, [TextSpan(text="Hello world", font_id="f1", font_size=12.0, color="#000")]),
        _block("second line", 114.0, [TextSpan(text="second line", font_id="f1", font_size=12.0, color="#000")]),
    ]
    ctx = _context_with_page(blocks, fonts)
    ReconstructTreeStage().run(ctx)

    page = ctx.document.get_page(1)
    assert page.regions, "tree must be populated in parallel"
    tree_text = "".join(
        run.text
        for region in page.regions
        for paragraph in region.paragraphs
        for line in paragraph.lines
        for run in line.runs
    )
    assert tree_text == "Hello worldsecond line"  # every character survived
    # legacy model is untouched
    assert [b.text for b in page.text_blocks] == ["Hello world", "second line"]


def test_stage_raises_if_a_builder_loses_characters(monkeypatch) -> None:
    """The strict-pipeline gate: a builder that drops text fails loudly."""
    fonts = [FontResource(id="f1", original_name="Arial", family="Arial")]
    blocks = [_block("keepme", 100.0, [TextSpan(text="keepme", font_id="f1", font_size=12.0, color="#000")])]
    ctx = _context_with_page(blocks, fonts)

    import app.pipeline.stages.reconstruct_tree as mod

    real_build = mod.build_paragraphs

    def _lossy(lines, fonts_by_id=None):
        paras = real_build(lines, fonts_by_id)
        for p in paras:  # simulate a bug that truncates run text
            for line in p.lines:
                for run in line.runs:
                    run.text = run.text[:-2]
        return paras

    monkeypatch.setattr(mod, "build_paragraphs", _lossy)
    with pytest.raises(ValueError, match="lost characters"):
        ReconstructTreeStage().run(ctx)
