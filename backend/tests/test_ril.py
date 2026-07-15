"""Render Instruction Layer (permanent rendering architecture, approved
2026-07-12; Rule 0 added 2026-07-13; Line Layout Engine 2026-07-15;
line-as-absolute-primitive 2026-07-15b). Rules under test: compiler purity
(Rule 1), determinism (Rule 2), paragraph DOM as a semantic wrapper around
per-PDF-line `<span class="lf-line">` children (Rule 3), compiler-never-
repairs via validator gating (Rules 4+6), Style Registry classes (Rule 7),
and Rule 0 — one dimension, one owner: a region is the one absolute anchor
per region; every line is ALSO absolute within it, positioned directly from
its own PDF-measured `baseline_y`/`bbox.x` (never a predicted sibling or
paragraph size — see render_tree.py's `_line_offset`); a paragraph is a
purely semantic, position:static wrapper that asserts no geometry at all."""

import ast
from pathlib import Path

import pytest

from app.pipeline.document import Document
from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.line import Line
from app.pipeline.elements.page import Page
from app.pipeline.elements.paragraph import Paragraph
from app.pipeline.elements.region import Region
from app.pipeline.elements.run import Run
from app.pipeline.elements.textbox import TextBlock
from app.pipeline.rendering.html_compiler import compile_page_text_layer
from app.pipeline.rendering.render_tree import build_render_tree
from app.pipeline.rendering.tree_validator import RenderTreeValidationError, validate_render_tree


def _document() -> tuple[Document, Page]:
    fonts = [
        FontResource(id="f1", original_name="Arial", family="Arial"),
        FontResource(id="f2", original_name="Arial-Bold", family="Arial-Bold", weight="bold"),
    ]
    bb1 = BoundingBox(50, 100, 300, 14)
    bb2 = BoundingBox(50, 114, 300, 14)
    runs1 = [
        Run(id="r1", bbox=bb1, text="Hello ", font_id="f1", font_size=12.0, color="#000000"),
        Run(id="r2", bbox=bb1, text="bold", font_id="f2", font_size=12.0, color="#000000"),
        Run(id="r3", bbox=bb1, text=" world", font_id="f1", font_size=12.0, color="#000000"),
    ]
    runs2 = [Run(id="r4", bbox=bb2, text="second line here", font_id="f1", font_size=12.0,
                 color="#000000", rise=3.5)]
    lines = [
        Line(id="l1", bbox=bb1, baseline_y=110.0, ascent=10.0, leading=14.0, runs=runs1),
        Line(id="l2", bbox=bb2, baseline_y=124.0, ascent=10.0, leading=14.0, runs=runs2),
    ]
    paragraph = Paragraph(id="p1", bbox=BoundingBox(50, 100, 300, 28), line_height=14.0, lines=lines)
    blocks = [
        TextBlock(id="b1", page=1, bbox=bb1, text="Hello bold world", origin_y=110.0,
                  font_size=12.0, ascender=0.8, descender=-0.2),
        TextBlock(id="b2", page=1, bbox=bb2, text="second line here", origin_y=124.0,
                  font_size=12.0, ascender=0.8, descender=-0.2),
    ]
    page = Page(number=1, width=600, height=800, text_blocks=blocks,
                regions=[Region(id="reg1", bbox=BoundingBox(50, 100, 300, 28), paragraphs=[paragraph])])
    return Document(project_id="p", pages=[page], fonts=fonts), page


