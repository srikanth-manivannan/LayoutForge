# 08 — Validation Rules (Deliverable 9)

Validation is measurable and automated (extends the shipped Web-Worker
Validation engine). Each rule has a severity and a machine check. Target
(Output Quality): no overlapping text, no baseline drift, no font fallback,
no collapsed paragraphs, no broken tables/equations.

## Typography rules

| Rule | Check | Severity |
|---|---|---|
| No font fallback | every rendered run's `document.fonts[family].status == "loaded"`; no run resolves to a generic family | error |
| Width fidelity | per run/word, `|actualWidth − expectedWidth| / expected < ε` (Canvas measure vs metric) | warn→error by margin |
| Baseline on grid | each line's baseline within τ of its paragraph grid | warn |
| No overlap | no two runs/words in a line have overlapping x-extents; no two lines overlap in y | error |
| No collapsed paragraph | every source line maps to a rendered line; paragraph line-count preserved | error |
| Glyph coverage | every source glyph has a target glyph (no `.notdef`/tofu) | error |
| Missing glyph in subset | source char absent from font cmap | warn |

## Structure rules

| Rule | Check | Severity |
|---|---|---|
| Table integrity | rectangular grid; spans consistent; no uncovered/overlapping cells; header present for data tables | error/warn |
| MathML well-formed | parses as MathML; all source glyphs consumed; render-back bbox ≈ source | error |
| Reading order | Region order monotonic; columns L→R/R→L; no orphaned region | warn |
| List integrity | markers consistent; nesting balanced | warn |
| Reference resolution | every noteref/cross-ref target exists | error |
| Image presence | every figure has a resolvable asset (reflowable) | error |

## Proofing oracle (the ground-truth check)

The strongest validation is **overlay-vs-raster**: render the reconstructed
page and diff against the background raster (which is the PDF's own
composite). Per-region pixel difference above threshold → a finding pinned
to that region. This is the Compare panel made quantitative, and it's the
single metric that operationalizes "99.99% visual accuracy."

## How it runs

- Backend: structural checks during reconstruction (fast, per-stage).
- Frontend Web Worker (shipped): per-page, progressive, cancelable —
  gains the typography + proofing-oracle rules. Findings ride the one
  selection pipeline (click → jump → highlight, shipped).
- Regression: the benchmark corpus (09) runs these rules in CI, gating
  accuracy metrics per document class.
