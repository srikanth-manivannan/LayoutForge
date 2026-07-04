# LayoutForge — PDF Layout Reconstruction Engine

LayoutForge converts PDFs into pixel-accurate, structured HTML/CSS projects:
upload a PDF, and it extracts pages, text, images, and fonts, then reconstructs
each page as absolutely-positioned HTML with shared and per-page CSS, ready
for preview and future editing.

Full requirements and design live in [docs/](docs/) — read those before
changing architecture.

## Architecture

```
PDF
 ↓
Input Adapter (PyMuPDF)
 ↓
Internal Document Model (IDM)   ← pipeline/document.py, pipeline/elements/
 ↓
Output Plugins                  ← pipeline/outputs/ (html, css, manifest; future: epub, json)
 ↓
HTML / CSS / Manifest
```

Conversion runs as an ordered set of `Stage`s (`pipeline/stages/`) executed by
a backend-agnostic `PipelineEngine` (`pipeline/engine.py`) — today driven by
FastAPI `BackgroundTasks`, swappable later for Celery/RQ/Kubernetes Jobs
without touching stage logic. Stages populate the IDM; output plugins only
ever read the IDM, never PyMuPDF objects.

The pipeline (Validate → Metadata → Render Backgrounds → Extract Fonts →
Extract Images → Extract Text → Normalize IDM → Persist Assets → Generate
CSS → Generate HTML) splits cleanly at `PersistAssetsStage`: everything
before it builds and persists the IDM (no layout/rendering decisions);
everything after it is output generation that reads *only* the IDM —
`CssOutputPlugin` and `HtmlOutputPlugin` never import PyMuPDF. The full
`Document` is also serialized to `storage/projects/{id}/idm.json`
(`StorageService.save_idm`/`load_idm`), so any future output plugin (EPUB,
JSON, XML) can reconstruct everything it needs from disk + DB without
reopening the source PDF. Images and fonts are deduplicated by content hash
within a project (`Asset.hash`, `AssetPageLink` tracks every page that
references a given asset); `NormalizeIdmStage` is where cross-element
decisions belong (reading order, default line height) so extraction stages
stay a faithful, un-opinionated read of the source.

HTML generation follows a strict split: `PageRenderer` orchestrates
`TextRenderer`/`ImageRenderer`/`ShapeRenderer`, each rendering its own
Jinja2 template (`outputs/templates/`) into a fragment; `PageRenderer`
assembles those fragments into `page.html`'s background/images/shapes/text/
overlay layers. Every element keeps its IDM UUID as its DOM id
(`tb-{uuid}`, `img-{uuid}` — matching the CSS selectors from Task 4) and
carries `data-*` attributes (`data-page`, `data-font`, `data-asset`,
`data-rotation`, etc.) so a future editor can address any element without
re-parsing. `HtmlValidator` runs before each page is written to disk and
fails fast on duplicate ids or missing asset references.

Status, stage, and asset-kind values are closed enums (`app/core/enums.py`:
`ProjectStatus`, `JobStatus`, `PipelineStage`, `AssetType`) rather than
magic strings — `Job.stage` itself stays a plain string column so future
plugin stages outside the enum remain representable without a migration.
Cross-cutting actions (`ProjectCreated`, `UploadCompleted`, `JobStarted`,
`StageCompleted`, `JobFinished`, `ProjectDeleted`) are published through a
lightweight in-process event dispatcher (`app/events/`); today the only
subscriber logs them, but notifications/WebSockets/audit trails can subscribe
later without touching call sites.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy + SQLite, PyMuPDF, Pillow, FontTools
- **Frontend:** React, TypeScript, Vite, Bootstrap
- **Infra:** Docker Compose

## Project layout

