# 05 — MathML Reconstruction Engine (Deliverable 6)

Goal: reconstruct semantic **MathML** from positioned glyphs; fall back to
SVG/image only when reconstruction is impossible.

## Reality check (sets expectations honestly)

PDF discards math structure — there is no "equation object," only
positioned glyphs (often in math fonts: Computer Modern, STIX, Cambria
Math, Latin Modern). Reconstruction is **inference from geometry + font
semantics**, so it is confidence-gated and staged. This is the hardest
engine; the roadmap (10) sequences it late and incrementally.

## Detection (is this region math?)

Signals: math fonts in use; isolated centered display blocks; operator
glyphs (∑ ∫ √ ∏ ± × relations); sub/superscript geometry (small glyphs
offset from baseline); fraction bars (short thin h-rules between vertically
stacked runs); stretchy delimiters (tall ( [ { | matched pairs).

## Layout analysis → MathML tree

Recursive geometric parsing into presentation MathML:

- **Baseline runs** → `<mrow>` of `<mi>`/`<mn>`/`<mo>` (identifier / number
  / operator classified by Unicode + font).
- **Superscript / subscript** → `<msup>` / `<msub>` / `<msubsup>` from
  vertical offset vs the base run's baseline and reduced size.
- **Fraction** → `<mfrac>` from a thin h-rule with numerator above /
  denominator below, horizontally centered.
- **Root** → `<msqrt>`/`<mroot>` from a radical glyph + overline extent.
- **Matrix** → `<mtable>` from a delimiter pair enclosing a grid (reuses
  the Table engine's grid detection, 04).
- **Big operators** (∑ ∫ ∏) → `<munderover>`/`<msubsup>` with limits from
  glyphs above/below.
- **Greek / operators** → correct Unicode via the font's cmap + a
  math-symbol table (glyph name → Unicode).
- **Chemical formulae** → subscripted `<mn>` runs (H₂O); detected as math
  or via a chemistry heuristic → MathML or `<sub>`.

## Inline vs display

Inline math stays in the paragraph run stream (`<math display="inline">`);
display math is its own centered block (`<math display="block">`).

## Fallback ladder

1. Full MathML (confident parse).
2. Partial MathML with raw `<mo>`/`<mtext>` for unparsed sub-regions.
3. **SVG** of the region's vector/glyph outlines (crisp, scalable) when
   structure can't be inferred.
4. Cropped raster (last resort; the background already has it).

Never emit malformed MathML — "No broken equations" = confident MathML or
an honest visual fallback.

## Validation (08)

MathML well-formedness; every source glyph accounted for; render-back
width/height ≈ source region bbox.
