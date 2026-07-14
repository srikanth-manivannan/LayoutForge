"""Instruction Builder (RIL) — the ONLY place rendering decisions are made.

Rule 0 (permanent, 2026-07-13): **a single layout dimension must never have
two owners.** R-2 gave every paragraph an independently PDF-absolute `top`
while handing `height` to browser flow — the two owners never reconciled,
so a paragraph that rendered taller than its PDF box overlapped the next
paragraph, whose position didn't know or care. The fix is not to reconcile
the two owners after the fact; it is to never let one paragraph carry both.

**Paragraphs flow in reading order.** Only the REGION is PDF-absolute (one
anchor per region, from `region.bbox`); every paragraph inside it is a
normal-flow block, spaced from its predecessor by a `margin-top` equal to
the PDF-measured GAP between them (not an absolute coordinate) — so if a
paragraph renders taller than the PDF implied, the next one is pushed down
by ordinary CSS flow, exactly like every other browser-owns-layout system.
Height is never asserted on a paragraph. This holds for every paragraph
uniformly — no classification, no thresholds, no per-paragraph judgment.

Phase R-2's line-flattening (paragraph → merged runs, browser wraps within
the paragraph) is unchanged and combines with this: paragraphs now flow
correctly relative to EACH OTHER, and text flows correctly WITHIN each one.

Rule 4 extended (2026-07-13): **the Instruction Builder must not destroy
measured geometry, only decline to invent it.** `margin-top` is the PDF-
measured gap between consecutive paragraphs' bounding boxes, emitted
EXACTLY as measured — including negative values. A negative gap is not
measurement noise; it means the two paragraphs' PDF boxes genuinely
overlap (found on a real cover: a title's tall glyph bbox overlapping the
tagline beneath it by 31pt — ordinary for large/hand-drawn display type).
Clamping that to zero was itself a repair — discarding a real measurement
because the model didn't expect it, the same failure mode Rule 0 exists to
prevent. CSS `margin-top` supports negative values natively; the browser
pulls the next paragraph up to reproduce the overlap. No classification, no
threshold: every gap, whatever its sign, is represented as-is.

Rotated paragraphs (margin text) are the one deliberate exception: rotation
requires an absolute anchor, so they stay ABSOLUTE within their region and
do not participate in the flow chain (they neither push nor are pushed by
siblings — the same treatment PDF margin text always needs).

Deterministic: same Document/Page → identical tree. Derived: lives in
`context.scratch` for one conversion and is never serialized.
"""

import math
from dataclasses import dataclass, field

from app.pipeline.document import Document
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.page import Page
from app.pipeline.outputs.font_naming import css_family_stack

# Render modes — decided here, once. Compilers map them mechanically.
NORMAL = "normal"      # in-flow text (run children) / in-flow block (flowed paragraphs)
ANCHORED = "anchored"  # in-flow at a fixed offset (reserved for builder v2)
ABSOLUTE = "absolute"  # positioned block (regions; rotated paragraphs)
GLYPH = "glyph"        # per-glyph placement (M2; compilers may fall back)


@dataclass
class RenderNode:
    kind: str  # "page" | "region" | "paragraph" | "run"
    object_id: str
    mode: str = NORMAL
    text: str = ""
    # CSS-ready declarations. Geometry (unique per node) and style (heavily
    # repeated → deduplicated by the Style Registry at compile time).
    geometry: dict = field(default_factory=dict)
    style: dict = field(default_factory=dict)
    rise: float = 0.0
    children: "list[RenderNode]" = field(default_factory=list)

    def iter_runs(self):
        if self.kind == "run":
            yield self
        for child in self.children:
            yield from child.iter_runs()

    def iter_paragraphs(self):
        if self.kind == "paragraph":
            yield self
        for child in self.children:
            yield from child.iter_paragraphs()


def _run_differs_from_base(run, base) -> bool:
    """Whether this run needs its own `<span>` at all — a style boundary,
    never a positioning unit (ADR-011). Whitespace-only runs carry no
    visible glyphs: always base style."""
    if not run.text.strip():
        return False
    return (
        run.font_id != base.font_id
        or run.color != base.color
        or run.weight != base.weight
        or run.italic != base.italic
        or abs(run.font_size - base.font_size) > 0.01
        or abs(run.letter_spacing - base.letter_spacing) > 0.001
    )


def _run_style(run, base, fonts_by_id: dict[str, FontResource]) -> dict:
    """Rendering Stabilization phase (temporary, 2026-07-13): the Style
    Registry is bypassed, so every `<span>` must be fully self-contained —
    a run that differs from the paragraph base gets its COMPLETE typography
    declarations here, not just the differing ones, so nothing is implied by
    a shared class a debugger can't see inline. A base-style run still gets
    an EMPTY style dict and compiles to a plain text node (deciding WHETHER
    a run needs a span at all is a content-fidelity concern — Rule 3/8 — and
    is unchanged; only what a differing run carries has changed)."""
    if not _run_differs_from_base(run, base):
        return {}
    return {
        "color": run.color,
        "font-family": css_family_stack(fonts_by_id.get(run.font_id) if run.font_id else None),
        "font-size": f"{run.font_size:g}px",
        "font-weight": f"{run.weight}",
        "font-style": "italic" if run.italic else "normal",
        "letter-spacing": f"{run.letter_spacing:g}px",
    }


