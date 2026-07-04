# ARCHITECTURE — Pointer

The authoritative architecture document is
[../ARCHITECTURE.md](../ARCHITECTURE.md). It is stable and already
implemented through Phase 2A. Do not duplicate it here.

The five architectural pillars every design decision must respect:

1. **Document Manager** — the single owner of a project's IDM data, with
   capped LRU caches. Nothing else parses the whole `idm.json`. This is the
   enforcement point for the Large Document memory rules.
2. **Viewer Engine** — framework-agnostic, project-agnostic rendering
   singleton. Same-origin iframes are the one golden rendering path (in-app
   preview === standalone browser tab). Never resize the iframe on zoom —
   transform the wrapper.
3. **Event Bus** — typed pub/sub app-wide (and an analogous EventDispatcher
   on the backend). Cross-module communication never uses direct references.
4. **Command Registry** — every UI control dispatches a command. This is the
   seam for the command palette, keybindings, undo/redo, and Phase 3 editing.
5. **Plugin System** — reserved extension points (`plugins/{exporters,
   validators,ai}/`) sized so EPUB export, accessibility, and AI drop in
   without reorganizing the app.

Additional non-negotiables (from ARCHITECTURE.md):

- Large Document Architecture: 2,000+ pages, 100k text spans must work
  without architectural change; hard resource caps + LRU eviction.
- Every IDM element has a stable `object_id` = `data-object-id` in generated
  HTML; one Selection pipeline powers viewing today and editing in Phase 3 —
  no parallel identity mechanism, ever.
- Performance budgets: startup < 2s · open project < 500ms · page nav < 50ms
  · zoom < 16ms · selection < 10ms.
