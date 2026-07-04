# 03 — User Journey

The end-to-end journey for the primary persona (Priya) on the reference
title (27-page children's book), annotated with the screen/panel and the
design requirement each step creates.

## Journey map

| # | Step | Where | What Priya does | Design requirement |
|---|---|---|---|---|
| 1 | Receive | outside app | Customer emails PDF | (Phase 7: watch folder/API intake) |
| 2 | Import | Dashboard → Import | Drags PDF onto the drop zone | Drop target on Dashboard too; upload streams; UI never blocks |
| 3 | Extract + Generate | Import / anywhere | Watches stage progress (Validate → … → Generate HTML) | Live per-stage progress (Conversion Monitor); she can leave and come back |
| 4 | Open | notification → Workspace | Clicks "Ready" toast or project card | `Ready → open workspace` is ONE click; opens < 500 ms |
| 5 | First look | Viewer | Skims pages with `PgDn`, thumbnails rail | Page nav < 50 ms; thumbnails virtualized |
| 6 | Proof | Compare tab | Overlays source raster on reconstruction, drags opacity; split view for tricky pages | Tab switch keeps current page + zoom; opacity slider keyboard-adjustable |
| 7 | Find issues | Validation tab | Runs checks; gets 2 warnings on pages 12, 19 | Findings are rows → click jumps Viewer to page + selects object |
| 8 | Inspect | Properties | Clicks the broken headline; checks Typography group | Selection < 10 ms; font name links to the Resources font entry |
| 9 | Fix | (Phase 3) Viewer edit | Nudges the text block 2px, replaces font | Same selection + command seams; undo (Ctrl+Z) |
| 10 | Re-validate | Validation tab | Re-runs only pages 12, 19 | Incremental re-check, not full re-run |
| 11 | Accessibility | (Phase 5) A11y tab | Confirms reading order, fills alt text | Reading-order overlay on the same canvas |
| 12 | Export | Export | Picks HTML (today) / EPUB fixed-layout (Phase 4) | Export runs async; package appears in Output + download |
| 13 | Deliver | Dashboard | Marks delivered; Marcus sees it on the Dashboard | Status roll-up; report artifacts attached |

## The inner loop (steps 6–10) — the product's heartbeat

```
        ┌──────────────┐
   ┌───▶│    Proof     │ Compare tab
   │    └──────┬───────┘
   │           ▼
   │    ┌──────────────┐
   │    │  Find / Fix  │ Validation → click-through → Properties/(edit)
   │    └──────┬───────┘
   │           ▼
   │    ┌──────────────┐
   └────│  Re-validate │ Validation tab (incremental)
        └──────────────┘
```

Loop cost budget: **switching legs of this loop must cost one keystroke or
one click, and never lose page/zoom/selection context.** This is the single
most important UX requirement in the product.

## Emotional arc to design for

- **Import:** anxiety ("will it convert cleanly?") → answer with visible
  per-stage progress and an honest failure message if not.
- **First proof:** skepticism ("browser tools are toys") → answer with
  pixel-parity in Compare. This moment converts users.
- **Validation pass:** relief → make the all-clear state satisfying and
  quantified ("27/27 pages pass").
- **Delivery:** confidence → attachable reports make her work legible to
  Marcus and the customer.

## Secondary journeys (summarized)

- **Marcus, Monday morning:** opens Dashboard → sees in-flight/stuck/shipped
  in 5 seconds → clicks a stuck job → lands in its Logs. Never enters the
  Viewer.
- **Elena, remediation (P5):** opens a Validated project → A11y tab →
  reading-order overlay → fixes order + alt text → exports conformance
  report. Same workspace, different center tab.
- **David, evaluation:** uploads a 900-page textbook → watches memory stay
  flat while paging (windowing) → reads the plugin directory structure →
  approves.