def _two_paragraph_document() -> tuple[Document, Page]:
    """Two single-line paragraphs in one region, with overlapping PDF boxes
    (the exact shape of the real cover-page case) — demonstrates that each
    line's position depends ONLY on its own baseline_y/ascent/leading, never
    on the other paragraph's rendered size."""
    fonts = [FontResource(id="f1", original_name="Arial", family="Arial")]
    bb1 = BoundingBox(50, 100, 300, 14)
    line1 = Line(id="l1", bbox=bb1, baseline_y=110.0, ascent=10.0, leading=14.0,
                 runs=[Run(id="r1", bbox=bb1, text="First paragraph", font_id="f1", font_size=12.0)])
    para1 = Paragraph(id="p1", bbox=bb1, line_height=14.0, lines=[line1])

    bb2 = BoundingBox(50, 105, 300, 14)  # genuinely overlaps para1's box
    line2 = Line(id="l2", bbox=bb2, baseline_y=118.0, ascent=10.0, leading=14.0,
                 runs=[Run(id="r2", bbox=bb2, text="Second paragraph", font_id="f1", font_size=12.0)])
    para2 = Paragraph(id="p2", bbox=bb2, line_height=14.0, lines=[line2])

    blocks = [
        TextBlock(id="b1", page=1, bbox=bb1, text="First paragraph", origin_y=110.0,
                  font_size=12.0, ascender=0.8, descender=-0.2),
        TextBlock(id="b2", page=1, bbox=bb2, text="Second paragraph", origin_y=118.0,
                  font_size=12.0, ascender=0.8, descender=-0.2),
    ]
    region = Region(id="reg1", bbox=BoundingBox(50, 100, 300, 19), paragraphs=[para1, para2])
    page = Page(number=1, width=600, height=800, text_blocks=blocks, regions=[region])
    return Document(project_id="p", pages=[page], fonts=fonts), page


def _three_line_paragraph_document() -> tuple[Document, Page]:
    """One paragraph, three PDF lines, non-uniform baseline gaps (16px then
    12px) — each line's own `top` is derived directly from its own
    `baseline_y`, independent of the others (no chain, no margin math)."""
    fonts = [FontResource(id="f1", original_name="Arial", family="Arial")]
    baselines = [100.0, 116.0, 128.0]  # gaps: 16, 12
    lines = []
    for i, baseline_y in enumerate(baselines):
        bb = BoundingBox(50, baseline_y - 10, 300, 14)
        lines.append(Line(id=f"l{i}", bbox=bb, baseline_y=baseline_y, ascent=10.0, leading=14.0,
                           runs=[Run(id=f"r{i}", bbox=bb, text=f"Line {i}", font_id="f1", font_size=12.0)]))
    bbox = BoundingBox(50, baselines[0] - 10, 300, (baselines[-1] - 10) - (baselines[0] - 10) + 14)
    paragraph = Paragraph(id="p1", bbox=bbox, line_height=14.0, lines=lines)
    blocks = [
        TextBlock(id=f"b{i}", page=1, bbox=lines[i].bbox, text=f"Line {i}",
                  origin_y=baselines[i], font_size=12.0)
        for i in range(3)
    ]
    region = Region(id="reg1", bbox=bbox, paragraphs=[paragraph])
    page = Page(number=1, width=600, height=800, text_blocks=blocks, regions=[region])
    return Document(project_id="p", pages=[page], fonts=fonts), page


def _mixed_font_size_line_document() -> tuple[Document, Page]:
    """One line, two runs at different font sizes — the proximate cause of
    the compounding bug this architecture replaces (a mixed-size line used
    to inflate its shared paragraph box, pushing every later paragraph down
    the chain). The line's own `top` must come from whichever run's local
    offset is larger, not just the primary (longest-text) run's — and,
    since nothing chains off it anymore, this stays local to this one line."""
    fonts = [
        FontResource(id="f1", original_name="Arial", family="Arial"),
        FontResource(id="f2", original_name="Arial-Bold", family="Arial-Bold", weight="bold"),
    ]
    bbox = BoundingBox(50, 90, 300, 30)
    base_run = Run(id="r1", bbox=bbox, text="Normal text", font_id="f1", font_size=20.0)
    big_run = Run(id="r2", bbox=bbox, text="BIG", font_id="f2", font_size=30.0, weight="bold")
    line = Line(id="l1", bbox=bbox, baseline_y=110.0, ascent=16.0, leading=24.0, runs=[base_run, big_run])
    paragraph = Paragraph(id="p1", bbox=bbox, line_height=24.0, lines=[line])
    blocks = [TextBlock(id="b1", page=1, bbox=bbox, text="Normal text BIG", origin_y=110.0, font_size=20.0)]
    region = Region(id="reg1", bbox=bbox, paragraphs=[paragraph])
    page = Page(number=1, width=600, height=800, text_blocks=blocks, regions=[region])
    return Document(project_id="p", pages=[page], fonts=fonts), page


