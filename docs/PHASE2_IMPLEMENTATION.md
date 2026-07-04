# Phase 2 Implementation Checklist

Living execution log for Phase 2 (2A → 2B → 2C). See `docs/ARCHITECTURE.md`
for the stable architecture overview this implements.

## Sub-phase 2A — Shell, command system, event bus, nav, dashboard, IDE explorer

| # | Task | Files | Status |
|---|---|---|---|
| 1 | Write ARCHITECTURE.md + this file | `docs/ARCHITECTURE.md`, `docs/PHASE2_IMPLEMENTATION.md` | ✅ |
| 2 | Install `react-router-dom`, `react-resizable-panels` | `frontend/package.json` | ✅ |
| 3 | Backend: `GET /api/projects/{id}/summary` | `backend/app/api/summary.py`, `backend/app/schemas/summary.py`, `backend/app/services/summary_service.py` | ✅ |
| 4 | Backend: `GET /api/logs` | `backend/app/api/logs.py`, `backend/app/schemas/logs.py` | ✅ |
| 5 | Backend tests for both endpoints | `backend/tests/test_summary.py`, `backend/tests/test_logs.py` | ✅ |
| 6 | Frontend API client additions | `frontend/src/api/client.ts` | ✅ |
| 7 | App Event Bus | `frontend/src/context/EventBusContext.tsx` | ✅ |
| 8 | Command Registry + built-in commands | `frontend/src/commands/` | ✅ |
| 9 | Document Manager (lazy idm.json + capped caches) | `frontend/src/document/DocumentManager.ts` | ✅ |
| 10 | Context providers (Workspace, ViewerEngine singleton, DocumentManager, Command, EventBus) | `frontend/src/context/`, `frontend/src/app/AppProviders.tsx` | ✅ |
| 11 | Router + ShellLayout + NavRail | `frontend/src/layout/ShellLayout.tsx`, `frontend/src/layout/NavRail.tsx`, `frontend/src/App.tsx` | ✅ |
| 12 | ProductionWorkspaceLayout (resizable docks + tab strip) | `frontend/src/layout/ProductionWorkspaceLayout.tsx` | ✅ |
| 13 | Design tokens / light theme | `frontend/src/styles/tokens.css`, `shell.css`, `viewer.css` | ✅ |
| 14 | Dashboard route | `frontend/src/routes/DashboardPage.tsx` | ✅ |
| 15 | IDE-style Project Explorer panel | `frontend/src/panels/ExplorerPanel.tsx` | ✅ |
| 16 | Workspace route (hosts Viewer/Properties/Logs today; Compare/Validation panels stubbed for 2C) | `frontend/src/routes/WorkspacePage.tsx` | ✅ |
| 17 | Retire `AppLayout.tsx` | remove after cutover | ✅ |
| 18 | Verify: backend tests, frontend build, headless e2e | — | ✅ |
| 19 | Update README.md + CHANGELOG.md | — | ✅ |

## Pre-2B architectural refinements (requested on 2A review, completed)

2A was approved with four refinements to land before starting 2B, so 2B's
larger surface area (windowing, virtualization, view modes) builds on the
right seams rather than needing a later rewrite:

