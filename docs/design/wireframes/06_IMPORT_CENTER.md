# Wireframe 6 — Import Center

`/conversion` — the dedicated intake surface. Same drop-to-import gesture
as the Dashboard (shared ImportDropZone component); adds the full
pipeline view and, later (P7), the batch queue.

## State A — Idle

```
┌────┬──────────────────────────────────────────────────────────────────────┐
│ 🏠 │  Import                                                              │
│ 📁 │                                                                      │
│ ●⬆ │   ┌────────────────────────────────────────────────────────┐        │
│ ⚙  │   │                                                        │        │
│    │   │              ⬆                                         │        │
│    │   │   Drop PDF here, or [Choose file] ‹1›                  │        │
│    │   │   PDF up to 250 MB · processed on this server          │        │
│    │   │                                                        │        │
│    │   └────────────────────────────────────────────────────────┘        │
│    │                                                                      │
│    │   RECENT IMPORTS ‹2›                                                 │
│    │   Book Title        27p    Ready      2 min ago    [Open]            │
│    │   Gov Report       112p    Failed ⚠   1 hr ago     [Details]         │
└────┴──────────────────────────────────────────────────────────────────────┘
```

## State B — Converting (the honest pipeline view)

```
│   Science Textbook Gr.4.pdf · 48 MB                                  │
│   Upload      ████████████████████  done (streamed) ‹3›              │
│   ─────────────────────────────────────────────────────              │
│   PIPELINE ‹4›                                                       │
│   ✓ Validate            12 ms                                        │
│   ✓ Metadata            31 ms                                        │
│   ✓ Render Backgrounds  38 s                                         │
│   ✓ Extract Fonts       2.1 s · 14 fonts (2 sanitized)               │
│   ✓ Extract Images      12 s · 214 images                            │
│   ▶ Extract Text        ██████░░░ p 214/890                          │
│   ○ Normalize IDM                                                    │
│   ○ Persist Assets                                                   │
│   ○ Generate CSS                                                     │
│   ○ Generate HTML                                                    │
│   ─────────────────────────────────────────────────────              │
│   ‹5› [View live log]              est. ~3 min remaining             │
│   You can leave this page — progress continues. ‹6›                  │
```

## State C — Failed (specific, actionable)

```
│   ✕ Extract Fonts — failed                                           │
│   Font "Frutiger-Cn" subset is malformed (fontTools:                 │
│   bad cmap table). Conversion stopped at stage 4/10.                 │
│   [View conversion log] [Retry] [Report issue] ‹7›                   │
```

## State D — Complete

```
│   ✓ All stages complete · 890 pages · 4 min 12 s                     │
│   [Open workspace →]  (primary)   [Import another]                   │
```

## Callouts

- **‹1› Drop zone** — same shared component as Dashboard; keyboard path:
  `Choose file` is focusable, palette has `import.pdf`.
- **‹2› Recent imports** — job-centric view (vs. Projects' title-centric
  list); failures persist here until retried or dismissed.
- **‹3› Upload** — streamed (existing behavior); upload and pipeline are
  separate bars — a stalled network is distinguishable from a slow stage.
- **‹4› Pipeline stage list** — the ten real stages by name, with real
  per-stage results ("2 sanitized" is the font-sanitization story made
  visible). This is THE shared component: Dashboard card and 2C
  Conversion Monitor render the same data smaller.
- **‹5› Live log** — expands bottom-sheet with the conversion log stream
  tail (the `/api/logs` endpoint) — no navigation.
- **‹6› Leave-safe** — explicit reassurance; job continues server-side,
  Dashboard card + toast track it (Principle 5).
- **‹7› Failure actions** — stage-specific message (from the real error
  event), retry re-runs the job, log opens pre-scrolled to the failure.

## Scale check

An 890-page textbook shows per-page progress within stages (`p 214/890`);
stage list length is fixed (10) regardless of document size; recent
imports virtualize past ~50.

## Principles check

5 ✅ leave-safe async · 7 ✅ per-stage streaming truth · 3 ✅ stage names
match the real pipeline enum (one vocabulary, `PipelineStage`) ·
0 ✅ surfacing sanitization counts makes fidelity work visible, not magic.

## Open questions

1. Multiple simultaneous uploads in 2C (queue them visually) or hold
   strictly to one-at-a-time until P7 batch? Recommend: allow queueing
   uploads, process serially — honest about backend capability.
2. Should `Retry` offer "retry from failed stage" once 2.5 adds stage
   checkpointing, or always full re-run today? Full re-run today; note
   the seam.
