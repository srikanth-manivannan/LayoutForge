# Wireframe 1 — Workspace · Proof Mode

The flagship screen. Priya lives here. Default mode when a project opens.

## Default state (reference title open, page 12, 150%)

```
┌────┬──────────────────────────────────────────────────────────────────────┐
│ 🏠 │ [⬆ Import] [⇄ Compare] [✓ Validate] [♿ A11y] [⬇ Export]  ‹1›        │
│ 📁 │                                        [🔍 Search] [⌘K]              │
│ ⬆  ├───────────────┬───────────────────────────────────┬──────────────────┤
│ ⚙  │ EXPLORER ‹2›  │ ● Proof │ Compare │ Validate ‹3›  │ PROPERTIES ‹8›   │
│    │               ├───────────────────────────────────┤ ┌──────────────┐ │
│────│ ▾ Book Title  │ ‹4› ◀ 12 / 27 ▶  [Go]  100▾%     │ │TextBlock     │ │
│ 👁 │   ▸ Source    │     [Fit W][Fit P][1:1] [▤ mode]  │ │tb-8f3a…      │ │
│ ⇄  │   ▸ Pages 27  ├────┬──────────────────────────────┤ ├──────────────┤ │
│ ✓  │   ▸ Fonts 5   │‹5› │                              │ │▾ Geometry    │ │
│ ≡  │   ▸ Images 40 │ ▫  │   ┌────────────────────┐     │ │  x 84  y 210 │ │
│    │   ▸ CSS       │ ▫  │   │                    │     │ │  w 412 h 56  │ │
│    │   ▸ Output    │ ▫  │   │   PAGE CANVAS ‹6›  │     │ │▾ Typography  │ │
│    │   ▸ Reports   │[▫] │   │   (iframe, page 12)│     │ │  Font: Kidst…│ │
│    │               │ ▫  │   │   ┌─────────┐      │     │ │  Size: 24pt  │ │
│    │               │ ▫  │   │   │selected │◀─────┼─────┼─│▸ Appearance  │ │
│    │               │ ▫  │   │   └─────────┘      │     │ │▸ Metadata    │ │
│    │               │ ⋮  │   └────────────────────┘     │ │▸ Advanced    │ │
│    │               │    │                              │ └──────────────┘ │
│    ├───────────────┴────┴──────────────────────────────┴──────────────────┤
│    │ ▾ BOTTOM DOCK  Job log │ Application │ Conversion │ Performance ‹7› │
│    │   12:03 [HTML] page_0012.html generated (48ms)                      │
├────┴──────────────────────────────────────────────────────────────────────┤
│ Book Title · p 12/27 · 150% · 1 selected (TextBlock) · ● backend ok ‹9›  │
└────────────────────────────────────────────────────────────────────────────┘
```

## Callouts

- **‹1› Quick Actions** — the frozen seven, nothing else. Compare/Validate/
  A11y/Export switch modes; Import jumps to Import Center; Search focuses
  document search; ⌘K opens the palette. All are command dispatches.
- **‹2› Explorer** — counts, not lists (`Pages 27`, `Fonts 5`). Expanding
  `Pages` shows a *windowed* list. Node click → selects in canvas/properties
  where addressable. Context menu on every node (commands).
- **‹3› Mode strip** — `Proof` active (●). `Edit`/`A11y`/`Export` render
  disabled with honest tooltips ("Phase 3/4/5") until their phase lands.
  `Ctrl+1..5` switches.
- **‹4› Mode toolbar (Proof)** — page nav (◀ ▶, editable `12/27`, Go-to),
  zoom preset dropdown + `Fit Width / Fit Page / 1:1`, view-mode toggle
  (Continuous / Single / Facing / Book — 2B).
- **‹5› Thumbnail rail** — windowed plain `<img>` thumbnails; `[▫]` marks
  current page; click = navigate; collapsible; scrollbar doubles as a page
  position indicator on large docs.
- **‹6› Page canvas** — the hero (≥55% width at defaults). Same-origin
  iframe, untouched golden rendering path. Click object → selection
  outline + `SelectionChanged`. Neutral gutter, never themed.
- **‹7› Bottom dock** — tabs per log stream; collapsed by default to a
  single status row, expands on click or `Ctrl+J`.
- **‹8› Properties** — groups per approved taxonomy; empty state when
  nothing selected: "Click any object on the page". Font name links to the
  Explorer font entry.
- **‹9› Status bar** — identity + position + selection + env health + job
  state. Every segment clickable (e.g. zoom → zoom menu, env → recheck).

## Key states

1. **Opening (< 500 ms budget):** shell + Explorer skeleton render
   immediately; canvas shows page skeleton; no full-screen spinner ever.
2. **Search (`Ctrl+F`):** inline bar drops below the mode toolbar —
   `[🔍 query] 3/17 ◀▶ · indexing 42%…` — results jump+highlight; index
   builds in background chunks, searchable while partial.
3. **Docks collapsed (`Ctrl+B`+`Ctrl+J`+`Ctrl+Alt+B`):** canvas ≥ 85%
   width; mode strip and status bar remain.
4. **Error (page fails to load):** in-canvas card — reason, expected
   endpoint, suggestions (PreviewError pattern) — never a blank canvas.

## Scale check (2,000-page textbook)

Explorer shows `Pages 2,000` (count node, windowed expansion); thumbnail
rail virtualizes (~30 mounted); go-to-page is the primary long-range nav;
≤ ~9 mounted page iframes (LRU). Nothing else changes.

## Principles check

0 ✅ canvas untouched golden path · 1 ✅ no route changes · 2 ✅ one
selection pipeline · 4 ✅ counts/windows · 5 ✅ no blocking states ·
6 ✅ all controls are commands · 8 ✅ full keyboard path · 14 ✅ single tab.

## Open questions for review

1. Thumbnail rail: left of canvas (drawn) or right, adjacent to
   Properties? Left matches Acrobat muscle memory — recommended.
2. Should `Go to page` live in the palette only, or also as the editable
   page field (drawn)? Drawn version recommended for operators.
3. Bottom dock default: collapsed (drawn) or open on first project open?
