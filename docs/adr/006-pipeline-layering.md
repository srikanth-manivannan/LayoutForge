# ADR-006: Reconstruction Pipeline Layering

**Status:** Accepted · 2026-07-04

## Context

`NormalizeIdmStage` had grown to do several unrelated jobs (reading order,
baseline/line metrics, font measurement, adaptive word decisions). Mixed
responsibilities make debugging hard and couple geometry to font logic.
Reconstruction (paragraphs/tables/math) is coming and needs clean seams.

## Decision

Layer the post-extraction pipeline into single-responsibility phases;
extraction stays frozen:

```
Extraction (frozen)
   ↓  Raw IDM
Geometry Normalizer     reading order · baseline · line metrics (no fonts)
   ↓
Typography Analyzer     measure runs/words vs font metrics (kerning, coverage)
   ↓
Adaptive Reconstruction decide mode/reason/confidence per object (ADR-002)
   ↓
Semantic Analyzer       paragraphs · lists · tables · math · columns (M3+)
   ↓  Rich IDM
Writers                 fixed-layout · HTML · XHTML · EPUB · XML · PML
```

Each phase is independent, feature-flagged, and degrades to the prior level
on failure — so a document is never corrupted, and each phase is debuggable
in isolation.

## Consequences / current state

- Implemented as separate modules today:
  `typography/geometry_normalizer.py`, `typography/font_metrics.py`
  (Typography Analyzer's measurement), and
  `typography/adaptive_reconstruction.py` (the engine).
- `NormalizeIdmStage` currently **orchestrates** Geometry → Adaptive
  Reconstruction. It formally splits into registered `PipelineEngine`
  stages when the **Semantic Analyzer** gains real work (M3+); creating
  those stages now would leave them hollow, so the split is staged to avoid
  no-op stages and churn. The module boundaries already enforce
  single-responsibility.
- `Typography Analyzer` measurement lives in `font_metrics.py` and is
  consumed by the engine; it becomes its own stage if/when M2's glyph
  measurement needs to run standalone.