```
backend/app/
  api/          FastAPI routers (thin controllers) + deps.py (DI wiring)
  core/         Settings (Pydantic Settings) and enums — the only place config/status values live
  pipeline/
    document.py    the IDM root (Document, DocumentMetadata) + to_dict/from_dict
    elements/       BoundingBox, Page, TextBlock, ImageElement, ShapeElement, FontResource, AssetResource
    stages/         validate, metadata, render_backgrounds, extract_fonts, extract_images,
                     extract_text, normalize_idm, persist_assets, generate_css, generate_html
    engine.py       backend-agnostic PipelineEngine
    outputs/
      css_output.py    common.css + per-page CSS (Task 4)
      html_output.py   semantic, layered per-page HTML via Jinja2 templates (Task 5)
      renderers/       TextRenderer, ImageRenderer, ShapeRenderer + PageRenderer (orchestrator)
      templates/       page.html, text_block.html, image.html, shape.html
      html_validator.py  fail-fast: duplicate ids, missing asset references
      (manifest/EPUB output plugins land in later tasks)
  services/     business logic (project, conversion, storage; html/css/preview land in later tasks)
  events/       Event base class, concrete events, EventDispatcher
  repositories/ interfaces.py (IProjectRepository etc.) + sqlite/ implementations
  models/       SQLAlchemy ORM models (includes AssetPageLink for asset dedup)
  schemas/      Pydantic request/response models
  database/     engine/session setup, bootstrap
  utils/        logging, filename sanitization, upload validation, streaming
frontend/src/
  app/          AppProviders — all context providers, above the router
  layout/       ShellLayout, NavRail, ProductionWorkspaceLayout (resizable docks)
  routes/       DashboardPage, ProjectsPage, ConversionPage, SettingsPage, WorkspacePage, router.tsx
  panels/       ExplorerPanel, ProjectTree (IDE-style tree), CenterDock (tab strip)
  context/      WorkspaceContext, ViewerEngineContext, DocumentManagerContext, CommandContext, EventBusContext
  commands/     CommandRegistry, built-in commands — every control dispatches a command, never calls the engine directly
  document/     DocumentManager (lazy idm.json + capped LRU caches), idmTypes
  components/   Toolbar, ProjectExplorer, PreviewPane (thin — delegates to viewer/), ViewerPageHost, PropertiesPanel, LogPanel
    ui/         design-system primitives (Button, Badge, Tabs, …) — new UI composes these; status renders only via Badge
  theme/        theme service — light/dark as a token swap (data-lf-theme), persisted, driven by view.setTheme/view.toggleTheme commands
  viewer/       ViewerEngine, IframeRenderer, NavigationManager, ZoomManager, Viewport, Selection, EventBus, types
  hooks/        useProjectWorkspace (upload, project list, job polling, project selection + page list), useCommand
  api/          typed fetch client
  styles/       tokens.css (design tokens — single source of truth, light + dark themes), ui.css (primitive styles), shell.css, viewer.css, layout.css
storage/
  projects/{id}/
    source.pdf
    idm.json          the persisted Internal Document Model (see Architecture above)
    resources/images/ page background PNGs + extracted embedded images
    resources/fonts/   extracted embedded font files
    resources/css/     common.css (shared rules + @font-face) + page_XXXX.css (per-page absolute positioning)
    pages/             page_XXXX.html — semantic, layered, Jinja2-rendered per page
  cache/        reusable intermediate artifacts
  temp/         scratch space during processing (streamed uploads land here first)
  logs/         application.log, conversion.log, performance.log
```

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

`GET http://localhost:8000/api/health` should return `{"status": "ok", "app_env": "development"}`.
On startup the backend creates `storage/{projects,cache,temp,logs}/` at the
repo root and initializes `storage/layoutforge.db` (SQLite).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The toolbar shows a "Backend connected" badge
once it can reach the backend's `/api/health` endpoint (proxied via Vite).
Click "Upload PDF" in the Projects panel to upload a file — the bottom log
panel shows live stage/progress updates polled from `GET /api/jobs/{id}`
until the job completes or fails.

### Docker Compose

```bash
docker compose up --build
```

Backend on `:8000`, frontend on `:5173`, with `storage/` bind-mounted into the
backend container so generated projects persist on the host.

### Tests

```bash
cd backend
pytest
```

### Note on schema changes

There's no migration system yet (`init_db()` only calls `Base.metadata.create_all`,
which never alters existing tables). If you pull a change that adds/renames
DB columns, delete your local `storage/layoutforge.db` and let the backend
recreate it on next startup — there's no production data to preserve at
this stage.

