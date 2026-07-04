# 02 — Font Metrics Engine (Deliverable 4)

"Measure, never estimate." One engine every reconstruction stage consults
for glyph and font metrics. Formalizes what several shipped font fixes
(width-fitting, bare-CFF, base-14) already do ad hoc.

## Inputs it must read

TTF, OTF, CFF/Type1C (wrapped to OTF), CID/Type0, subset fonts,
non-embedded standard fonts (base-14).

## Metrics it exposes (per font)

`units_per_em`, `ascent`, `descent`, `cap_height`, `x_height`,
`line_gap`, `italic_angle`, `is_fixed_pitch`; per glyph: `advance`,
`left_side_bearing`, bounding box; **kerning** (GPOS pair kerning + legacy
`kern` table); OpenType feature tables (liga, kern, smcp, onum, …) for
detection.

## Three-tier measurement (in priority order)

1. **Embedded font file via fontTools** — exact `hmtx` advances, cmap,
   GPOS/kern. The default for embedded fonts (already loaded by
   `normalize_idm.load_font_metrics`).
2. **MuPDF built-in metrics** — for the base-14 standard fonts
   (`fitz.Font(name)`), whose metrics equal the local Times/Arial/Courier
   we map them to. (Shipped as `Base14Metrics`.)
3. **Browser Canvas `measureText`** — a *frontend* validation oracle only
   (the reconstructed HTML runs in the same engine that will render it),
   used by the Validation worker to confirm `actualWidth ≈ expectedWidth`.
   Never a source of truth for generation (backend has no DOM).

Estimation (½-em fallback for a missing glyph) is allowed **only** to
decide *coverage* (skip fitting a word if too many glyphs are unmeasured) —
never to produce a width we then render.

## Kerning: the last-mile width source

The residual on strongly-kerned words (`HTML`, `Ti…`) is unkerned
sum-of-advances vs the PDF's kerned width. The engine adds:

- `kern_pair(gid_a, gid_b) -> dx` from GPOS/kern.
- `measure_run(text, font, size, features) -> (width, per_glyph_x[])`
  applying advances **and** kern pairs (and later liga/GSUB).

`per_glyph_x` is what the Baseline/Glyph engine (03/M2) uses to pin glyphs
when a word's residual exceeds threshold — turning "uniform letter-spacing
approximation" into "exact per-glyph placement."

## Caching (large-document safe)

One metrics object per **font file** per document (documents reuse a
handful of fonts across thousands of pages — already the pattern in
`_load_all_font_metrics`). Kern lookups memoized per pair. Bounded memory
regardless of page count.

## API sketch (`pipeline/typography/font_metrics.py`)

```python
class FontMetricsEngine:
    def metrics(self, font_ref) -> FontFaceMetrics        # cached per file
    def measure(self, text, font_ref, size, *, features=()) -> RunMeasure
        # RunMeasure: width, expected_width, glyph_advances, glyph_x, missing
    def kern(self, font_ref, a: str, b: str) -> float
    def has_feature(self, font_ref, tag: str) -> bool
```

Reuses `FontMetrics`/`Base14Metrics`/`natural_text_width` (already in
`normalize_idm.py`) as the tier-1/2 backends; adds kern + glyph_x.