# ---- Rule 1: compiler purity ------------------------------------------------

def test_compiler_imports_no_idm_nodes() -> None:
    """The HTML compiler may import ONLY the Render Tree + Style Registry —
    never Paragraph/Line/Run/Word/Glyph/TextBlock. Enforced by AST so a
    future edit cannot silently violate the architecture."""
    source = Path("app/pipeline/rendering/html_compiler.py").read_text(encoding="utf-8")
    forbidden = {"paragraph", "line", "run", "word", "glyph", "textbox", "page", "document"}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module:
            module = node.module.lower()
            assert not any(module.endswith(f"elements.{name}") for name in forbidden), \
                f"compiler imports IDM node module: {node.module}"
            assert "elements" not in module, f"compiler imports from elements: {node.module}"


# ---- Rule 2: determinism ----------------------------------------------------

def test_render_tree_is_deterministic() -> None:
    document, page = _document()
    tree_a = build_render_tree(document, page)
    tree_b = build_render_tree(document, page)
    html_a = compile_page_text_layer(tree_a)
    html_b = compile_page_text_layer(tree_b)
    assert html_a == html_b


# ---- Rule 3: semantic paragraphs, absolutely-positioned lines --------------

def test_dom_is_region_wrapping_one_p_per_paragraph() -> None:
    document, page = _document()
    tree = build_render_tree(document, page)
    validate_render_tree(tree, page)
    fragments = compile_page_text_layer(tree)
    assert len(fragments) == 1  # one region fragment
    html = fragments[0]
    assert html.startswith('<div class="lf-region"')
    assert html.count('class="lf-paragraph') == 1  # ONE <p> for both source lines
    # Every PDF line is its own DOM element — a paragraph is a purely
    # semantic wrapper now.
    assert html.count('class="lf-line"') == 2
    assert html.count("<span") == 4  # 2 lf-line wrappers + bold + risen runs
    # No join character of any kind between lines — they're separate
    # elements, not text glued together with a space or a forced \n.
    assert "world</span><span class=\"lf-line\"" in html
    assert ">second line here</span>" in html


def test_runs_merge_within_line_not_across() -> None:
    """Adjacent same-style runs merge WITHIN one line (unchanged behavior),
    but merging can never cross a line boundary — each PDF line is its own
    DOM element, so there is no "next line's text" to merge into."""
    document, page = _document()
    page.regions[0].paragraphs[0].lines[1].runs[0].rise = 0.0
    tree = build_render_tree(document, page)
    paragraph = tree.children[0].children[0]
    lines = [c for c in paragraph.children if c.kind == "line"]
    assert len(lines) == 2
    line1_texts = [c.text for c in lines[0].children]
    line2_texts = [c.text for c in lines[1].children]
    assert " world" in line1_texts  # stays on line 1, never merges with line 2
    assert "second line here" in line2_texts
    assert " world" not in line2_texts and "second line here" not in line1_texts


def test_rise_is_emitted_as_data_not_decided() -> None:
    document, page = _document()
    tree = build_render_tree(document, page)
    html = "".join(compile_page_text_layer(tree))
    # Rendering Stabilization phase: no Style Registry class — rise is
    # inline on the span itself.
    assert "top: -3.5px" in html


def test_paragraph_is_semantic_only_lines_carry_layout() -> None:
    """A paragraph never flows text or owns position/size — it's a semantic
    wrapper around its own `line` children, each of which is absolutely
    positioned and owns its own `line-height`."""
    document, page = _document()
    tree = build_render_tree(document, page)
    paragraph = tree.children[0].children[0]
    assert "line-height" not in paragraph.style
    assert paragraph.geometry == {}
    assert all(c.kind == "line" for c in paragraph.children)
    for line in paragraph.children:
        assert line.geometry["line-height"] == "14px"
        assert "top" in line.geometry and "left" in line.geometry
        assert all(c.kind == "run" for c in line.children)


# ---- Line-as-absolute-primitive: position from baseline, not flow ----------

