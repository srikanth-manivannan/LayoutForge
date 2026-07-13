"""Render Instruction Layer (permanent rendering architecture, approved
2026-07-12; Rule 0 added 2026-07-13). Rules under test: compiler purity
(Rule 1), determinism (Rule 2), paragraph DOM with no line elements (Rule 3),
compiler-never-repairs via validator gating (Rules 4+6), Style Registry
classes (Rule 7), and Rule 0 — one dimension, one owner: flowed paragraphs
carry no top/height; regions are the one absolute anchor; inter-paragraph
spacing is a PDF-measured-gap margin, never an absolute coordinate."""

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
        Line(id="l1", bbox=bb1, baseline_y=110.0, runs=runs1),
        Line(id="l2", bbox=bb2, baseline_y=124.0, runs=runs2),
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


def _two_paragraph_document(gap: float = 6.0) -> tuple[Document, Page]:
    """Two single-line paragraphs in one region, separated vertically by
    `gap` px — the exact shape of the copyright-page overlap bug."""
    fonts = [FontResource(id="f1", original_name="Arial", family="Arial")]
    bb1 = BoundingBox(50, 100, 300, 14)
    y2 = 100 + 14 + gap
    bb2 = BoundingBox(50, y2, 300, 14)
    line1 = Line(id="l1", bbox=bb1, baseline_y=110.0,
                 runs=[Run(id="r1", bbox=bb1, text="First paragraph", font_id="f1", font_size=12.0)])
    line2 = Line(id="l2", bbox=bb2, baseline_y=y2 + 10.0,
                 runs=[Run(id="r2", bbox=bb2, text="Second paragraph", font_id="f1", font_size=12.0)])
    para1 = Paragraph(id="p1", bbox=bb1, line_height=14.0, lines=[line1])
    para2 = Paragraph(id="p2", bbox=bb2, line_height=14.0, lines=[line2])
    blocks = [
        TextBlock(id="b1", page=1, bbox=bb1, text="First paragraph", origin_y=110.0,
                  font_size=12.0, ascender=0.8, descender=-0.2),
        TextBlock(id="b2", page=1, bbox=bb2, text="Second paragraph", origin_y=y2 + 10.0,
                  font_size=12.0, ascender=0.8, descender=-0.2),
    ]
    region = Region(id="reg1", bbox=BoundingBox(50, 100, 300, y2 + 14 - 100), paragraphs=[para1, para2])
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


# ---- Rule 3 (R-2): real paragraphs, NO line elements -------------------------

def test_dom_is_region_wrapping_one_p_per_paragraph() -> None:
    document, page = _document()
    tree = build_render_tree(document, page)
    validate_render_tree(tree, page)
    fragments = compile_page_text_layer(tree)
    assert len(fragments) == 1  # one region fragment
    html = fragments[0]
    assert html.startswith('<div class="lf-region"')
    assert html.count('class="lf-paragraph') == 1  # ONE <p> for both source lines
    assert "lf-line" not in html  # lines are engine-only — NEVER in HTML
    assert html.count("<span") == 2  # bold + risen runs only
    assert " world <span" in html and ">second line here</span>" in html


def test_adjacent_same_style_runs_merge_across_lines() -> None:
    document, page = _document()
    page.regions[0].paragraphs[0].lines[1].runs[0].rise = 0.0
    tree = build_render_tree(document, page)
    paragraph = tree.children[0].children[0]
    texts = [c.text for c in paragraph.children]
    assert " world second line here" in texts


def test_rise_is_emitted_as_data_not_decided() -> None:
    document, page = _document()
    tree = build_render_tree(document, page)
    html = "".join(compile_page_text_layer(tree))
    # Rendering Stabilization phase: no Style Registry class — rise is
    # inline on the span itself.
    assert "top: -3.5px" in html


def test_paragraph_carries_typography_not_lines() -> None:
    document, page = _document()
    tree = build_render_tree(document, page)
    paragraph = tree.children[0].children[0]
    assert paragraph.style["line-height"] == "14px"
    assert paragraph.geometry["width"] == "300px"
    assert all(c.kind == "run" for c in paragraph.children)


