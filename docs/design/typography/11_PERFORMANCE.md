# 11 — Performance for Very Large Documents (Deliverable 12)

Targets (unchanged from ARCHITECTURE.md, restated for the typography
engine): 3,000 pages · 100,000 text objects · 50,000 images · large
dictionaries and scientific books — **without architectural change**.

## Backend (reconstruction) budget

- **Per-page, streaming, independent.** Every reconstruction stage
  processes one page at a time and never holds the whole document's tree in
  memory at once. The `PipelineEngine` already runs stages page-scoped; the
  660-page dictionary reconstructs in ~2 min today.
- **Font metrics cached per file, not per use** (02): a handful of fonts
  across thousands of pages → bounded memory. Kern pairs memoized.
- **Glyph nodes only where needed** (01/M2): per-glyph data is materialized
  only for words whose metric residual exceeds threshold, not for all 100k
  words. Typical documents store glyphs for a small fraction.
- **Vector/drawing analysis** (tables/SVG/math) is the heaviest step;
  gated per page by cheap pre-checks (does the page have drawings? math
  fonts? multiple columns?) so text-only pages skip it entirely.
- **Parallelism:** pages are independent → the backend-agnostic engine can
  fan out to workers (Celery/RQ/K8s — already the reserved seam) for very
  large jobs. Not required for correctness; a throughput lever.

## Serialization

- `idm.json` stays the on-disk contract; the tree is nested but still
  per-project. For 3,000-page documents, consider **per-page IDM shards**
  (`idm/page_XXXX.json`) so the frontend fetches only the pages it renders
  — a natural extension of the existing static mount, no API redesign.

## Frontend (unchanged rules, reaffirmed)

- Windowed viewer: ≤ ~9 mounted iframes regardless of page count (shipped,
  verified on 660 pages → 3 mounted).
- Document Manager: lazy, LRU-capped; never parses the whole tree into
  React state.
- Thumbnails virtualized; search indexed in background chunks; validation
  per-page in a Web Worker.
- Per-page shards (above) make the tree's extra richness free on the
  frontend — it only ever holds the visible window.

## Output generation

- Per-page HTML/CSS files (shipped) keep generated output windowable and
  cache-friendly. Semantic/EPUB output streams page-by-page into the
  package.
- Style deduplication (07) keeps total CSS size sub-linear in run count.

## Budgets to hold per milestone (re-checked against corpus 09)

| Operation | Budget |
|---|---|
| Reconstruct + generate, per page | < 60 ms text-only; < 250 ms w/ tables/math |
| 3,000-page full conversion | streams; flat peak memory |
| Frontend open project | < 500 ms (shard-fetched) |
| Page navigation | < 50 ms · ≤ 9 iframes |

Regression on any budget fails CI alongside the accuracy metrics.