def test_paragraph_has_one_line_node_per_pdf_line() -> None:
    """Validation criterion (1): number of HTML lines == number of
    extracted PDF lines. Never merged, never split."""
    document, page = _three_line_paragraph_document()
    tree = build_render_tree(document, page)
    paragraph = tree.children[0].children[0]
    lines = [c for c in paragraph.children if c.kind == "line"]
    assert len(lines) == len(page.regions[0].paragraphs[0].lines) == 3


def test_line_top_left_computed_from_baseline_and_ascent() -> None:
    """`top = baseline_y - ascent - region.bbox.y` (half-leading collapses
    to zero here because `line-height` is set to the line's own natural
    `leading`); `left = bbox.x - region.bbox.x`. Baselines 100/116/128,
    ascent 10, region top 90 -> tops 0/16/28 — the raw PDF baseline deltas,
    with zero chain math involved."""
    document, page = _three_line_paragraph_document()
    tree = build_render_tree(document, page)
    lines = [c for c in tree.children[0].children[0].children if c.kind == "line"]
    assert lines[0].geometry == {"left": "0px", "top": "0px", "line-height": "14px"}
    assert lines[1].geometry["top"] == "16px"
    assert lines[2].geometry["top"] == "28px"


def test_runs_stay_nested_under_their_own_line() -> None:
    """Validation criteria (2)/(3): every HTML line starts/ends with
    exactly the same content as its PDF line — structurally guaranteed
    here since runs are never flattened across a line boundary."""
    document, page = _three_line_paragraph_document()
    tree = build_render_tree(document, page)
    lines = [c for c in tree.children[0].children[0].children if c.kind == "line"]
    for i, line_node in enumerate(lines):
        pdf_line = page.regions[0].paragraphs[0].lines[i]
        assert line_node.children[0].text == pdf_line.runs[0].text
        assert line_node.children[-1].text == pdf_line.runs[-1].text


def test_line_left_uses_its_own_bbox_x() -> None:
    """A line's own measured `bbox.x` captures indentation/alignment
    geometrically now — the paragraph no longer asserts text-align/
    text-indent of its own (removed with the flow-chain model)."""
    document, page = _three_line_paragraph_document()
    page.regions[0].paragraphs[0].lines[1].bbox = BoundingBox(80, 106, 270, 14)  # indented
    tree = build_render_tree(document, page)
    lines = [c for c in tree.children[0].children[0].children if c.kind == "line"]
    assert lines[1].geometry["left"] == "30px"  # 80 - region.bbox.x(50)


def test_mixed_font_line_offset_uses_tallest_run() -> None:
    """The line's own top comes from the run whose local (ascent +
    half-leading) offset is largest, not just the primary run's — for a
    20px base run + a 30px bold run (ascent 16/leading 24 at 20px), the
    30px run's scaled offset (18.0) exceeds the base run's (16.0), so
    top = 110 - 18 - region.bbox.y(90) = 2px."""
    document, page = _mixed_font_size_line_document()
    tree = build_render_tree(document, page)
    line = tree.children[0].children[0].children[0]
    assert line.geometry["top"] == "2px"


def test_line_dom_shape() -> None:
    document, page = _document()
    tree = build_render_tree(document, page)
    html = compile_page_text_layer(tree)[0]
    assert '<p class="lf-paragraph"' in html
    assert '<span class="lf-line"' in html
    assert 'class="lf-line" data-object-id=' in html
    assert 'style="left: 0px; top: 0px; line-height: 14px"' in html


def test_validator_requires_top_and_left_on_absolute_line() -> None:
    document, page = _document()
    tree = build_render_tree(document, page)
    line_node = tree.children[0].children[0].children[0]
    del line_node.geometry["top"]
    with pytest.raises(RenderTreeValidationError, match="missing"):
        validate_render_tree(tree, page)


def test_validator_rejects_unlisted_line_property() -> None:
    document, page = _document()
    tree = build_render_tree(document, page)
    line_node = tree.children[0].children[0].children[0]
    line_node.geometry["z-index"] = "5"
    with pytest.raises(RenderTreeValidationError, match="Rule 0.1"):
        validate_render_tree(tree, page)


