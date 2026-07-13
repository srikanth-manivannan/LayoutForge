# Paragraph Vertical Layout Investigation

**Status:** Investigation report — NO implementation · 2026-07-13
**Scope:** Paragraph layout ownership only. Extraction, Reconstruction,
Typography, and HTML semantics (R-2's `<p>` + minimal `<span>` contract) were
NOT touched and are NOT implicated by this report.
**Method:** code-path inspection of the Instruction Builder + measured,
per-paragraph comparison of PDF geometry vs required CSS flow height, on the
exact page shown (page 4, "Copyright © 2026 by Jim Benton…").

## Verdict up front

**Vertical position and vertical extent have two different, uncoordinated
owners**, and nothing reconciles them:

- **Position** (`top`) — owned by **PDF/reconstruction geometry**
  (`paragraph.bbox.y`), applied as an absolute coordinate, independently per
  paragraph.
- **Extent** (how tall the paragraph actually renders) — owned by **the
  browser's text flow**, which the renderer intentionally handed control to
  in R-2 (`white-space: pre-wrap`, no line elements, browser wraps).

Nothing in the pipeline checks that the box the first owner reserves is tall
enough for what the second owner will need. When it isn't, the paragraph
overflows downward, over the next paragraph's fixed, independent `top` —
exactly the strikethrough-looking overlap in the screenshot.

## Code-path confirmation

`app/pipeline/rendering/render_tree.py`, the Instruction Builder:

```python
geometry = {
    "left": f"{paragraph.bbox.x:g}px",
    "top": f"{paragraph.bbox.y:g}px",          # ← raw PDF/reconstruction Y
    "width": f"{paragraph.bbox.width:g}px",
    "min-height": f"{paragraph.bbox.height:g}px",  # ← raw PDF/reconstruction height, UNENFORCED
}
```

`app/pipeline/outputs/css_output.py`: `.lf-paragraph { position: absolute; }`,
and `.lf-page { position: relative; }` — every paragraph is positioned
**directly against the page**, not against its preceding sibling. There is
no normal-flow container anywhere in the text layer. `min-height` is a CSS
*floor*, not a *reservation*: if the browser's flowed content is taller, the
box simply grows and the next (independently positioned) paragraph is
underneath it, not below it.

## Answers to the five investigation questions

1. **Are paragraph `top` values taken directly from PDF coordinates?**
   Yes — `paragraph.bbox.y`, unmodified, becomes `top`.
2. **Are paragraph heights taken from PDF instead of browser layout?**
   Yes — `paragraph.bbox.height`, unmodified, becomes `min-height`. It is
   never compared against what the paragraph's own CSS (`line-height` ×
   however many lines the browser produces) will actually require.
3. **Is the next paragraph positioned using PDF Y instead of the previous
   paragraph's rendered height?**
   Yes, unconditionally. Every paragraph's `top` is computed solely from its
   own `paragraph.bbox.y`; nothing reads or reacts to any other paragraph's
   size, rendered or otherwise.
4. **Does the renderer mix browser flow with absolute PDF geometry?**
   Yes — this is the core of the defect. Position is absolute/PDF-owned;
   extent is flow/browser-owned; the two are architecturally uncoupled.
5. **Measured PDF vs. required-flow height, every paragraph on page 4:**

| Paragraph (start of text) | PDF lines | PDF `bbox.height` | measured `line-height` | PDF height ÷ line-height | Required height (lines × line-height) | Deficit |
|---|---:|---:|---:|---:|---:|---:|
| "Copyright © 2026…" | 1 | 19.86px | 19.86px | 1.00 | 19.86px | 0px |
| "All rights reserved. Published…" | 2 | 34.39px | 19.86px | **1.73** | 39.72px | **+5.33px** |
| "The publisher does not have…" | 2 | 34.26px | 19.86px | **1.73** | 39.72px | **+5.46px** |
| "All rights reserved under International…" | 7 | 106.26px | 19.86px | **5.35** | 139.02px | **+32.76px** |
| "This book is a work of fiction…" | 3 | 48.66px | 19.86px | **2.45** | 59.58px | **+10.92px** |
| "e-ISBN 979-8-225-07148-6" | 1 | 19.86px | 19.86px | 1.00 | 19.86px | 0px |

**Every multi-line paragraph on the page is reserved a box shorter than its
own line count times its own measured line-height** — by 5 to 33 pixels,
scaling directly with line count (~2.7–4.7px per line). This is not a
browser-wrapping artifact — the PDF's own line count was used in this
calculation, no browser simulation involved. It is a **definitional
mismatch inside the geometry itself**: `paragraph.bbox.height` is a tight
geometric union of the member lines' ink-extent bounding boxes (top of the
first line's box to bottom of the last), which is measurably smaller than
`line_count × leading` — leading includes inter-line space that a tight ink
union does not.

*(Separately, a rough greedy-wrap simulation using the same font metrics the
engine trusts suggests browser line-wrapping may add a further, smaller
discrepancy on some short single-line paragraphs — this signal was noisy for
base-14 fallback fonts and is reported with low confidence; the table above,
using the PDF's own actual line count, is the reliable, primary finding.)*

## Where this mismatch is introduced vs. where it becomes a defect

- **The geometric mismatch itself is introduced in reconstruction**
  (`paragraph_builder.py`): `paragraph.bbox` is computed as a tight union of
  line boxes, while `paragraph.line_height` is computed independently (median
  measured leading). Nothing there guarantees `bbox.height ≈ line_count ×
  line_height` — and nothing needed to, because until R-1/R-2 the renderer
  never asked the box to also be a valid CSS flow container. The bbox was,
  and still is, a correct and faithful *positioning* box; it was never
  contracted to be a *flow-sizing* box.

- **The mismatch becomes a rendering defect in the Instruction Builder**
  (`render_tree.py`). This is the stage that decided to (a) hand vertical
  extent to browser flow, while (b) continuing to anchor every paragraph
  independently to absolute PDF coordinates, with (c) no check that the
  reserved box satisfies the flow it now permits, and (d) no coupling between
  siblings that would let one paragraph's overflow push the next one down.
  The Instruction Builder's own validator (`tree_validator.py`) also has no
  self-consistency check here — it validates unicode, paragraph count, ids,
  and geometry *presence*, but not geometry *sufficiency*.

**Ownership conclusion:** the Instruction Builder owns the incorrect vertical
positioning model. It introduced browser-flow extent (R-2) without updating
the positioning model (still R-1's independent-absolute-per-paragraph, a
model that was only ever safe when extent was also absolute/PDF-derived, as
it was in R-1). The reconstruction-side bbox/line_height definitions are not
themselves wrong for what they were designed to guarantee — the Instruction
Builder began relying on a guarantee (box height ⊇ flowed content height)
that was never established by the stage that produced the box.

**No fix implemented, per instruction.**
