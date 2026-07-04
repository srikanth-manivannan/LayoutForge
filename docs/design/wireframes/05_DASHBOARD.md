# Wireframe 5 — Dashboard (Launcher)

The launcher, not a home base (frozen rule): `Start → Dashboard → open
project → Workspace`, returning only to switch titles. Answers Marcus's
question — *in flight? ready? failed?* — in five seconds.

## Default state

```
┌────┬──────────────────────────────────────────────────────────────────────┐
│ ●🏠│  LayoutForge Studio                                    [⌘K Palette]  │
│ 📁 │                                                                      │
│ ⬆  │  ┌────────────────────────────────────────────────────────────────┐ │
│ ⚙  │  │ ‹1›            ⬆  Drop a PDF anywhere to import                │ │
│    │  │                     or  [Import PDF]                           │ │
│    │  └────────────────────────────────────────────────────────────────┘ │
│    │                                                                      │
│    │  ┌──────────────────────────────┐  ┌──────────────────────────────┐ │
│    │  │ ACTIVE CONVERSION ‹2›        │  │ PRODUCTION SUMMARY ‹3›       │ │
│    │  │ Science Textbook Gr.4        │  │  4 Ready · 1 Processing      │ │
│    │  │ ▸ Extract Text  ██████░ 7/10 │  │  1 Failed · 12 Delivered     │ │
│    │  │ p 214/890 · ~3 min left      │  │  (each count → filtered      │ │
│    │  │ [View logs] [Open when ready]│  │   Projects list)             │ │
│    │  └──────────────────────────────┘  └──────────────────────────────┘ │
│    │                                                                      │
│    │  RECENT PROJECTS ‹4›                                    [All →]     │
│    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│    │  │[thumb]   │ │[thumb]   │ │[thumb]   │ │[thumb]   │               │
│    │  │Book Title│ │Magazine  │ │Gov Report│ │Textbook  │               │
│    │  │27p ·Ready│ │64p ·Ready│ │112p·Fail⚠│ │890p·Proc…│               │
│    │  │ [Open]   │ │ [Open]   │ │ [Details]│ │ [Monitor]│               │
│    │  └──────────┘ └──────────┘ └──────────┘ └──────────┘               │
├────┴──────────────────────────────────────────────────────────────────────┤
│ ● backend ok · storage ok · static ok · API v1 ‹5›                        │
└────────────────────────────────────────────────────────────────────────────┘
```

## Callouts

- **‹1› Drop zone** — the entire screen is a drop target (banner is the
  affordance). Drop → streams upload → pipeline starts → card ‹2› appears.
  No navigation required to import (≤3-clicks rule: this is 1).
- **‹2› Active conversion** — reuses the PipelineStageList component
  (same one as Import Center + Conversion Monitor). `Open when ready`
  arms a one-shot: toast + auto-enable when the job completes.
- **‹3› Summary** — exact counts using the one status taxonomy; each is a
  filter link into Projects.
- **‹4› Recent projects** — cards with page-1 thumbnail (2B provides
  thumbnails). Primary action follows status: Ready→Open ·
  Processing→Monitor · Failed→Details (which opens the failing stage's
  log — specific, actionable).
- **‹5› Env health** — the four environment checks (backend/storage/
  static/API) live in the status bar here too; blocking red banner only
  for the two fatal cases (existing behavior, kept).

## States

1. **First run (no projects)** — hero drop zone + one sentence ("Import a
   PDF to create your first project") + sample-PDF link. Teaches the one
   gesture that matters.
2. **Nothing in flight** — Active Conversion card collapses; recents grow.
3. **A failure exists** — Failed count and card surface at the top of
   recents; never hidden.

## Scale check

Recents capped (8); Production Summary is counts from the summary
endpoint; the full (virtualized) list lives in Projects. The Dashboard
never renders unbounded data.

## Principles check

14 ✅ import happens here, no tab-hopping · 5 ✅ conversions never block ·
launcher rule ✅ nothing in the production loop routes back here ·
3 ✅ all data from summary/jobs endpoints (IDM-derived).

## Open questions

1. Does Marcus need a "this week: delivered/failed" mini-trend on the
   summary card now, or is that P7 territory? Recommend P7 — counts only
   for 2A/2C.
2. `Open when ready`: auto-navigate on completion, or toast-with-button
   (drawn)? Toast recommended — auto-navigation steals focus mid-task.
