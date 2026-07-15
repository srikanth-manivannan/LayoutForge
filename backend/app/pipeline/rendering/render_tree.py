"""Instruction Builder (RIL) — the ONLY place rendering decisions are made.

**Line-as-absolute-primitive (2026-07-15b, replaces the flow-chain Line
Layout Engine from earlier the same day):** a `Region` remains the one
`position:absolute` anchor per region (`region.bbox`, unchanged). Inside it,
every `Line` is now ALSO `position:absolute`, positioned directly from its
own PDF-measured `baseline_y`/`bbox.x` — never from CSS flow, never from a
predicted sibling or paragraph height. `Paragraph` is a purely semantic,
`position:static` wrapper: it owns typography defaults (color/font-family/
size/weight/style/letter-spacing/word-spacing) that its lines/runs inherit,
but asserts NO geometry of its own — nothing flows, so there is nothing to
predict.

This replaces the flow-chain model (Region -> flowed Paragraphs, each with a
`margin-top` computed from a PDF-measured inter-paragraph gap plus a
`chain_bottom`/`_half_leading` correction; Paragraphs -> flowed Lines with
their own `margin-top` chain). That model was found, on a real book, to
compound: a paragraph's chain_bottom assumed the paragraph's RENDERED height
equalled its assigned `line_height` exactly — false whenever a line mixes
runs of different font sizes (CSS grows the line box to fit the tallest
inline child's own natural metrics). The resulting few-px error then
propagated into every subsequent paragraph's position, reaching +16.6px by
the third paragraph on a three-paragraph cover page, even though each
paragraph's own Rich IDM `baseline_y` was independently exact. See
docs/ROAD_TO_PHASE4.md for the measured evidence.

Absolute per-line positioning eliminates the propagation structurally: since
no line's position depends on any other line's or paragraph's rendered
size, an error on one line (e.g. a genuinely mixed-font-size line whose own
box still doesn't perfectly match a naive single-run assumption) stays
local to that line — it cannot compound down the page.

**The one remaining real conversion (see `_line_offset`):** `baseline_y` is
a PDF pen position; CSS `top` is a box edge. Converting between them still
needs a local ascent/half-leading offset — this is unavoidable, not
estimation of the forbidden kind (wrapping, paragraph height, sibling
position): it is a single, local, per-line computation from that line's own
already-measured `ascent`/`leading`, reusing the same `(line_height -
natural)/2` half-leading reasoning proven correct for the old model's
paragraph-to-paragraph transitions, now applied per line instead of chained.

Rotated paragraphs (margin text) are no longer a special flow exception —
every line is absolute now, rotated or not, so a rotated line just carries a
`transform` alongside its `left`/`top` instead of a separate code path.

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
NORMAL = "normal"      # in-flow, no geometry of its own (paragraphs only)
ANCHORED = "anchored"  # in-flow at a fixed offset (reserved for builder v2)
ABSOLUTE = "absolute"  # positioned block (regions; every line)
GLYPH = "glyph"        # per-glyph placement (M2; compilers may fall back)


@dataclass
class RenderNode:
    kind: str  # "page" | "region" | "paragraph" | "line" | "run"
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

    def iter_lines(self):
        if self.kind == "line":
            yield self
        for child in self.children:
            yield from child.iter_lines()


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


def _line_offset(line) -> float:
    """The local baseline-to-box-top conversion (see module docstring). For
    a single-font-size line this is exactly `line.ascent`: setting the box's
    `line-height` to `line.leading` (the font's own natural single-line box
    — the same "natural" quantity `_half_leading` used in the old model)
    makes CSS's `(line_height - natural)/2` half-leading collapse to zero,
    so the baseline sits `ascent` below the box top.

    A line that mixes runs of different font sizes (the proximate cause of
    the compounding bug this replaces) needs the max over its own runs,
    scaled from the line's single measured ascent/leading by each run's
    font-size ratio to the line's primary (longest-text) run — the same
    "one line, multiple sizes" case that used to silently inflate a shared
    paragraph box now only affects this one line's own offset, and does not
    propagate to any sibling."""
    if not line.runs:
        return 0.0
    primary = max(line.runs, key=lambda r: len(r.text))
    primary_size = primary.font_size or 1.0
    leading = line.leading
    best = 0.0
    for run in line.runs:
        ratio = (run.font_size / primary_size) if primary_size else 1.0
        ascent_r = line.ascent * ratio
        natural_r = leading * ratio
        half_leading_r = (leading - natural_r) / 2 if leading > 0 else 0.0
        best = max(best, ascent_r + half_leading_r)
    return best


def _line_rotation_geometry(line, block, region) -> dict | None:
    """Rotation transform for a rotated line (margin text): PDF rotates
    about the BASELINE START, not a bbox corner. `None` for an unrotated
    line — every line is absolute now, so rotation is just an alternate
    geometry dict for the same node, not a separate flow-vs-absolute path."""
    if block is None or not block.rotation:
        return None
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
        "left": f"{block.origin_x - region.bbox.x:g}px",
        "top": f"{block.origin_y - baseline_offset - region.bbox.y:g}px",
        "width": f"{run_length:g}px",
        "transform": f"rotate({block.rotation:g}deg)",
        "transform-origin": f"0px {baseline_offset:g}px",
    }


def _flatten_line_runs(line, base, fonts_by_id) -> list[tuple[str, dict, float, str]]:
    """(text, style, rise, source_run_id) sequence for ONE line: adjacent
    identical styles merged, scoped to this line's own runs only. Merging
    NEVER crosses a line boundary — each PDF line is its own DOM element, so
    there is no "next line's text" to accidentally merge into; the boundary
    is structural, not a joined character to reason about."""
    entries: list[tuple[str, dict, float, str]] = [
        (run.text, _run_style(run, base, fonts_by_id), run.rise, run.id) for run in line.runs
    ]
    merged: list[list] = []
    for text, style, rise, run_id in entries:
        if merged and merged[-1][1] == style and abs(merged[-1][2] - rise) < 0.01:
            merged[-1][0] += text
        else:
            merged.append([text, style, rise, run_id])
    return [tuple(entry) for entry in merged]


def _build_line_nodes(paragraph, base, region, fonts_by_id, block_by_line) -> list:
    """One absolutely-positioned `<span class="lf-line">` RenderNode per PDF
    line. `top`/`left` come directly from `line.baseline_y`/`line.bbox.x`
    (region-relative — the region is the one PDF-absolute anchor); nothing
    here depends on any sibling line or paragraph, so an error on one line
    can never compound into another (see module docstring)."""
    nodes = []
    for line in paragraph.lines:
        block = block_by_line.get(line.id)
        rotation = _line_rotation_geometry(line, block, region)
        if rotation is not None:
            geometry = rotation
        else:
            offset = _line_offset(line)
            geometry = {
                "left": f"{line.bbox.x - region.bbox.x:g}px",
                "top": f"{line.baseline_y - offset - region.bbox.y:g}px",
            }
            if line.leading > 0:
                geometry["line-height"] = f"{line.leading:g}px"
        line_node = RenderNode(kind="line", object_id=line.id, mode=ABSOLUTE, geometry=geometry)
        for text, run_style, rise, run_id in _flatten_line_runs(line, base, fonts_by_id):
            line_node.children.append(RenderNode(kind="run", object_id=run_id, mode=NORMAL,
                                                  text=text, style=run_style, rise=rise))
        nodes.append(line_node)
    return nodes


def _build_paragraph_node(paragraph, region, fonts_by_id, block_by_line) -> RenderNode:
    """A paragraph is a purely semantic, `position:static` wrapper: it owns
    typography defaults its lines/runs inherit, but no geometry — every
    line positions itself absolutely against the region, so there is
    nothing for the paragraph to flow or predict."""
    runs = [run for line in paragraph.lines for run in line.runs]
    base = max(runs, key=lambda r: len(r.text))

    # Rendering Stabilization phase (temporary): every property here is
    # always present, including true-default zero values (letter-spacing:
    # 0px, word-spacing: 0px are the real default, not invented data) — the
    # Style Registry is bypassed, so this paragraph's inline style is the
    # ONLY place its typography is recorded; nothing may be implied by a
    # class a debugger can't see. `width`/`text-align`/`text-indent` are
    # gone (2026-07-15b) — each line's own `left` (from its measured
    # `bbox.x`) already captures alignment/indent geometrically; asserting
    # them again on the paragraph would be redundant, unowned geometry on a
    # node that no longer flows anything.
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

    node = RenderNode(kind="paragraph", object_id=paragraph.id, mode=NORMAL, geometry={}, style=style)
    node.children.extend(_build_line_nodes(paragraph, base, region, fonts_by_id, block_by_line))
    return node


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
        for paragraph in paragraphs_with_runs:
            region_node.children.append(_build_paragraph_node(paragraph, region, fonts_by_id, block_by_line))
        page_node.children.append(region_node)
    return page_node
