# UX_RULES — Non-Negotiable Interaction Rules

1. **≤ 3 clicks** from anywhere to any operation on the current project.
2. **Never block the UI.** No modal spinners; long work runs async with
   inline progress. (Backend is already fully async: BackgroundTasks +
   polled job status.)
3. **Everything asynchronous** — uploads stream, validation runs in a Web
   Worker, search indexes in background chunks.
4. **Undo everywhere** (Phase 3+): every mutating command is reversible;
   the Command Registry is the undo/redo seam. Until editing exists,
   destructive actions (delete project) get explicit confirmation instead.
5. **Keyboard shortcuts** for the whole inner loop: page nav, zoom, tab
   switching, command palette. Every command may declare a `keybinding` —
   the field already exists on the Command type.
6. **Context menus** on everything addressable: pages, tree nodes, objects.
   Context menu items are commands, so they stay in sync with toolbars.
7. **Searchable** — projects, pages, document text, commands, settings.
8. **Dockable** — panels resize and (future) rearrange; no fixed layouts.
9. **Persistent layouts** — panel sizes, active tab, last project, zoom
   level survive reload (autoSaveId + `?panel=` already do part of this).
10. **Honest UI** — placeholders say what's coming; no fabricated data (the
    "no confidence scores" decision is precedent); errors are specific and
    actionable (the PreviewError pattern is precedent).
11. **The document is the hero.** Chrome collapses/steps back; max canvas.
12. **Selection is universal.** Click anything → Properties shows it; the
    same selection drives editing later. One selection model, everywhere.
