# Wireframe 3 — Workspace · Validation Mode

Automated QA replacing eyeball proofing. Entered via Quick Actions, mode
strip, or `Ctrl+3`. Findings are the navigation — every row jumps the
canvas.

## State A — Results (2 warnings on the reference title)

```
┌────┬──────────────────────────────────────────────────────────────────────┐
│ …shell identical…                                                         │
│    ├───────────────┬───────────────────────────────────┬──────────────────┤
│    │ EXPLORER      │ Proof │ Compare │ ● Validate       │ PROPERTIES       │
│    │               ├───────────────────────────────────┤                  │
│    │  Reports ‹6›  │ ‹1› [▶ Run all] [↻ Re-run changed]│ (selected        │
│    │   └ Validation│     Checks: [☑Layout ☑Assets      │  finding's       │
│    │     2 warnings│      ☑Links ☑Structure]           │  object)         │
│    │               │ ‹2› ████████████░░ 24/27 pages…   │                  │
│    │               ├───────────────────────────────────┤                  │
│    │               │ ‹3› 25 ✓ pass · 2 ⚠ · 0 ✕        │                  │
│    │               ├───────────────────────────────────┤                  │
│    │               │ SEV  PAGE  OBJECT      MESSAGE ‹4›│                  │
│    │               │ ⚠    12    tb-8f3a…   Missing gly…│                  │
│    │               │ ⚠    19    tb-2c91…   Font fallba…│                  │
│    │               │ ── pages 1–11, 13–18, 20–27: pass │                  │
│    │               │                                   │                  │
│    │               │ ‹5› finding detail (selected row):│                  │
│    │               │  Glyph U+2014 absent from subset  │                  │
│    │               │  "KidstuffBold". Affected text:   │                  │
│    │               │  "…ran home — fast!"              │                  │
│    │               │  [Go to object] [Ignore] [Copy]   │                  │
└────┴───────────────┴───────────────────────────────────┴──────────────────┘
```

## Callouts

- **‹1› Run controls** — `Run all`, `Re-run changed` (incremental — the
  inner-loop accelerator), check-category toggles. All commands
  (`validate.*` — already reserved in the registry).
- **‹2› Progress** — page-by-page, streaming, cancelable; runs in a Web
  Worker (approved 2C architecture). Canvas stays fully usable during a
  run (Principle 5 test case).
- **‹3› Summary strip** — exact counts, the satisfying all-clear:
  `27 ✓ · 0 ⚠ · 0 ✕` in the pass state.
- **‹4› Findings table** — virtualized; sortable by severity/page; row
  click = jump canvas to page + select object (`F8`/`Shift+F8` = next/prev
  finding). Severity uses the Badge taxonomy — nothing invents new colors.
- **‹5› Detail pane** — specific, actionable message; `Ignore` records a
  reviewed-and-accepted state (persisted to the report, auditable);
  `Copy` for handoff.
- **‹6› Explorer sync** — Reports node shows the same summary; report file
  lands in Output for export packaging.

## State B — Never run (first open)

Empty state: "No validation yet — [▶ Run all] (Ctrl+Shift+V) · checks
layout, assets, links, structure." One sentence, one action.

## State C — All pass

`27/27 pages pass` + timestamp + [Re-run]. Quantified relief (journey
step 10).

## Scale check

Findings virtualized (a bad 2,000-page doc can emit 10k findings);
worker streams results per page so first findings appear in seconds;
`Re-run changed` touches only dirty pages.

## Principles check

5 ✅ worker + streaming + cancel · 2 ✅ finding→selection uses the one
pipeline · 4 ✅ virtualized table · 7 ✅ progressive results ·
10 ✅ same table architecture will host a11y findings (P5).

## Open questions

1. Should `Ignore` require a reason string (auditable for Marcus/P7) or
   stay one-click for speed? Recommend optional note, required in P7.
2. Auto-run validation after every conversion completes? Recommend yes,
   as a Settings-default-on pipeline preference.
