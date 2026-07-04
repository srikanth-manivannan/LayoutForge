# 02 — Information Architecture

## The core objects (domain model, user-facing)

```
Workspace (the app)
└── Project (one title, one source PDF)          ← storage/projects/{id}
    ├── Source            source.pdf
    ├── Document (IDM)    idm.json — the single source of truth
    │   └── Pages (1..n)
    │       └── Objects   TextBlock · ImageElement · ShapeElement
    │                     (each with a stable object_id)
    ├── Resources         Fonts · Images · CSS   (hash-deduplicated)
    ├── Output            HTML pages · Manifest · (Phase 4: EPUB)
    ├── Reports           Validation · (Phase 5: Accessibility) · Logs
    └── Jobs              pipeline runs: status · stage · progress
```

**Rule:** the UI's mental model mirrors this tree exactly — the Explorer
*is* this hierarchy. Users never see backend concepts (IDM, stages) under
other names in different screens.

## Object → where it lives in the UI

| Object | Primary surface | Secondary surfaces |
|---|---|---|
| Project | Projects screen, Dashboard cards | Explorer root, window title |
| Page | Viewer canvas, thumbnails | Explorer count, Validation rows |
| Object (text/image/shape) | Viewer selection | Properties, (P3) edit handles |
| Font / Image / CSS | Explorer Resources | Properties (Typography), Assets detail |
| Output | Explorer Output | Export flow |
| Report | Validation / A11y tabs | Explorer Reports, export package |
| Job | Conversion Monitor, Dashboard | Logs, status bar |

## Hierarchy of attention (what gets the pixels)

1. **The page canvas** — the document is the hero (~60–70% of workspace width)
2. **The active center tab's tools** (Compare sliders, Validation results)
3. **Docks** — Explorer (left), Properties (right), Logs/Monitor (bottom)
4. **Chrome** — NavRail, toolbar, status bar (fixed, minimal)

## Information scent rules

- Every count in the Explorer is clickable and leads to the thing counted.
- Every validation finding links to its page + object (selection pipeline).
- Every job links to its logs; every log line carries its stage.
- Breadcrumb identity: `Project name › page x/y` always visible in the
  workspace toolbar.

## State taxonomy (one vocabulary, everywhere)

Project: `Imported · Processing · Ready · Failed` (today) → adds
`In Proofing · Validated · Accessible · Exported · Delivered` as phases land.
Jobs: `Queued · Running(stage) · Completed · Failed`.
Checks: `Pass · Warning · Error` (badge colors: success/warning/danger tokens).

These names appear identically in Dashboard, Explorer, Monitor, and API —
no synonyms ("Done"/"Complete"/"Finished" drift is forbidden).
