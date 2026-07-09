# Quality Gate — Definition of "Production Ready"

The objective, permanent bar every change to the reconstruction engine must
clear. This is what turns "looks good" into "measurably good" and protects
the architecture's maturity as new capabilities are added. Backed by the
per-conversion `report.json` (M1.7) and the regression suite.

## Targets

**Character fidelity = 100% is the PRIMARY success criterion.** Pixel-perfect
rendering is valuable, but if a single character disappears ("much" →
"mu h"), the document is no longer faithfully reconstructed. Text
preservation is the first gate every conversion must pass. A character may
be *substituted* (rendered visibly in a fallback font, counted and reported)
— it may **never** be lost (painted as nothing). Enforced structurally: the
blank-mapping purge unmaps any empty non-whitespace glyph after the
sibling-subset merge, so browsers always fall back visibly.

| Metric | Target | Enforced by |
|---|---|---|
| **Character fidelity** | **100.0%** (`fidelity.chars_lost == 0`, always) | blank-mapping purge (structural) + `report.json` + corpus tests |
| **Unicode fidelity** | **100.0%** (DOM text == extracted glyph-stream text) | extraction is glyph-stream-sourced; corpus assertion |
| Visual fidelity (overlay vs source) | ≥ 99.9% (worst-case word width error < 1px after M2) | benchmark corpus + browser measurement |
| Font fidelity | ≥ 99.9% (chars painted in their own font; substitution rate reported) | `fidelity.character_substitution_rate` in `report.json` |
| Reading order | ≥ 99.9% | M3-WP3 + Validation (as it lands) |
| Table fidelity | ≥ 99% (confidence-gated; never a wrong table) | M3-WP4 + Validation (as it lands) |
| Math fidelity | ≥ 99% (MathML ladder; never flattened) | M4 + Validation (as it lands) |
| Unexpected font fallbacks | **0** (embedded font with no served file) | `test_engine_stabilization.test_no_unexpected_font_fallbacks` |
| Validation regressions | 0 new errors on the corpus | Validation engine (2C) over corpus |
| Reconstruction profile | populated; `glyph_fraction` within document-class band | `test_benchmark_profile_is_populated_and_sane` |
| Mean reconstruction confidence | ≥ 0.75 (healthy document) | benchmark test + `report.json` |
| Memory growth | < 10% over recorded baseline (per stage) | `report.json` peak_memory_mb + review |
| Large-PDF support | 3,000+ pages, windowed viewer ≤ ~9 iframes | frontend windowing tests + manual |
| Performance | no order-of-magnitude regression | `test_performance_budget_many_pages` + `report.json` |
| Benchmark corpus | 100% pass | the regression suite |

"Visual accuracy" is defined against the **rasterized source page as ground
truth** (the overlay must match it), measured as text-block ink width vs
declared width and baseline offset.

## The benchmark corpus

The regression harness (`tests/test_engine_stabilization.py`) runs against a
committed **synthetic corpus** (`make_rich_pdf_bytes`) today; real
representative documents plug into the same harness. The target corpus
(from the architecture) spans: children's picture books, dense dictionaries,
PrinceXML/TeX output, academic journals (multi-column), scientific/math
books, government forms, and multilingual (RTL/CJK) titles. Each becomes a
regression fixture with recorded baselines (profile, accuracy, memory,
timing) so a release can be compared to the last:

```
v0.8  kerning 18%  →  v0.9  11%  →  v1.0  4%
```

## How a change clears the gate

1. `pytest` green (unit + benchmark + performance regression).
2. `report.json` for the corpus shows no unexpected fallbacks, profile
   within band, memory within +10%, no timing blow-up.
3. Browser proofing pass on the reference titles (Compare overlay).
4. Frontend build + windowing assertions green.

A change that regresses any target is not merged until the target is
restored or the target is deliberately, explicitly revised (with an ADR if
architectural).