## Viewer architecture (Task 6, revised)

`PreviewPane` is a thin React shell — all rendering, page loading,
navigation, zoom, virtualization, and selection logic lives in
`frontend/src/viewer/`, independent of React:

```
PreviewPane (React)
   ↓
ViewerEngine            — orchestrator; owns the modules below
   ↓
IframeRenderer          — renders one page via a same-origin <iframe>
                           pointing at the backend-served, self-contained
                           HTML (relative URLs — the same file works opened
                           directly, served, or in the iframe)
   ↓
NavigationManager / ZoomManager / Viewport / Selection
   ↓
EventBus                — ProjectOpened, PageChanged, ZoomChanged,
                           SelectionChanged, ...
```

Earlier revisions used a Shadow-DOM-based renderer (`PageLoader` +
`ShadowRenderer`, rewriting relative URLs to absolute ones before
injection). That approach was replaced after diagnosing a real rendering
bug: `@font-face` rules declared inside a Shadow DOM `<style>` tag never
register in `document.fonts`, so font-load waits were meaningless and
pages painted with fallback-font metrics before the real font arrived.
The same-origin-iframe approach is the **one rendering path** shared by
opening a page directly in a browser, the backend serving it, and the
in-app preview — so the preview is now guaranteed to match what a
standalone browser tab shows, with no URL rewriting anywhere.

- **Virtualization**: `Viewport` only asks the engine to mount the current
  page ± 1 — never the whole document. Verified with a real 27-page PDF.
- **Selection without DOM parsing**: every generated element already
  carries `data-object-id` (the IDM UUID); `Selection` resolves a click to
  `{objectId, type, page}` and emits `SelectionChanged` — `PropertiesPanel`
  just renders whatever it receives.
- Backend support: `GET /api/projects/{id}/pages` (page geometry + paths)
  and a read-only static mount (`/static/projects/{id}/...`) serving each
  project's generated HTML/CSS/resources directly.

## Layout Accuracy phase

Investigating "text looks doubled/larger/shifted" led to two distinct,
now-fixed findings (see CHANGELOG for the full diagnostic trail):

