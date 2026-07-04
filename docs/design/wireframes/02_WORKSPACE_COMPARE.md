# Wireframe 2 — Workspace · Compare Mode

The proofing power tool: source raster vs. reconstruction. Entered from
Quick Actions, mode strip, or `Ctrl+2` — **always inheriting the current
page, zoom, and selection from Proof mode.**

## State A — Overlay (default)

```
┌────┬──────────────────────────────────────────────────────────────────────┐
│ …shell identical (Quick Actions · NavRail · Explorer · Properties)…       │
│    ├───────────────┬───────────────────────────────────┬──────────────────┤
│    │ EXPLORER      │ Proof │ ● Compare │ Validate       │ PROPERTIES       │
│    │               ├───────────────────────────────────┤                  │
│    │  (unchanged)  │ ‹1› [● Overlay | Split]  ◀ 12/27 ▶│  (same selected  │
│    │               │ ‹2› Overlay opacity ▁▂▃▅▆ 60%     │   object as      │
│    │               │ ‹3› [☐ Difference emphasis]       │   Proof mode)    │
│    │               ├───────────────────────────────────┤                  │
│    │               │                                   │                  │
│    │               │   ┌───────────────────────────┐   │                  │
│    │               │   │ SOURCE RASTER (base) ‹4›  │   │                  │
│    │               │   │  + reconstruction @ 60%   │   │                  │
│    │               │   │    over it                │   │                  │
│    │               │   │      [drift visible as    │   │                  │
│    │               │   │       ghosting]           │   │                  │
│    │               │   └───────────────────────────┘   │                  │
│    │               │ ‹5› base: [Source ▾]  overlay:    │                  │
│    │               │     [Reconstruction ▾]  [⇆ swap]  │                  │
└────┴───────────────┴───────────────────────────────────┴──────────────────┘
```

## State B — Split

```
├───────────────────────────────────────────┤
│ [Overlay | ● Split]   ◀ 12 / 27 ▶   150%  │
├─────────────────────┬─────────────────────┤
│  SOURCE ‹6›         ┃  RECONSTRUCTION     │
│  (page 12 raster)   ┃  (page 12 iframe)   │
│                     ┃                     │
│     synced pan/zoom ┃ synced pan/zoom     │
├─────────────────────┸─────────────────────┤
│ ‹7› divider draggable · [⇅ orientation]   │
└───────────────────────────────────────────┘
```

## Callouts

- **‹1› Mode switch** — Overlay ⟷ Split; `O` / `S` while in Compare.
- **‹2› Opacity slider** — keyboard-steppable (arrows = 1%, PgUp/Dn = 10%);
  double-click resets 50%. The single most-used control in this mode.
- **‹3› Difference emphasis** — tints only mismatched regions in
  `--lf-compare-diff` magenta (reserved token; collides with no semantic
  color). Off by default: Principle 13 — nothing paints over the page
  unless the operator asks.
- **‹4› Overlay canvas** — base at 100%, overlay at slider opacity.
  Reuses the shipped `applyAccuracySettings` seam (AccuracyDebugView is
  the proven ancestor — this panel replaces it).
- **‹5› Layer picker** — either layer can be Source raster /
  Reconstruction / Background-only / Overlay-only (the four proven debug
  views, now production-grade). Swap = one click.
- **‹6› Split panes** — pan/zoom locked together, always. Unsynced panes
  are how proofing errors happen; not offered.
- **‹7› Divider** — draggable; orientation toggle (vertical/horizontal —
  horizontal suits wide spreads).

## Key states

1. **Entering Compare** — no reload: same page, zoom, selection. The only
   change is the center surface. (Principle 1 test case.)
2. **Selection carry-over** — the selected object's outline renders in
   both layers/panes; Properties stays populated.
3. **Missing source raster** — honest in-canvas card ("Background raster
   not found for page 12 — re-run conversion"), never a silent blank.

## Scale check

Compare mounts only the current page (±0 — heavier than Proof per page,
so no read-ahead). Page nav still < 50 ms via the already-warm iframe LRU.

## Principles check

0 ✅ this mode IS Principle 0 made visible · 13 ✅ diff emphasis is opt-in
· 2 ✅ selection shared · 8 ✅ `O`/`S`/arrow-keys · 5 ✅ no blocking.

## Open questions

1. Difference emphasis v1: cheap CSS blend (`difference`) or real pixel
   diff in a worker? Recommend CSS blend for 2C, worker diff in 2.5.
2. Is Background-only/Overlay-only worth exposing to operators (drawn in
   layer picker), or keep them palette-only commands?