def test_validator_accepts_absolute_line_geometry() -> None:
    document, page = _three_line_paragraph_document()
    tree = build_render_tree(document, page)
    validate_render_tree(tree, page)  # must not raise


def test_validator_rejects_line_count_mismatch() -> None:
    document, page = _three_line_paragraph_document()
    tree = build_render_tree(document, page)
    paragraph_node = tree.children[0].children[0]
    # Simulate a builder bug that collapses two PDF lines into one line
    # node — moves the last line's runs into the previous line and drops
    # the now-empty node, so total unicode content is UNCHANGED (rules out
    # the unicode-mismatch check firing instead) but the structural line
    # count no longer matches the PDF's — only criterion (1)'s dedicated
    # check catches this.
    paragraph_node.children[-2].children.extend(paragraph_node.children[-1].children)
    del paragraph_node.children[-1]
    with pytest.raises(RenderTreeValidationError, match="line count diverges"):
        validate_render_tree(tree, page)


# ---- Rule 0: one dimension, one owner ---------------------------------------

def test_paragraph_carries_no_geometry() -> None:
    """A paragraph never flows or positions text — it must never assert
    ANY geometry (top/left/height/width/margin/...), since every line
    positions itself absolutely and nothing needs a paragraph-level box."""
    document, page = _two_paragraph_document()
    tree = build_render_tree(document, page)
    for region in tree.children:
        for paragraph in region.children:
            assert paragraph.geometry == {}


def test_only_the_region_is_absolutely_anchored() -> None:
    document, page = _two_paragraph_document()
    tree = build_render_tree(document, page)
    region = tree.children[0]
    assert region.kind == "region"
    assert {"left", "top", "width"} <= region.geometry.keys()
    assert all(p.mode == "normal" for p in region.children)


def test_two_paragraphs_lines_are_independently_positioned() -> None:
    """The structural guarantee behind the fix: each paragraph's line `top`
    is computed purely from its OWN baseline_y/ascent/leading and the
    region's anchor — never from the other paragraph's rendered size, even
    when the two paragraphs' PDF boxes genuinely overlap (the real
    cover-page shape). Baselines 110/118, ascent 10, region top 100 ->
    tops 0px/8px, straight from the PDF measurements."""
    document, page = _two_paragraph_document()
    tree = build_render_tree(document, page)
    para1_line = tree.children[0].children[0].children[0]
    para2_line = tree.children[0].children[1].children[0]
    assert para1_line.geometry["top"] == "0px"
    assert para2_line.geometry["top"] == "8px"


def test_validator_rejects_top_on_a_flowed_paragraph() -> None:
    document, page = _document()
    tree = build_render_tree(document, page)
    tree.children[0].children[0].geometry["top"] = "999px"  # Rule 0 violation
    with pytest.raises(RenderTreeValidationError, match="Rule 0"):
        validate_render_tree(tree, page)


# ---- Rule 0.1: explicit allow/deny list on flow paragraphs ------------------

@pytest.mark.parametrize("prop,value", [
    ("position", "absolute"),
    ("transform", "translate(0, 12px)"),
    ("bottom", "0px"),
    ("right", "0px"),
    ("min-height", "20px"),
    ("max-height", "40px"),
])
def test_validator_rejects_forbidden_geometry_property(prop: str, value: str) -> None:
    document, page = _document()
    tree = build_render_tree(document, page)
    tree.children[0].children[0].geometry[prop] = value
    with pytest.raises(RenderTreeValidationError, match="Rule 0.1"):
        validate_render_tree(tree, page)


def test_validator_rejects_forbidden_style_property() -> None:
    """Rule 0.1 must check `style`, not just `geometry` — a smuggled
    `position: absolute` in style would defeat Rule 0's narrower check."""
    document, page = _document()
    tree = build_render_tree(document, page)
    tree.children[0].children[0].style["position"] = "absolute"
    with pytest.raises(RenderTreeValidationError, match="Rule 0.1"):
        validate_render_tree(tree, page)


def test_validator_rejects_unlisted_geometry_property() -> None:
    """A property that's neither explicitly allowed nor explicitly forbidden
    must still fail closed — the allow list is exhaustive, not a denylist."""
    document, page = _document()
    tree = build_render_tree(document, page)
    tree.children[0].children[0].geometry["z-index"] = "5"
    with pytest.raises(RenderTreeValidationError, match="Rule 0.1"):
        validate_render_tree(tree, page)


