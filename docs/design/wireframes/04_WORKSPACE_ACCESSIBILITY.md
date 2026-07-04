# Wireframe 4 — Workspace · Accessibility Mode (Phase 5 preview)

Wireframed now to **prove the frozen shell holds a whole future module
without change** — nothing here requires new architecture. Ships in
Phase 5; until then the mode tab renders disabled with an honest tooltip.

Elena's mode: reading order, alt text, conformance — inside the same
workspace, on the same selection pipeline.

## Default state

```
┌────┬──────────────────────────────────────────────────────────────────────┐
│ …shell identical…                                                         │
│    ├───────────────┬───────────────────────────────────┬──────────────────┤
│    │ EXPLORER      │ Proof │ Compare │ Validate │ ●A11y │ ‹5› ALT TEXT     │
│    │               ├──────────────┬────────────────────┤ ┌──────────────┐ │
│    │               │ READING      │  PAGE CANVAS ‹2›   │ │ img-4b2a…    │ │
│    │               │ ORDER ‹1›    │  ┌──────────────┐  │ │ [thumbnail]  │ │
│    │               │              │  │ ①────┐       │  │ ├──────────────┤ │
│    │               │ p12          │  │ ┌────▼───┐   │  │ │ Alt text:    │ │
│    │               │ ① Heading    │  │ │ ②      │   │  │ │ ┌──────────┐ │ │
│    │               │ ② Body text  │  │ └────┬───┘   │  │ │ │A brown   │ │ │
│    │               │ ③ Image ⚠    │  │  ┌───▼────┐  │  │ │ │dog runs… │ │ │
│    │               │ ④ Caption    │  │  │ ③  ⚠  │  │  │ │ └──────────┘ │ │
│    │               │              │  │  └───┬────┘  │  │ │ [AI draft]‹6›│ │
│    │               │ ‹3› [↑][↓]   │  │   …④        │  │ │ [☐Decorative]│ │
│    │               │ reorder ·    │  └──────────────┘  │ │ [Save]       │ │
│    │               │ drag or keys │   numbered badges  │ └──────────────┘ │
│    │               ├──────────────┴────────────────────┤                  │
│    │               │ ‹4› ⚠ 3 images missing alt · ✓ order confirmed 11/27 │
└────┴───────────────┴────────────────────────────────────┴─────────────────┘
```

## Callouts

- **‹1› Reading-order list** — the page's elements in IDM reading order
  (`NormalizeIdmStage` already computes it; P5 makes it editable).
  Selecting a row selects the object — same `SelectionChanged` event.
- **‹2› Canvas overlay** — numbered badges + flow arrows over the page;
  an operator-invoked overlay, so Principle 13 is satisfied. Toggle: `R`.
- **‹3› Reorder** — drag or `Alt+↑/↓`; each move is an undoable command
  (`a11y.moveInReadingOrder`).
- **‹4› Progress strip** — remediation is per-page work; exact counts of
  what remains ("3 images missing alt · order confirmed 11/27").
- **‹5› Alt-text editor** — replaces Properties content while an image is
  selected in A11y mode (same right dock, contextual content — the
  approved Modes behavior). Decorative checkbox = explicit empty-alt.
- **‹6› [AI draft]** — Phase 6 hook: dispatches `ai.generateAltText`,
  fills the field as a *draft* the specialist reviews. AI is a command in
  a panel; nothing auto-ships (approved AI rule).

## Additional states

1. **Conformance report** — `[Generate report]` in the mode toolbar →
   async build → lands in Explorer › Reports + Output (packaged with
   export). WCAG 2.1 AA / EPUB Accessibility 1.1 checklists with
   pass/warn/fail per criterion — same FindingsTable component as
   Validation.
2. **A11y findings in Validation** — a11y checks also register as a
   Validation category once P5 lands (one findings infrastructure, two
   entry points).

## Scale check

Reading-order list renders one page at a time (never the document);
"order confirmed" state persists per page so a 2,000-page remediation is
resumable.

## Principles check

10 ✅ the module itself · 2 ✅ same selection · 6 ✅ every mutation is a
command (undoable) · 12 ✅ ships as panels+commands+validators, zero shell
change · 14 ✅ Elena never leaves the tab.

## Open questions

1. Reading-order list: left of canvas (drawn, replaces thumbnails in this
   mode) or as a right-dock tab? Left recommended — it *is* the nav here.
2. Should "order confirmed" be per-page explicit sign-off (drawn) or
   implicit on edit? Explicit recommended — it's an auditable deliverable.
