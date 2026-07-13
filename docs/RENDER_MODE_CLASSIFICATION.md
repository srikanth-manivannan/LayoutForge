# Render Mode Classification — Semantic Flow vs. Fixed Layout

**Status:** PARKED — premature (user, 2026-07-13). The actual overlap bug did
not need this classifier; it needed a structural fix to the paragraph layout
model (regions become the flow container; paragraphs are chained in normal
flow with PDF-gap margins instead of independent absolute positions — see
`docs/RENDER_INSTRUCTION_LAYER.md` Rule 0). That fix is universal and
threshold-free, and is what shipped. This document's proposal (a per-
paragraph FLOW/FIXED decision for cases where position genuinely IS the
document's meaning — display type, cover art) remains a real, separate
question for later, once corpus evidence exists to calibrate it. Not
implemented; revisit only when specific documents demonstrate the need.

**Original framing below, preserved for reference:**
**Triggered by:** the Paragraph Layout Investigation's ownership finding,
sharpened by review: reconstruction's `bbox`/`line_height` are *correct for a
PDF renderer, insufficient for a browser-flow renderer* — the real fix is
not to reconcile the two, but to recognize that **not every paragraph should
be browser-flowed**, and decide *which* per paragraph, from evidence.

## Rule 0 (new, permanent): one dimension, one owner

> A single layout dimension must never have two owners. If the PDF owns a
> paragraph's `top`, the PDF must also own its `height` — the browser may
> never silently expand a box whose position another authority fixed.
> Symmetrically, if the browser owns `height` (flow), the PDF must not
> assert a `height` at all.

This is now binding on the Instruction Builder and every future compiler.
Added to `docs/RENDER_INSTRUCTION_LAYER.md`.

## The two contracts this implies

**Fixed-layout paragraph** (PDF owns position AND extent — Mode 1,
"Pixel Proof"): geometry = `{x, y, width, height}`, exactly as today.
Internally still built from lines (their bboxes are real PDF facts for this
mode), each positioned absolutely. No browser wrapping is ever invoked —
`white-space: pre` (not `pre-wrap`), because wrapping would violate the
height the PDF asserted.

**Semantic-flow paragraph** (browser owns extent — Mode 2, R-2's model):
geometry = `{x, y, width}` — **no `height` field at all**, matching your
proposal exactly. Typography carried: `alignment`, `first_line_indent`,
`line_height` (as CSS `line-height`, a *rate* the browser applies to
however many lines it produces — not a *reservation*), `space_before`/
`space_after` (margins). The browser computes height, wrapping, baseline
stacking. `white-space: pre-wrap`.

## Where the decision lives (Rule 4 compliance)

**This is a reconstruction decision, not a rendering one** — exactly the
shape of `ReconstructionMode` (WORD/GLYPH/…). The Instruction Builder must
not invent this judgment; it must *read* it. Proposed: `Paragraph.layout_mode:
"flow" | "fixed"`, decided by a new lightweight classifier that runs after
the Paragraph Builder, consuming data that already exists — **no extraction,
typography, or Adaptive Reconstruction changes required.**

## Proposed classification signals (all already computed)

| Signal | Source (existing) | What it indicates |
|---|---|---|
| Multi-line, high-confidence grouping | `Paragraph.confidence`, `Paragraph.reason` (`"single_line"` vs `"grouped"`) | A `single_line` paragraph never merged with a neighbor — it's a display block by construction, not prose. Strong FIXED signal. |
| Font size vs. document median | `Run.font_size` across the document (cheap to compute once) | Body prose clusters tightly around one size; titles/covers are typically ≥1.5–2× the median. Large-relative-to-median → FIXED. |
| Reconstruction cleanliness | per-word `mode`/`reason` already on `WordBox`, aggregated per paragraph | A paragraph whose words are mostly `WORD` mode with `reason="none"` is measuring cleanly — ordinary typeset prose. Heavy `GLYPH`/`tracking`/`kerning` (the ChauncyPro/KGDancing pattern) signals hand-set display type where position IS the meaning → FIXED. |
| Line count | `len(Paragraph.lines)` | A 1-line paragraph has no wrapping question either way — mode is nearly moot, but line count ≥2 is a prerequisite for FLOW to matter at all. |

**Proposed rule (paragraph qualifies for FLOW only if ALL hold):**
1. `reason == "grouped"` **and** `confidence ≥ 0.6` (genuine multi-line prose,
   not a lone display line);
2. dominant run's `font_size ≤ 1.5 ×` the document's median body font size;
3. ≥ 80% of the paragraph's words are `mode == "word"` with `reason in
   {"none", "tracking"}` (clean measurement — excludes the GLYPH-heavy
   optical-kerning pattern M-R2 found in display type).

Everything else — single lines, oversized text, heavily-escalated
typography — renders **FIXED**, using the *original per-line* geometry
(closer to R-1's model, not R-2's line-flattening), because for exactly
these paragraphs position is part of the document's meaning, as you said.

This also explains the corpus evidence cleanly in hindsight: the copyright
page (7-line prose, clean ChauncyPro-Regular/Palatino body text) is a
textbook FLOW candidate; the title page ("Tot theToad", KGDancingontheRooftop
at 60–115px, 45% glyph escalation) is a textbook FIXED candidate. R-2 applied
FLOW's contract uniformly and got the copyright page right by accident and
the title page wrong by design.

## Category-level default, not a substitute

Per-paragraph classification (above) is the mechanism; a document-category
prior (novels/dictionaries default toward FLOW, comics/magazines/children's-
book covers default toward FIXED) is a reasonable *tie-breaker* for
low-confidence cases, but — as you noted — a single document mixes both
(a children's book has a decorative cover **and** a plain-prose copyright
page), so classification must stay per-paragraph. Category becomes a prior
RVF can report on (M-R0's category breakdown already exists for this), not
a hard switch.

## Deferred / explicitly out of scope for this design

- **Background-raster analysis** (is this paragraph sitting over illustrated
  art?) — a real signal, heavier to compute (image variance under the bbox),
  not required to resolve the immediate defect. Flagged as a future
  refinement, not blocking.
- Any change to extraction, typography, or Adaptive Reconstruction.

## What I need from you before implementing

1. **Approve or adjust the three thresholds** above (0.6 confidence, 1.5×
   median size, 80% clean-word fraction) — these are product judgment calls,
   not measurements I can derive.
2. **Confirm the decision belongs in reconstruction** (a new stage/step
   producing `Paragraph.layout_mode`), consumed — never decided — by the
   Instruction Builder, per Rule 4.
3. **Go-ahead to implement**, given this changes visual output broadly
   (every paragraph in the corpus gets classified) and is exactly the kind
   of consequential, hard-to-reverse-by-accident change worth confirming
   before touching code.