def test_validator_accepts_paragraph_typography_only() -> None:
    """A paragraph carries only base-run typography (color/font-family/...)
    and no geometry at all — the only thing left for it to legitimately own."""
    document, page = _two_paragraph_document()
    tree = build_render_tree(document, page)
    validate_render_tree(tree, page)  # must not raise


# ---- Rules 4+6: validator gates the compiler --------------------------------

def test_validator_rejects_unicode_loss() -> None:
    document, page = _document()
    tree = build_render_tree(document, page)
    # region -> paragraph -> line -> run
    run = tree.children[0].children[0].children[0].children[0]
    run.text = run.text[:-3]
    with pytest.raises(RenderTreeValidationError, match="unicode mismatch"):
        validate_render_tree(tree, page)


def test_validator_rejects_duplicate_ids() -> None:
    document, page = _two_paragraph_document()
    tree = build_render_tree(document, page)
    tree.children[0].children[1].object_id = tree.children[0].children[0].object_id
    with pytest.raises(RenderTreeValidationError, match="duplicate"):
        validate_render_tree(tree, page)


def test_validator_rejects_missing_geometry() -> None:
    document, page = _document()
    tree = build_render_tree(document, page)
    tree.children[0].geometry = {}  # region with no geometry
    with pytest.raises(RenderTreeValidationError, match="no geometry"):
        validate_render_tree(tree, page)


# ---- Rendering Stabilization: inline styles only (2026-07-13, temporary) ---
# Rule 7 (Style Registry dedup) is explicitly BYPASSED during this phase —
# shared classes made debugging the paragraph-layout bug harder (one class
# edit silently moved unrelated elements). Every element must be completely
# self-contained. This will be reintroduced as a separate dedup PASS after
# Golden Corpus + visual validation (docs/RENDER_INSTRUCTION_LAYER.md).

def test_no_typography_classes_are_generated() -> None:
    document, page = _document()
    html = "".join(compile_page_text_layer(build_render_tree(document, page)))
    assert "lf-p0" not in html and "lf-p1" not in html
    assert "lf-r0" not in html and "lf-r1" not in html
    assert 'class="lf-s' not in html
    # Structural classes (layout mechanics, not typography) still present.
    assert 'class="lf-region"' in html
    assert 'class="lf-paragraph"' in html


def test_every_paragraph_and_span_carries_a_complete_inline_style() -> None:
    document, page = _document()
    html = "".join(compile_page_text_layer(build_render_tree(document, page)))
    # The base paragraph style: color/font-family/font-size/font-weight/
    # font-style/letter-spacing/word-spacing/writing-mode always present.
    # No geometry (2026-07-15b) — a paragraph asserts none.
    assert 'style="color: #000000; font-family:' in html
    assert "font-weight: 400" in html
    assert "font-style: normal" in html
    assert "letter-spacing: 0px" in html
    assert "word-spacing: 0px" in html
    assert "writing-mode: horizontal-tb" in html
    # The differing "bold" run's span carries its own complete style, not a
    # diff. Search specifically for `<span style="` (the run's OWN span) —
    # `rindex` finds the nearest one before "bold", never the preceding
    # `<span class="lf-line">` wrapper, which has no bare `style=` prefix
    # (it's always `class="lf-line" data-object-id="..." style="..."`).
    bold_end = html.index(">bold</span>")
    span_start = html.rindex('<span style="', 0, bold_end)
    span = html[span_start:html.index(">", span_start) + 1]
    for prop in ("color:", "font-family:", "font-size:", "font-weight:", "font-style:", "letter-spacing:"):
        assert prop in span, f"{prop} missing from differing run's inline style: {span}"


def test_compile_page_text_layer_no_longer_takes_a_registry() -> None:
    """Signature check: registry argument removed, not just unused — a
    future call site can't silently pass a registry and have it ignored."""
    import inspect

    sig = inspect.signature(compile_page_text_layer)
    assert list(sig.parameters) == ["tree"]
