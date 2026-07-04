# PERFORMANCE — Scale Targets and Budgets

Performance is a product feature, contractual, and already partially
enforced in architecture (Document Manager caps, windowed viewer). Design
must never assume "the document is small."

## Scale targets

- 2,000+ pages per document
- 100,000 text objects; 50,000 images; thousands of fonts; thousands of
  vector objects
- Files 5 MB → 50 MB → 250 MB → 1 GB (future)

## Techniques (mandated, mostly implemented or reserved)

- **Windowed rendering** — only current page ± window mounts (≈9 iframe cap,
  LRU eviction) — 2B
- **Thumbnail virtualization** — plain `<img loading="lazy">`, windowed — 2B
- **Incremental search** — background-chunked index building — 2B
- **LRU caches** — IDM slices, thumbnails, summaries, validation results
  (Document Manager owns all of them)
- **Streaming** — uploads stream to temp storage today; pipeline streaming is
  Phase 2.5
- **Memory efficiency** — never hold the whole document in React state;
  idm.json consumed incrementally; Properties loads only the selected object;
  validation runs page-by-page off the main thread

## Budgets (verified under Phase 2.5 stress tests)

| Operation | Budget |
|---|---|
| Workspace startup | < 2 s |
| Open project | < 500 ms |
| Page navigation | < 50 ms |
| Zoom | < 16 ms (one frame) |
| Selection → Properties | < 10 ms |
| Property update | < 5 ms |

## UX consequences

- Counts, not lists: the Explorer summarizes ("Pages (2,000)") instead of
  rendering thousands of nodes — already the 2A behavior.
- Every list in the product is virtualized by default.
- Progress must be visible for anything > 200 ms; skeletons over spinners.
