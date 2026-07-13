"""Semantic HTML writer (Phase 3): the renderer as a compiler over the Rich
IDM. Verifies the Region→Paragraph→Line→Run→Text hierarchy, span minimization
(plain text when a run matches the paragraph base; <span> only on a real style
change), text coalescing, CSS dedup, stable ids, and the fidelity gate."""

import pytest

from app.pipeline.document import Document
from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.page import Page
from app.pipeline.elements.textbox import TextBlock, TextSpan
from app.pipeline.outputs.writers.context import FeatureFlags, Target, WriterContext
from app.pipeline.outputs.writers.html_writer import HtmlFidelityError, HtmlWriter
from app.pipeline.outputs.writers.render_engine import RenderEngine, UnsupportedTargetError
from app.pipeline.typography.line_builder import build_line
from app.pipeline.typography.paragraph_builder import build_paragraphs
from app.pipeline.typography.region_builder import build_regions


def _font(fid: str, name: str, weight: str = "normal", style: str = "normal") -> FontResource:
    return FontResource(id=fid, original_name=name, family=name, weight=weight, style=style)


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


def _document(blocks: list[TextBlock], fonts: list[FontResource]) -> Document:
    fonts_by_id = {f.id: f for f in fonts}
    lines = [build_line(b, i, fonts_by_id) for i, b in enumerate(blocks)]
    paras = build_paragraphs(lines, fonts_by_id)
    page = Page(number=1, width=600.0, height=800.0, text_blocks=blocks, regions=build_regions(paras))
    return Document(project_id="p", pages=[page], fonts=fonts)


def _render(doc: Document, flags: FeatureFlags | None = None) -> str:
    ctx = WriterContext.create(doc, target=Target.HTML, flags=flags)
    return RenderEngine().render(ctx).pages[0][1]


def test_uniform_paragraph_emits_no_run_spans() -> None:
    fonts = [_font("f1", "Arial")]
    doc = _document([_block("Hello world", 100.0, [TextSpan(text="Hello world", font_id="f1", font_size=12.0, color="#000000")])], fonts)
    html = _render(doc)
    assert "lf-region" in html and "lf-paragraph" in html and "lf-line" in html
    assert "Hello world" in html
    assert '<span class="lf-r' not in html  # no run-level span for uniform text


def test_style_change_emits_exactly_one_span() -> None:
    fonts = [_font("reg", "Arial"), _font("ital", "Arial-Italic", style="italic")]
    spans = [
        TextSpan(text="Hello ", font_id="reg", font_size=12.0, color="#000000"),
        TextSpan(text="world", font_id="ital", font_size=12.0, color="#000000"),
    ]
    html = _render(_document([_block("Hello world", 100.0, spans)], fonts))
    assert html.count('<span class="lf-r') == 1  # only the italic run
    assert "Hello " in html  # base run stays plain text


def test_adjacent_base_runs_coalesce_into_one_text_node() -> None:
    # Same visual style split into two spans by extraction → one text node.
    fonts = [_font("a", "ABCDEF+Arial"), _font("b", "XYZQWE+Arial")]
    spans = [
        TextSpan(text="Hello ", font_id="a", font_size=12.0, color="#000000"),
        TextSpan(text="world", font_id="b", font_size=12.0, color="#000000"),
    ]
    html = _render(_document([_block("Hello world", 100.0, spans)], fonts))
    assert "Hello world" in html  # contiguous, no span boundary inside
    assert '<span class="lf-r' not in html


def test_whitespace_only_run_never_forces_a_span() -> None:
    # A space extracted at a different size (bold, larger) must not become its
    # own <span> — an invisible glyph carries no style.
    fonts = [_font("reg", "Arial"), _font("big", "Arial-Bold", weight="bold")]
    spans = [
        TextSpan(text="Hello", font_id="reg", font_size=12.0, color="#000000"),
        TextSpan(text=" ", font_id="big", font_size=24.0, color="#000000"),
        TextSpan(text="world", font_id="reg", font_size=12.0, color="#000000"),
    ]
    html = _render(_document([_block("Hello world", 100.0, spans)], fonts))
    assert "Hello world" in html
    assert '<span class="lf-r' not in html


def test_css_is_deduplicated_across_paragraphs() -> None:
    fonts = [_font("f1", "Arial")]
    style = [TextSpan(text="line", font_id="f1", font_size=12.0, color="#000000")]
    # Two blocks far apart → two paragraphs, identical style → one shared class.
    doc = _document([_block("first", 100.0, style), _block("second", 400.0, style)], fonts)
    result = RenderEngine().render(WriterContext.create(doc))
    assert result.stylesheet.count(".lf-p") == 1


def test_stable_ids_toggle_with_flag() -> None:
    fonts = [_font("f1", "Arial")]
    doc = _document([_block("Hi", 100.0, [TextSpan(text="Hi", font_id="f1", font_size=12.0, color="#000000")])], fonts)
    assert "data-object-id" in _render(doc, FeatureFlags(emit_stable_ids=True))
    assert "data-object-id" not in _render(doc, FeatureFlags(emit_stable_ids=False))


def test_debug_attributes_expose_confidence() -> None:
    fonts = [_font("f1", "Arial")]
    doc = _document([_block("Hi", 100.0, [TextSpan(text="Hi", font_id="f1", font_size=12.0, color="#000000")])], fonts)
    assert "data-confidence" in _render(doc, FeatureFlags(emit_debug_attributes=True))


def test_render_engine_rejects_reserved_targets() -> None:
    fonts = [_font("f1", "Arial")]
    doc = _document([_block("Hi", 100.0, [TextSpan(text="Hi", font_id="f1", font_size=12.0, color="#000000")])], fonts)
    with pytest.raises(UnsupportedTargetError):
        RenderEngine().render(WriterContext.create(doc, target=Target.EPUB))


def test_fidelity_gate_catches_a_dropped_run() -> None:
    class _LossyWriter(HtmlWriter):
        def _render_line(self, line, base_key, registry, ctx):
            html = super()._render_line(line, base_key, registry, ctx)
            return html.replace("world", "")  # simulate a rendering bug

    fonts = [_font("f1", "Arial")]
    doc = _document([_block("Hello world", 100.0, [TextSpan(text="Hello world", font_id="f1", font_size=12.0, color="#000000")])], fonts)
    with pytest.raises(HtmlFidelityError):
        _LossyWriter().write(WriterContext.create(doc))