| # | Refinement | Files | Status |
|---|---|---|---|
| 1 | `ViewerEngine` made project-agnostic: `ViewerPage` carries only geometry + a resolved `html_url`, never a project id or relative path; `openProject(projectId, pages)` → `openDocument(pages)` | `frontend/src/viewer/types.ts`, `frontend/src/viewer/ViewerEngine.ts` | ✅ |
| 2 | Explorer (`ProjectTree`) reads `ProjectSummary` via the Document Manager, not the API client directly | `frontend/src/document/DocumentManager.ts` (new `getSummary` + its own small capped cache), `frontend/src/panels/ProjectTree.tsx` | ✅ |
| 3 | Commands flow through a new `WorkspaceService` (owns projectId + `html_path`→`html_url` resolution) instead of calling `ViewerEngine` directly | `frontend/src/workspace/WorkspaceService.ts`, `frontend/src/context/WorkspaceServiceContext.tsx`, `frontend/src/commands/types.ts`, `frontend/src/commands/builtins.ts`, `frontend/src/hooks/useCommand.ts`, `frontend/src/components/PreviewPane.tsx`, `frontend/src/routes/WorkspacePage.tsx` | ✅ |
| 4 | `WorkspacePanel` lifecycle contract defined and adopted by the one dock that actually switches panels today (CenterDock's Viewer/Compare/Validation tabs get real `activate`/`deactivate` calls; always-on docks satisfy the contract trivially via their own mount/unmount) | `frontend/src/workspace/WorkspacePanel.ts`, `frontend/src/panels/CenterDock.tsx` | ✅ |

Verification: `tsc -b` clean, `vite build` clean, headless-browser pass on a
real upload — dashboard → upload → ready, workspace opens, iframes mount for
the windowed radius, Next/zoom-150%/tab-switch all still work through the new
WorkspaceService/CenterDock seams, Explorer tree renders via
`DocumentManager.getSummary`, zero real console errors (only a pre-existing
`/favicon.ico` 404 and expected `ERR_ABORTED` from the StrictMode mount-guard
cancelling a superseded page load).

## Design-package implementation increment (pre-2B, completed)

The approved product design package (`docs/design/`, ratified 2026-07-02 —
personas/IA/navigation/screens, wireframes, hi-fi mockups) landed its first
implementation increment ahead of 2B so 2B/2C UI is built from primitives
instead of ad-hoc markup:

| # | Item | Files | Status |
|---|---|---|---|
| 1 | Full design-system token set + dark theme (`[data-lf-theme="dark"]` token swap) | `frontend/src/styles/tokens.css` | ✅ |
| 2 | Theme service + `useTheme` + `view.setTheme`/`view.toggleTheme` commands; applied pre-paint | `frontend/src/theme/theme.ts`, `frontend/src/hooks/useTheme.ts`, `frontend/src/commands/builtins.ts`, `frontend/src/main.tsx` | ✅ |
| 3 | `components/ui/` primitives (Button, IconButton, Badge, Tabs, Toolbar, Progress, Slider, EmptyState, Skeleton) + `styles/ui.css` | `frontend/src/components/ui/` | ✅ |
| 4 | Settings → Appearance (first primitive consumer, dispatches theme commands) | `frontend/src/routes/SettingsPage.tsx` | ✅ |
| 5 | Hard-coded surfaces → tokens (`.lf-surface`); gutter neutral-dark in both themes; document never themed | `Toolbar/PreviewPane/ProjectExplorer/PropertiesPanel.tsx`, `layout.css`, `shell.css` | ✅ |

Rules for all subsequent 2B/2C UI work: build from `components/ui`
primitives; status renders only via `<Badge>`; no hex values outside
`tokens.css`; dark-theme parity is a completion gate for every new surface.
Tree/VirtualTable primitives land with their first consumers (2B thumbnails,
2C findings table).

## Sub-phase 2B — Advanced document viewer (core complete)

Ordered per user direction: windowing and thumbnail virtualization first
(the two features where a 500–2,000 page document can actually break the
app), then view modes and zoom/fit, then incremental search.

| # | Item | Files | Status |
|---|---|---|---|
| 1 | **Windowing** — `Viewport.windowAround`, `ViewerEngine.computeWindow`/`syncWindow` (contiguous strip, `MAX_MOUNTED_PAGES = 9`, evict-farthest-from-anchor ≡ LRU for linear reading; long jumps reset the strip), `useViewerWindow` (IntersectionObserver → most-visible page, `source: "scroll"` vs `"program"` + suppress window). `mountPage` StrictMode guard untouched. | `viewer/Viewport.ts`, `viewer/ViewerEngine.ts`, `viewer/NavigationManager.ts`, `viewer/types.ts`, `hooks/useViewerWindow.ts` | ✅ |
| 2 | **Thumbnail rail** — manually virtualized (fixed row height, spacer + windowed absolute rows), plain `<img loading="lazy">` of the page background rasters via `WorkspaceService.resolveStaticUrl`; click navigates; auto-scrolls to current page. | `components/ThumbnailRail.tsx`, `workspace/WorkspaceService.ts`, `styles/layout.css` | ✅ |
| 3 | **View modes** — Continuous, Single, Facing, Book (`setViewMode`, `spreadFor`, `groupIntoSpreads`); spread modes mount exactly their spread; scroll promotion only in continuous. `view.setMode` command enabled. | `viewer/ViewerEngine.ts`, `components/PreviewPane.tsx`, `commands/builtins.ts` | ✅ |
| 4 | **Zoom/Fit + keyboard** — Fit Page button, preset-stepped `zoomIn`/`zoomOut` (`zoom.in`/`zoom.out` commands), editable go-to-page field; `useViewerKeyboard`: PgUp/PgDn/Home/End, Ctrl+= / Ctrl+- / Ctrl+0, Ctrl+F (interim dispatcher; bindings also declared on the commands). Wrapper transforms only. | `viewer/ZoomManager.ts`, `hooks/useViewerKeyboard.ts`, `components/PreviewPane.tsx` | ✅ |
| 5 | **Incremental search** — UI over the Document Manager's existing background-chunked `search()` (progressive results, debounced); Enter/Shift+Enter cycle matches; jump = `navigateTo` + `ViewerEngine.highlightObject` (same `data-object-id` identity, announces via the one `SelectionChanged` event, pending-highlight if the page isn't mounted yet). | `components/ViewerSearchBar.tsx`, `viewer/ViewerEngine.ts` | ✅ |
| 6 | **Page Cache Debug panel** (`Ctrl+Shift+D`, WorkspacePanelDescriptor) — deferred: today's `ViewerDebugPanel` already surfaces state/mounted/missing; fold both into one developer panel in 2C when `ViewerDebugPanel` is retired. | — | deferred to 2C |
| 7 | **Mini Map** — reserved concept, still not foreclosed by the windowing work. | — | reserved |