# ---- Rule 0: one dimension, one owner ---------------------------------------

def test_flowed_paragraph_has_no_top_or_height() -> None:
    """The exact defect from the field: a flowed paragraph must never assert
    an absolute position or a height — both are browser-owned."""
    document, page = _two_paragraph_document()
    tree = build_render_tree(document, page)
    for region in tree.children:
        for paragraph in region.children:
            assert "top" not in paragraph.geometry
            assert "height" not in paragraph.geometry
            assert "left" not in paragraph.geometry


def test_only_the_region_is_absolutely_anchored() -> None:
    document, page = _two_paragraph_document()
    tree = build_render_tree(document, page)
    region = tree.children[0]
    assert region.kind == "region"
    assert {"left", "top", "width"} <= region.geometry.keys()
    assert all(p.mode == "normal" for p in region.children)


def test_margin_top_equals_the_pdf_measured_gap() -> None:
    document, page = _two_paragraph_document(gap=6.0)
    tree = build_render_tree(document, page)
    paragraphs = tree.children[0].children
    assert paragraphs[0].geometry.get("margin-top", "0px") in ("0px", "0")
    assert paragraphs[1].geometry["margin-top"] == "6px"


def test_margin_top_never_goes_negative() -> None:
    # A near-zero/negative measured gap (noisy geometry) must clamp to 0,
    # never produce a negative margin that recreates overlap.
    document, page = _two_paragraph_document(gap=-2.0)
    tree = build_render_tree(document, page)
    paragraphs = tree.children[0].children
    assert paragraphs[1].geometry["margin-top"] == "0px"


def test_taller_render_pushes_next_paragraph_not_overlaps() -> None:
    """Structural guarantee behind the fix: because paragraph 2's position is
    a MARGIN relative to paragraph 1 (normal flow), not an absolute PDF
    coordinate, the browser will push it down if paragraph 1 renders taller
    than the PDF implied — this is what CSS normal flow does by
    construction; verified here as the absence of any competing absolute
    top on paragraph 2."""
    document, page = _two_paragraph_document(gap=2.0)
    tree = build_render_tree(document, page)
    second = tree.children[0].children[1]
    assert "top" not in second.geometry  # nothing can compete with flow


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


def test_validator_accepts_allowed_flow_properties() -> None:
    """Every property the real builder actually emits on a flow paragraph —
    width, margin-top, margin-left, plus base run style — must pass clean."""
    document, page = _two_paragraph_document(gap=6.0)
    tree = build_render_tree(document, page)
    validate_render_tree(tree, page)  # must not raise


# ---- Rules 4+6: validator gates the compiler --------------------------------

def test_validator_rejects_unicode_loss() -> None:
    document, page = _document()
    tree = build_render_tree(document, page)
    tree.children[0].children[0].children[0].text = tree.children[0].children[0].children[0].text[:-3]
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
    assert 'style="width: 300px; margin-top: 0px; color: #000000; font-family:' in html
    assert "font-weight: 400" in html
    assert "font-style: normal" in html
    assert "letter-spacing: 0px" in html
    assert "word-spacing: 0px" in html
    assert "writing-mode: horizontal-tb" in html
    # The differing "bold" run's span carries its own complete style, not a diff.
    span_start = html.index("<span", html.index(">bold</span>") - 400)
    span = html[span_start:html.index(">", span_start) + 1]
    for prop in ("color:", "font-family:", "font-size:", "font-weight:", "font-style:", "letter-spacing:"):
        assert prop in span, f"{prop} missing from differing run's inline style: {span}"


def test_compile_page_text_layer_no_longer_takes_a_registry() -> None:
    """Signature check: registry argument removed, not just unused — a
    future call site can't silently pass a registry and have it ignored."""
    import inspect

    sig = inspect.signature(compile_page_text_layer)
    assert list(sig.parameters) == ["tree"]
