# FUTURE — The Open Roadmap

Nothing here is hidden from design. Screens and components must leave room
for all of it without redesign (see PHASE_ROADMAP.md for phase mapping).

- **Visual Editing** (Phase 3) — move/resize/restyle objects, font
  replacement, undo/redo. Seams exist: `data-object-id` selection pipeline,
  Command Registry.
- **AI** (Phase 6) — auto alt-text, layout-fix suggestions, semantic
  structure detection. Surfaces inside existing panels via `plugins/ai/`.
- **Accessibility** (Phase 5) — reading-order editor, tagging, WCAG / EPUB
  Accessibility conformance reports.
- **Plugins** (ongoing) — exporters / validators / ai extension points are
  already reserved directories; long-term: third-party plugin API.
- **Cloud** — multi-tenant hosting, project sync, storage backends (the
  pipeline engine is already backend-agnostic for Celery/K8s workers).
- **Batch** (Phase 7) — watch folders, queues, priorities, bulk export.
- **Enterprise** (Phase 7) — teams, roles, SSO, audit trails (backend event
  dispatcher is the audit seam).
- **Review Workflow** — annotations, approvals, versioned proofs.
- **Marketplace** — distribution for third-party plugins/themes.

## Design guardrails for the future

- New capabilities arrive as **panels, tabs, commands, and tree nodes** —
  never as new top-level app paradigms.
- The NavRail can grow items; the Workspace layout does not change shape.
- Anything AI-generated is labeled and reviewable — consistent with the
  honest-UI rule.
- **AI is a panel, not a chatbot.** The AI Assistant is a right-dock panel
  that runs commands (Fix Alignment · Find Missing Fonts · Generate Alt
  Text · Validate Reading Order) through the Command Registry — results
  are attributable and undoable like any other command. There is no "AI
  screen" and no free-floating chat window.