**2B verification** (real browser, live backend, real 27-page project):
paging 14× deep shows the strip growing to exactly 9 then sliding
(`8,9,…,16` — 9 iframes at every step, eviction confirmed); Home long-jump
resets the strip to `1,2,3`; facing mode mounts exactly `[1,2]` in one row,
book mode mounts the cover `[1]` alone; thumbnail rail renders 14 windowed
`<img>` rows for 27 pages and click-navigates; search "hide" → 6 matches,
Enter jumps to page 2 and outlines the matching text block inside the
iframe with the accent color, Properties populates via SelectionChanged;
zero console errors; `tsc -b` + `vite build` clean.

## Sub-phase 2C — Compare, validation engine, properties, logs, conversion monitor (complete)

| # | Item | Files | Status |
|---|---|---|---|
| 1 | **Compare panel** — Overlay (opacity slider + Combined/Background/Overlay layer isolation via `applyAccuracySettings`) and Split (source raster `<img>` beside the live iframe in ONE scroll container — pan synced by construction); inherits page/zoom; resets isolation on exit. Successor of `AccuracyDebugView` (removed). | `panels/ComparePanel.tsx` | ✅ |
| 2 | **Validation engine** — Web Worker (own Vite chunk), fetches `idm.json` itself, streams findings per page, cancelable (`terminate()`); IDM-only checks: layout bounds, empty text, non-web-embedded fonts, missing assets. Panel: run controls, exact-count badges, findings table; results persist in the Document Manager across tab switches; row click → Viewer + `navigateTo` + `highlightObject` (the one selection pipeline). `validate.run` command enabled — emits `validation:run` on the app event bus (CommandContext gained `bus`). | `validation/types.ts`, `validation/validationWorker.ts`, `panels/ValidationPanel.tsx`, `commands/`, `context/EventBusContext.tsx`, `document/DocumentManager.ts` | ✅ |
| 3 | **Properties panel** — collapsible Geometry/Typography/Appearance/Metadata/Advanced groups resolved via `DocumentManager.getObject`/`getFont`; warns "fallback — not embedded" on fonts without files; confidence still never fabricated. | `components/PropertiesPanel.tsx` | ✅ |
| 4 | **Bottom dock** — tabs: Job log · Conversion Monitor · Application/Conversion/Performance (tail via `GET /api/logs`, fetch-on-open + manual refresh, no idle polling). | `panels/BottomDock.tsx` | ✅ |
| 5 | **Conversion Monitor** — honest single-job view (status/stage/progress/error) matching what the polling loop actually tracks; a real queue is Phase 7. | `panels/BottomDock.tsx` | ✅ |
| 6 | **Debug cleanup** — `ViewerDebugPanel` + `AccuracyDebugView` + `ComingSoon` removed; developer diagnostics on `Ctrl+Shift+D` (state machine, mounted window, zoom, view mode, missing assets). | `components/DevDiagnosticsPanel.tsx`, `hooks/useViewerKeyboard.ts` | ✅ |