def _rotation_geometry(paragraph, block_by_line: dict) -> dict:
    """Rotation transform for rotated paragraphs (margin text): PDF rotates
    about the BASELINE START, not a bbox corner. Empty for unrotated
    paragraphs (the common case, which uses flow geometry instead)."""
    for line in paragraph.lines:
        block = block_by_line.get(line.id)
        if block is None or not block.rotation:
            continue
        size = block.font_size or 12.0
        line_height = block.line_height or size * 1.2
        theta = math.radians(block.rotation)
        cos_t, sin_t = abs(math.cos(theta)), abs(math.sin(theta))
        if cos_t >= sin_t:
            run_length = max(1.0, (line.bbox.width - line_height * sin_t) / max(cos_t, 1e-6))
        else:
            run_length = max(1.0, (line.bbox.height - line_height * cos_t) / max(sin_t, 1e-6))
        baseline_offset = (block.ascender or 0.8) * size
        return {
            "left": f"{block.origin_x:g}px",
            "top": f"{block.origin_y - baseline_offset:g}px",
            "width": f"{run_length:g}px",
            "transform": f"rotate({block.rotation:g}deg)",
            "transform-origin": f"0px {baseline_offset:g}px",
        }
    return {}


def _flatten_paragraph_runs(paragraph, base, fonts_by_id) -> list[tuple[str, dict, float, str]]:
    """(text, style, rise, source_run_id) sequence for the WHOLE paragraph:
    lines joined by a single space, adjacent identical styles merged. Line
    structure ends here — compilers never see it."""
    entries: list[tuple[str, dict, float, str]] = []
    for index, line in enumerate(paragraph.lines):
        if index > 0:
            # A line break separates words — but only add a space when the
            # boundary doesn't already have one (PDF lines often end with
            # trailing spaces; under pre-wrap a doubled join would render as
            # a visible gap). Layout-only: non-whitespace content untouched.
            previous_ends_space = bool(entries) and entries[-1][0][-1:].isspace()
            next_starts_space = bool(line.runs) and line.runs[0].text[:1].isspace()
            if not previous_ends_space and not next_starts_space:
                entries.append((" ", {}, 0.0, f"{line.id}-join"))
        for run in line.runs:
            entries.append((run.text, _run_style(run, base, fonts_by_id), run.rise, run.id))

    merged: list[list] = []
    for text, style, rise, run_id in entries:
        if merged and merged[-1][1] == style and abs(merged[-1][2] - rise) < 0.01:
            merged[-1][0] += text
        else:
            merged.append([text, style, rise, run_id])
    return [tuple(entry) for entry in merged]


def _build_paragraph_node(paragraph, region, fonts_by_id, block_by_line) -> "tuple[RenderNode, float, float]":
    """Returns (node, bbox_top, chain_bottom) — bbox_top anchors THIS
    paragraph's own margin-top; chain_bottom is what the NEXT paragraph's
    margin-top is measured from, and is never asserted as a CSS height.

    chain_bottom uses `line_count * line_height`, NOT the PDF's ink-tight
    `bbox.height` (2026-07-14). Those two numbers measure different things:
    ink-tight bbox spans first-line-ascent to last-line-descent, while the
    browser renders `line_count` uniform boxes of `line_height` — for
    generously-leaded text (line_height greater than the font's own
    ascent+descent) they diverge by that exact difference, and using the
    ink bbox as the anchor made every multi-line paragraph's actual
    rendered height fall short of what the anchor assumed, pulling every
    following paragraph up (found via real book: 5.46px/paragraph,
    compounding to -20.9px after 4 multi-line paragraphs). `line_count *
    line_height` is what the browser will actually render for a paragraph
    whose wrap matches the PDF's own line count — the common case — so the
    chain stays self-consistent. It is still an approximation when the
    browser wraps to a different line count than the PDF (a separate,
    smaller, already-acknowledged limit of browser-owned reflow — not
    solved here, and not solvable without the engine duplicating the
    browser's own text-measurement)."""
    runs = [run for line in paragraph.lines for run in line.runs]
    base = max(runs, key=lambda r: len(r.text))

    # Rendering Stabilization phase (temporary): every property here is
    # always present, including true-default zero values (letter-spacing:
    # 0px, word-spacing: 0px are the real default, not invented data) — the
    # Style Registry is bypassed, so this paragraph's inline style is the
    # ONLY place its typography is recorded; nothing may be implied by a
    # class a debugger can't see. line-height/text-align/text-indent stay
    # conditional: they're MEASURED values the builder may not have (single-
    # line paragraphs get line_height=0.0), and fabricating one here would
    # cross into the compiler's "never repair/invent" territory — Rule 4.
    style = {
        "color": base.color,
        "font-family": css_family_stack(fonts_by_id.get(base.font_id) if base.font_id else None),
        "font-size": f"{base.font_size:g}px",
        "font-weight": f"{base.weight}",
        "font-style": "italic" if base.italic else "normal",
        "letter-spacing": f"{base.letter_spacing:g}px",
        "word-spacing": f"{(paragraph.word_spacing or base.word_spacing):g}px",
        "writing-mode": base.writing_mode,
    }
    if paragraph.line_height:
        style["line-height"] = f"{paragraph.line_height:g}px"
    if paragraph.alignment and paragraph.alignment != "left":
        style["text-align"] = paragraph.alignment
    if paragraph.first_line_indent:
        style["text-indent"] = f"{paragraph.first_line_indent:g}px"

    rotation = _rotation_geometry(paragraph, block_by_line)
    if rotation:
        # Rotated text is a deliberate flow exception: absolute within the
        # region, position/size fully PDF-owned (Rule 0 — both dimensions
        # owned by the same authority), never flow-chained with siblings.
        node = RenderNode(kind="paragraph", object_id=paragraph.id, mode=ABSOLUTE,
                           geometry=rotation, style=style)
    else:
        # Flow paragraph: NO top, NO left, NO height. Width is the only
        # PDF-owned geometry left — the browser owns everything vertical.
        node = RenderNode(kind="paragraph", object_id=paragraph.id, mode=NORMAL,
                           geometry={"width": f"{paragraph.bbox.width:g}px"}, style=style)

    for text, run_style, rise, run_id in _flatten_paragraph_runs(paragraph, base, fonts_by_id):
        node.children.append(RenderNode(kind="run", object_id=run_id, mode=NORMAL,
                                        text=text, style=run_style, rise=rise))
    if paragraph.line_height:
        chain_bottom = paragraph.bbox.y + len(paragraph.lines) * paragraph.line_height
    else:
        # No measured or estimated line_height at all (degenerate case, e.g.
        # a paragraph with no positive leading anywhere) — the ink bbox is
        # the only geometry left to chain from.
        chain_bottom = paragraph.bbox.y + paragraph.bbox.height
    return node, paragraph.bbox.y, chain_bottom


