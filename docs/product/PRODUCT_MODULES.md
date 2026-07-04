# PRODUCT_MODULES — The Ten Modules of LayoutForge Studio

Each module is a coherent unit of capability. Modules ≠ screens: several
modules live as dockable panels inside the single Workspace screen.

| # | Module | What it does | Status |
|---|---|---|---|
| 1 | **Dashboard** | Production overview: recent projects, active conversions, health | ✅ Built (2A) |
| 2 | **Import** | Upload PDF, streamed to storage, kicks off the pipeline | ✅ Built (Phase 1) |
| 3 | **Workspace** | The production shell: dockable panels, tabs, command system | ✅ Built (2A) |
| 4 | **Viewer** | Pixel-accurate page rendering, navigation, zoom, view modes, thumbnails, search | ✅ Core built; 2B adds windowing/view modes/search |
| 5 | **Compare** | Source-vs-output proofing: overlay opacity + split view | 🔜 2C (AccuracyDebugView is the proven seed) |
| 6 | **Validation** | Automated checks in a Web Worker: layout, assets, links, structure | 🔜 2C |
| 7 | **Accessibility** | Reading order, alt text, semantic tagging, a11y reports | 🔜 Phase 5 (reserved seams: IDM ids, plugins/validators) |
| 8 | **Assets** | Fonts, images, CSS per project: inspect, replace, dedupe (hash-based dedup already in pipeline) | Partially built (Explorer tree groups) |
| 9 | **Export** | HTML/ZIP today; EPUB reflowable + fixed-layout in Phase 4 | 🔜 Phase 4 (plugins/exporters/ reserved) |
| 10 | **Settings** | App preferences, theme, keybindings, pipeline defaults | ✅ Route exists; grows with product |

## Cross-cutting systems (not user-facing modules, but every module rides on them)

- **Command Registry** — every control dispatches a command (`frontend/src/commands/`)
- **App Event Bus** — typed pub/sub between modules (`context/EventBusContext.tsx`)
- **Document Manager** — single owner of IDM data + LRU caches (`document/DocumentManager.ts`)
- **ViewerEngine** — framework-agnostic rendering singleton (`viewer/`)
- **Plugin System** — reserved extension points: `plugins/{exporters,validators,ai}/`
