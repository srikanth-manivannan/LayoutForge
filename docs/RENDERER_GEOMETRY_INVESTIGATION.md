# Renderer Geometry Investigation

**Status:** Investigation report — NO implementation · 2026-07-12
**Question (user):** why does the run-based renderer still produce visibly
incorrect layout even though the Rich IDM is correct?
**Method:** measured PDF glyph positions (texttrace) against the browser's
layout model for the same lines, on the reconverted reference book
(`deb6a59f`, page 1 — the failing title page).

## Verdict up front

The Rich IDM data is correct. Phase R-1's rendering *contract* (positioned
line, browser flow inside, spans only on style change) is right as a
DEFAULT — but it silently assumed three things PDF does not guarantee:

1. every glyph in an extracted line shares one baseline;
2. inter-word gaps equal the font's space advance (+tracking);
3. per-glyph advance residuals don't accumulate visibly.

All three assumptions are violated on this one page, each measurably.

## Mechanism A — intra-line vertical offsets (the "Tot the Toad" disaster)

Measured from the source PDF (`get_texttrace`):

```
'T' x=146.06  y=134.15  size=115.27      ← "Tot" baseline
' ' x=265.02  adv=3.60                    ← a SPACE with 3.6px advance at 115pt(!)
't' x=268.61  y=123.29  size= 60.46      ← "the" is RAISED +10.86px
'e' x=312.33  adv=21.13
'T' x=333.46  y=134.15  size=115.27      ← "Toad" back on the main baseline
```

The PDF renders "the" at 60.46px **10.86px above** the main baseline, with
NO space character before "Toad" (the visual gap is glyph-metric, not
whitespace). Inline flow **cannot express any of this**: the browser puts
"the" on the shared alphabetic baseline and renders the 3.6px space as a
normal (or hair) space — hence the overlapping "TottheToad".

**Conclusion:** per-run baseline offset (PDF `Ts` rise / Td jumps) and
non-metric gaps are REAL geometry that must be rendered absolutely.
`Run.rise` is already a reserved field — the data exists in texttrace
(per-glyph y) but extraction currently collapses a line to ONE baseline.
This is the first corpus-proven need for the reserved field.

## Mechanism B — cumulative horizontal drift (the smeared title line)

Two sub-causes, separated by measurement:

**B1 — inter-word gaps: the letter-spacing model largely WORKS.**
PDF gap vs browser gap (space advance + 2×tracking), title line:

```
after 'New'         pdf 10.35   browser 10.35   Δ −0.00
after 'York'        pdf 10.35   browser 10.35   Δ +0.00
after 'Times'       pdf 10.43   browser 10.35   Δ −0.08
after 'Bestselling' pdf 10.43   browser 10.43   Δ −0.00
after 'author'      pdf 13.76   browser 10.43   Δ −3.33   ← run boundary jump
after 'JIM'         pdf 13.06   browser 13.06   Δ +0.00
```

Same-style gaps match to ≤0.08px. The one failure is a **run-boundary
positioning jump** (regular→bold transition padded by the PDF) — a discrete,
per-boundary error, not systemic.

**B2 — per-glyph residual accumulation.** M-R2 measured ChauncyPro's
content-stream optical kerning at ~0.28px/glyph (non-uniform, cannot be
letter-spacing). Over the title line's ~38 glyphs: **~10.6px drift at line
end** — exactly the rightward smear over "JIM BENTON" in the screenshot.
Sub-pixel per glyph, very visible in aggregate. Word-pinning previously
reset this at every word start; removing it *universally* re-exposed
accumulation.

## Mechanism C — vertical line-box mechanics

Title line: `line-height: 31.38px` but inline content at 20.6 / 24.5 /
27.4px. CSS line-box rules grow the box around the tallest inline run and
shift the baseline — while our `<p>` is positioned by bbox **top**. Every
mixed-size line therefore renders its baseline at a browser-computed
position, not the PDF's. (The single-size lines are why fidelity's
baseline_error measured 0.001px — the model was only ever validated on
uniform lines.)

## What must be ABSOLUTE vs what can flow (the answer to Q3)

| Quantity | Verdict | Source of truth (already in IDM?) |
|---|---|---|
| Line baseline | **ABSOLUTE — anchor by baseline, not bbox top**; pin the strut | `origin_y` ✅ |
| Run origin (x) | ABSOLUTE **when** the run boundary carries a measured jump (>ε) — else flow | word/run x ✅ |
| Run baseline rise | **ABSOLUTE** (offset within the line) | ❌ NOT extracted — texttrace has it; `Run.rise` reserved |
| Word starts | FLOW, **re-anchored when cumulative residual exceeds ~0.5px** | `WordBox.x` ✅ + `width_error` ✅ |
| Glyphs within a word | FLOW (+ run letter-spacing) | ✅ |
| Inter-word gaps | FLOW when Δ≤ε vs space-advance model (measured: usually ≤0.08px); ANCHOR next word otherwise | gaps derivable ✅ |
| Ligatures/kerning | disabled in CSS (matches measurement) ✅ done | — |

## Minimum rendering model (design only)

**One model, selective anchoring — the Adaptive ladder applied to the
renderer.** Everything flows by default; an element becomes absolutely
anchored only where the measurement layer proves flow diverges:

```
LINE   anchored by BASELINE (always; strut pinned so mixed sizes can't move it)
 └── RUN     flows — anchored (left + rise) when boundary jump or rise ≠ 0
      └── WORD    flows — re-anchored when cumulative residual > 0.5px
           └── GLYPH  (M2, only for flagged words — e.g. ChauncyPro optical kerning)
```

Crucially: the anchor decisions consume data the engine ALREADY produces
(`WordBox.x`, `width_error`, `WordMeasurement`, run boundaries) — the
renderer consumes decisions, never recomputes them (ADR-002 discipline).
This is not a return to universal word-pinning: on this page, ~90% of words
flow; anchors land only at run boundaries, rise changes, and every ~2–4
words in optical-kerned display text.

**Two modes from the same IDM** (per the user's proposal):
- **Mode 1 — Production Preview:** the ladder above with a loose threshold
  (anchor at run level only). Fast, editable, minimal DOM.
- **Mode 2 — Pixel Proof:** tight thresholds (word re-anchoring on, M2
  glyph placement where flagged). Acrobat-grade.

## Prerequisites surfaced by this investigation (not yet implemented)

1. **Extract per-run baseline rise** (Mechanism A) — texttrace per-glyph y →
   `Run.rise` (field already reserved). Small extraction addition; the only
   engine-side gap this investigation found.
2. Renderer: baseline-anchored line placement + pinned strut (Mechanism C).
3. Renderer: selective anchors from existing measurements (Mechanisms A/B).
4. Verification: the browser oracle (M-R5) is the natural acceptance test
   for this model — browser glyph rects vs PDF glyph origins, per line.

**No code was changed for this report.**