def build_render_tree(document: Document, page: Page) -> RenderNode:
    """Deterministic: same Document/Page → identical tree. No I/O, no
    randomness, no environment reads."""
    fonts_by_id = {font.id: font for font in document.fonts}
    block_by_line: dict = {}
    for region in page.regions:
        for paragraph in region.paragraphs:
            for line in paragraph.lines:
                for block in page.text_blocks:
                    if abs(block.origin_y - line.baseline_y) < 0.01 and abs(block.bbox.x - line.bbox.x) < 0.01:
                        block_by_line[line.id] = block
                        break

    page_node = RenderNode(kind="page", object_id=f"page-{page.number}", mode=ABSOLUTE)
    for region in page.regions:
        paragraphs_with_runs = [p for p in region.paragraphs if any(l.runs for l in p.lines)]
        if not paragraphs_with_runs:
            continue

        region_node = RenderNode(
            kind="region", object_id=region.id, mode=ABSOLUTE,
            geometry={"left": f"{region.bbox.x:g}px", "top": f"{region.bbox.y:g}px",
                     "width": f"{region.bbox.width:g}px"},
        )
        previous_bottom: float | None = None
        for paragraph in paragraphs_with_runs:
            node, top, bottom = _build_paragraph_node(paragraph, region, fonts_by_id, block_by_line)
            if node.mode == NORMAL:
                # The PDF-measured GAP to the previous FLOWED paragraph becomes
                # a margin — never an absolute position. First paragraph in
                # the region anchors to the region's own top (already at
                # paragraph[0].bbox.y by construction — see region_builder).
                #
                # The gap is emitted EXACTLY as measured, including negative
                # values (2026-07-13): a negative gap means the two
                # paragraphs' PDF bounding boxes genuinely overlap — common
                # for large/hand-drawn display type (e.g. a cover's title
                # and tagline), never noise to be discarded. The Instruction
                # Builder must not invent or destroy geometry (Rule 4
                # extended to this layer): clamping to 0 would silently
                # throw away a real measurement, exactly the class of
                # "renderer repairs the model" behavior this architecture
                # forbids. CSS `margin-top` natively supports negative
                # values — the browser pulls the paragraph up into the
                # previous one's box, reproducing the PDF's own overlap
                # deterministically. No threshold, no classification: every
                # gap, positive or negative, is represented as-is.
                anchor = previous_bottom if previous_bottom is not None else region.bbox.y
                gap = top - anchor
                node.geometry["margin-top"] = f"{gap:g}px"
                left_offset = max(0.0, paragraph.bbox.x - region.bbox.x)
                if left_offset:
                    node.geometry["margin-left"] = f"{left_offset:g}px"
                previous_bottom = bottom
            # ABSOLUTE (rotated) paragraphs neither read nor advance
            # previous_bottom — they're out of the flow chain entirely.
            region_node.children.append(node)
        page_node.children.append(region_node)
    return page_node