1. **Font sanitization** (the dominant cause): PDF-embedded font subsets
   are frequently structurally valid to a lenient parser but fail
   browser OTS sanitization, so `@font-face` silently fails and the
   browser substitutes a fallback font with different metrics —
   confirmed via `document.fonts` reporting `status: "error"`. Fixed in
   `ExtractFontsStage` by re-saving every extracted `ttf`/`otf` font
   through `fontTools` (`_sanitize_for_web`), which recomputes checksums
   and normalizes the table directory. Bare `cff` font programs (PDF
   Type1C — the payload of an OTF's `CFF ` table, not a standalone font)
   were originally dropped as non-web-loadable; that resurfaced as visibly
   doubled 42pt title text on the reference book's page 26
   (`BHEMPQ+HelveticaRounded-Bold`, fallback-font metrics vs. the
   rasterized background). Now fixed properly: `_wrap_bare_cff` rebuilds a
   bare CFF into a complete OTF (widths/bounds recovered by drawing each
   charstring, cmap from AGL glyph names, outlines re-emitted through
   `T2CharStringPen` so subroutines are flattened, and — critically —
   line metrics taken from `fitz.Font(fontbuffer=…)` rather than glyph
   bounds, because NormalizeIdmStage's `line_height` and the browser's
   baseline must be computed from the same ascender/descender or text
   paints vertically offset from the raster). Verified loading in the
   browser (`document.fonts` → `loaded`) with the page rendering
   single-imaged and the measured baseline within 0.45px of the PDF's
   `origin_y`. Other non-recoverable formats are still not written
   rather than served broken.
2. **Background already contains everything**: `RenderBackgroundsStage`
   rasterizes the full page (PyMuPDF's `get_pixmap()` has no
   text-exclusion mechanism), so the same text the IDM extracts for HTML
   overlay is already baked into the background image. Per explicit
   direction, this is **not** being changed yet — removing text from the
   background before the overlay is accurate would make output look
   worse, not better. With the font fix in place, the duplication is now
   visually seamless rather than glaringly broken.

The IDM's `TextBlock` was also expanded with `origin_x`/`origin_y`,
`ascender`, `descender` (real PyMuPDF span values — `NormalizeIdmStage`
now computes `line_height` from them instead of a flat `font_size * 1.2`
guess) and reserved (not yet extracted) `horizontal_scale`/`render_mode`
fields, documented as such — `char_spacing`/`word_spacing`/`Tz`/`Tr` live
in raw PDF content-stream operators that `get_text("dict")` doesn't
expose; extracting them would need lower-level content-stream parsing.

### Accuracy Debug View

A permanent diagnostic tool (`frontend/src/components/AccuracyDebugView.tsx`,
visible below the viewer toolbar): three modes — **Background only**
(the raw rasterized PDF page, ground truth), **Overlay only** (just the
extracted text/images on a transparent background, our reconstruction in
isolation), **Combined** (normal view) — plus an opacity slider for the
overlay in Combined mode. Toggling between Background-only and
Overlay-only is the fastest way to spot a font, position, or sizing
mismatch without guessing from one flattened screenshot.

## Environment validation

The frontend never assumes the backend is healthy or compatible — `useEnvironmentCheck`
(`frontend/src/environment/`) runs on startup and checks, in order: backend
reachable (`GET /api/health`) → API version matches (`GET /api/version`,
compared against `EXPECTED_API_VERSION` in `checkEnvironment.ts` — keep this
in sync with `Settings.api_version` in `backend/app/core/config.py`) →
static mount serves files (`GET /static/projects/.static_ok`, a marker
file the backend writes at startup) → storage accessible (`storage_ok` in
the health response). Results render as four badges in the toolbar
(Backend/Storage/Static/API, with a manual recheck button) and, for the
two failures severe enough that nothing else can be trusted, a blocking
red banner: backend unreachable, or an API version mismatch — explicitly
never fails silently.

Opening a project follows the same guarded sequence
(`environment/PreviewError.ts`): version → health → the actual
`GET /api/projects/{id}/pages` request. Any failure produces a specific,
actionable message in the preview pane (reason / expected endpoint /
suggestions) instead of an empty-looking "no pages" state.

The backend also logs every registered route at startup
(`[OK] GET /api/projects/{id}/pages`, etc., in `application.log`) — a
router that failed to wire up is visible immediately rather than
discovered later as a confusing 404.

## Viewer diagnostics (stabilization phase)

A single state machine controls the viewer
(`idle → opening_project → loading_assets → rendering → ready`, or
`→ error` at any step) instead of scattered booleans — see
`ViewerEngine`'s `state`/`statePage`. Every page load logs structured
checkpoints (`Opening Page` → `HTML Loaded`/`CSS Loaded` → `Shadow DOM
Mounted` → `Ready`, prefixed `[Viewer]` in the browser console — filter on
that to debug a load issue). A **temporary** debug panel (toggle in the
preview toolbar) shows live state, mounted pages, zoom, and any image that
failed to load. Remove `ViewerDebugPanel` and `viewer/diagnostics.ts` once
preview reliability is no longer in question — tracked as a follow-up
alongside the Vitest/Alembic gaps below.

## Phase 2 — Production Publishing Workspace (sub-phase 2A)

Phase 1 delivered the conversion engine and a basic single-page-grid preview.
Phase 2 rebuilds the frontend into a **Production Publishing Workspace** —
architected as an extensible platform (command system, event bus, plugin
extension points, a Document Manager enforcing large-document memory rules)
rather than a one-off viewer, so future editing/EPUB export/accessibility
modules slot in without rewrites. Full architecture, the component diagram,
and the non-negotiable Large Document principles live in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md); the sub-phase execution
checklist lives in [docs/PHASE2_IMPLEMENTATION.md](docs/PHASE2_IMPLEMENTATION.md).

Sub-phase 2A (shell, command system, event bus, nav, dashboard, IDE-style
explorer) is complete:

- **Backend** (read-only, no pipeline/generator changes): `GET
  /api/projects/{id}/summary` — one consolidated read (project + statistics
  + manifest + health + progress + warnings + a recent-logs snippet),
  computed on demand from `idm.json` + DB + a directory walk. `GET
  /api/logs?stream=application|conversion|performance&tail=N` tails the
  three rotating log files (fixed stream allow-list — never an arbitrary
  path).
