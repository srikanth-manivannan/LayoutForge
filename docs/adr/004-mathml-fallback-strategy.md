# ADR-004: MathML Fallback Strategy

**Status:** Accepted · 2026-07-04

## Context

Math is the hardest reconstruction: PDF has only positioned glyphs in math
fonts, no equation structure. Full semantic MathML is ideal (accessible,
reflowable, searchable) but not always inferable. A malformed MathML tree
is worse than none.

## Decision

A strict fallback ladder, each rung an honest, valid output:

```
1. Full MathML        (confident geometric parse of the whole region)
2. Partial MathML     (parsed parts + <mtext>/<mo> for the rest)
3. SVG                (vector outlines of the region — crisp, scalable)
4. Cropped raster     (last resort; the background already has it)
```

Never emit malformed MathML — "No broken equations" means confident MathML
*or* an honest visual fallback. Detection and each rung are
confidence-gated (ADR-003 applied to math).

## Consequences

- Scientific/math documents degrade gracefully instead of failing.
- MathML where possible gives accessibility + reflow; SVG preserves fidelity
  where structure can't be inferred.
- Sequenced late and incrementally (M7): sub/superscript → fractions/roots →
  operators/matrices → chemistry.
- Validation checks MathML well-formedness and render-back bbox vs source.
