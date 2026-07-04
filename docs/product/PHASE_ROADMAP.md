# PHASE_ROADMAP — Multi-Year Product Phases

Reconciled with the shipped roadmap in `docs/ARCHITECTURE.md` (which defined
Phases 1–4 + a 2.5 hardening phase); this document extends it to the full
seven-phase product vision. ARCHITECTURE.md's "Phase 4 — EPUB Production
Platform" == this roadmap's "Phase 4 — Publishing".

| Phase | Name | Delivers | Status |
|---|---|---|---|
| 1 | **Engine** | PDF → IDM → pixel-accurate HTML/CSS; viewer; font sanitization | ✅ Complete |
| 2 | **Workspace** | Production shell: docks, commands, event bus, Document Manager (2A ✅); advanced viewer (2B); Compare/Validation/Properties/Logs/Monitor (2C) | 🔄 Current |
| 2.5 | **Performance & Scale** | Large-PDF hardening, streaming, background workers, benchmark corpus | Reserved |
| 3 | **Editing** | Visual editing: select/move/resize/restyle, undo/redo, font replacement — rides on Selection + Command Registry | Planned |
| 4 | **Publishing** | EPUB export (reflowable + fixed-layout), packaging, delivery — rides on plugins/exporters + idm.json | Planned |
| 5 | **Accessibility** | Reading order, alt text, semantic tagging, WCAG/EPUB-a11y validation & reports | Planned |
| 6 | **AI** | Auto alt text, layout-fix suggestions, semantic structure detection — rides on plugins/ai | Planned |
| 7 | **Enterprise** | Teams, roles, review workflow, batch queues, API automation, audit | Planned |

## Design implication

The UI designed in Phase 2 must accommodate Phases 3–7 **without redesign**:

- Editing (3): Properties panel becomes writable; toolbar gains edit tools;
  undo/redo already has its seam (commands).
- Publishing (4): Export becomes a center tab / flow; Explorer's Output node
  grows formats.
- Accessibility (5): a new center tab + validators; reading-order overlay in
  the Viewer.
- AI (6): suggestions surface inside existing panels (Properties, Validation,
  Accessibility) — never a separate "AI screen".
- Enterprise (7): Dashboard grows queues/teams; NavRail gains Admin; nothing
  inside the Workspace changes.