Architectural fixes surfaced by 2C verification (both landed):
- **The route owns `openProject`** (`WorkspacePage`), not the Viewer tab —
  Compare/Validation now work when the workspace is entered directly on
  their tab (`?panel=…`) with the Viewer never mounted.
- **Re-anchor on tab return**: `useViewerWindow` starts suppressed and
  `PreviewPane` scrolls the current page back into view on mount, killing a
  scroll-promotion cascade that walked the anchor page downward after
  returning from Compare/Validation.

**2C verification** (real browser, live backend): validation on the clean
reference project → 27/27 pass; on the pre-CFF-fix duplicate project → the
engine flags page 26's `HelveticaRounded-Bold` fallback automatically (the
exact bug the user reported by eye); finding click → Viewer + page 26 +
"Your Story Book!" outlined + Properties grouped with the fallback badge;
Compare split shows source vs doubled reconstruction side by side on the
old project; page 26 context survives Viewer→Compare→Viewer round trips;
Application tab tails 200 real log lines; Monitor shows an honest empty
state; Ctrl+Shift+D toggles diagnostics; zero console errors; `tsc` +
build clean (worker chunks separately).

## Notes / decisions log

- Confidence is never displayed anywhere in Properties — no such data exists
  in the IDM (PyMuPDF produces none) and it will not be fabricated.
- `/api/projects/{id}/summary` is intentionally one consolidated endpoint
  (not separate stats/manifest/health endpoints) per user decision.
- Existing `ViewerEngine`, `IframeRenderer`, `Viewport`, `Selection`,
  `useProjectWorkspace`, and `api/client.ts` are reused as-is in 2A; 2A only
  adds the shell around them.
- The bottom dock always shows the job log (`LogPanel`, reused unchanged);
  clicking "Logs" in the NavRail context group is wired for future use once
  2C's full Logs panel (application/conversion/performance tabs) exists —
  today it's part of the always-visible bottom dock rather than a distinct
  toggle state.
- Dashboard's "Active Conversion" reflects `useProjectWorkspace`'s actual
  capability (one tracked job at a time) rather than presenting a queue UI
  with nothing behind it; a true multi-job queue is Conversion Monitor's
  job in 2C.
- 2A verification (headless browser, real PDF upload): dashboard/projects/
  conversion/settings routes all navigate correctly; project opens at
  `/workspace/:id`; IDE Explorer tree renders real page geometry/font/asset
  counts without dumping per-page DOM nodes; center-dock tab switching
  works and Compare/Validation show honest "coming in 2C" placeholders;
  panel resize persists across a full page reload (`autoSaveId`); the
  `ViewerEngine` singleton survives navigating away and back with exactly
  one iframe per mounted page (no StrictMode duplicate-mount regression);
  zero browser console errors. 61 backend tests / clean frontend build.
