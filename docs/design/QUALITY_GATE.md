# Quality Gate — Definition of "Production Ready"

The objective, permanent bar every change to the reconstruction engine must
clear. This is what turns "looks good" into "measurably good" and protects
the architecture's maturity as new capabilities are added. Backed by the
per-conversion `report.json` (M1.7) and the regression suite.

## Targets

| Metric | Target | Enforced by |
|---|---|---|
| Visual fidelity (overlay vs source) | ≥ 99.9% (worst-case word width error < 1px after M2) | benchmark corpus + browser measurement |
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