- **Command Registry** (`frontend/src/commands/`): UI controls dispatch
  commands (`navigate.*`, `zoom.*`; `view.*`/`validate.*`/`export.*`
  registered but disabled until their sub-phase lands) instead of calling
  the engine directly — the seam Phase 3 editing and a future command
  palette build on.
- **App Event Bus** (`context/EventBusContext.tsx`): promotes the existing
  viewer `EventBus` pattern app-wide (project selection, selection
  re-broadcast today; more producers arrive as 2B/2C add the features that
  emit them).
- **Document Manager** (`document/DocumentManager.ts`): the single owner of
  a project's `idm.json`, behind a small LRU cache cap — the enforcement
  point for the Large Document memory rules (nothing else parses the whole
  IDM).
- **Router + shell**: `react-router-dom` global routes (Dashboard, Projects,
  Conversion, Settings) plus `/workspace/:projectId`, where Compare,
  Validation, Logs, and Properties are **dockable panels/tabs inside one
  workspace** — not separate destinations — matching how desktop publishing
  software behaves. `?panel=` on the URL is the source of truth for the
  active center-dock tab.
- **Resizable docking layout** (`react-resizable-panels`): Explorer | Viewer
  (tabbed: Viewer/Compare/Validation) | Properties, with a bottom Logs dock;
  every panel group persists its sizes to `localStorage` via `autoSaveId`.
- **IDE-style Project Explorer**: `Source → Pages → Resources
  (Fonts/Images/CSS) → Output (HTML/Manifest) → Reports`, built from the
  summary endpoint — deliberately summarizes counts rather than listing
  every page/asset (a 2,000-page document must never force this tree to
  render tens of thousands of DOM nodes).
- **ViewerEngine singleton**: created once via a `useRef`-backed context,
  above the router, so it survives every route change without remounting
  iframes.

Compare and Validation currently show an honest "planned for sub-phase 2C"
placeholder rather than a fake or broken panel.

**Verified** (headless browser, real PDF upload, zero console errors): all
four global routes navigate correctly; a project opens at
`/workspace/:id`; the IDE Explorer tree renders real page/font/asset counts;
center-dock tab switching works; panel resize **persists across a full page
reload**; navigating away from and back to the workspace leaves **exactly
one iframe per mounted page** (StrictMode duplicate-mount guard holds); 61
backend tests passing; clean frontend build.

## Status

**Phase 1** (Setup, Upload, Extraction, CSS generation, HTML generation,
Viewer, stabilization, final hardening) is complete — see prior sections
above for the full trail. **Phase 2 / sub-phase 2A** (Production Publishing
Workspace shell) is complete. **Sub-phase 2B core** (windowed viewer with a
hard 9-iframe cap, virtualized thumbnail rail, Continuous/Single/Facing/
Book view modes, zoom/fit + the approved keyboard map, Ctrl+F incremental
search riding the one selection pipeline) and **sub-phase 2C** (Compare
overlay/split proofing, Web-Worker validation engine with click-through
findings, grouped Properties, tabbed Logs, Conversion Monitor) are complete
and browser-verified — Phase 2's workspace feature set is done; the product
design package it implements lives in
[docs/design/](docs/design/00_DESIGN_OVERVIEW.md). Next: Phase 2.5
performance hardening or Phase 3 visual editing — see
[docs/PHASE2_IMPLEMENTATION.md](docs/PHASE2_IMPLEMENTATION.md).

**Known environment gaps** (by design, not yet addressed):
- No frontend test framework (Vitest) — frontend correctness is verified
  via `tsc` + build + manual/Playwright browser passes only.
- No DB migration system (Alembic) — schema changes require dropping the
  local `storage/layoutforge.db` (see note above). Fine pre-launch; would
  need fixing before any real user data exists.

See [docs/22_TASKS.md](docs/22_TASKS.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md),
[docs/PHASE2_IMPLEMENTATION.md](docs/PHASE2_IMPLEMENTATION.md), and
[CHANGELOG.md](CHANGELOG.md) for details.
