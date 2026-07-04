# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — Typography Reconstruction Engine v2 (architecture) + Milestone 1 (word positioning)

Commissioned architecture for reconstructing document *typography* (not
line-by-line screenshots) to reach 99.99% fidelity and generate
HTML/XHTML/EPUB/XML/PML from one model. Full package in
[docs/design/typography/](docs/design/typography/00_OVERVIEW.md): the Rich
Document Model (Document→Region→Paragraph→Line→Run→Word→Glyph +
Table/Math/List/Figure), baseline & paragraph engines, font-metrics engine,
table & MathML & multi-column engines, HTML/CSS strategy (two renderers,
thin format writers), validation rules, benchmark corpus, milestone
roadmap, and large-document performance. Milestones 2+ are approval-gated;
extraction is unchanged (work begins at the IDM).

**Platform freeze — LayoutForge Core v1.0 LOCKED (documented).** With the
architecture matured, the platform (not just the code) is frozen:
[ADR-009](docs/adr/009-core-v1-platform-freeze.md) + the manifest
[docs/CORE_v1.0.md](docs/CORE_v1.0.md) — LFS 1.0, Rich Document Model,
Adaptive Reconstruction Engine + ReconstructionDecision, Viewer/Compare/
Validation/Workspace, Quality Gate, Golden Corpus, ADR-001..009. No
architectural refactoring unless a serious flaw is found (requires an ADR);
all future work *expands what the engine understands*.
- **Canonical definition** (PRODUCT_VISION.md): "a document reconstruction
  platform that transforms fixed-layout documents into production-ready
  structured publishing assets while preserving visual fidelity" — no longer
  a PDF→HTML converter / Able2Extract competitor. Markets: publishing,
  accessibility remediation, government/legal, academic.
- **Seven Product Pillars** ([docs/product/PRODUCT_PILLARS.md](docs/product/PRODUCT_PILLARS.md)):
  Reconstruction · Accuracy · Semantics · Editing · Publishing ·
  Accessibility · Automation. Every feature maps to exactly one; intake rule
  = name its pillar + capability + LFS section + Quality-Gate targets.
- **M3 renamed Semantic Reconstruction** (Phase 3, "months not weeks") —
  Document Intelligence delivered as WP1 Paragraphs · WP2 Headings/Lists ·
  WP3 Reading Order/Regions · WP4 Tables · WP5 Figures/Captions · WP6
  Footnotes/Refs. Roadmap renumbered around it.
- **LFS: Document Intelligence Layer elevated to first-class** — added to the
  normative pipeline shape (§0) and §5 (per-WP node table).

**Strategic direction — Semantic-First, LFS 1.0, Golden Corpus, Editions
(documented).** With the engine core frozen (M1–M1.7), the reviewer set the
next direction: prioritize **semantic** reconstruction over **precision**.

- **Semantic-first ordering** ([ADR-008](docs/adr/008-semantic-first-ordering.md)):
  M2 (Precision/glyph) is **postponed** behind the semantic core
  (M3 paragraph → M4 columns → M5 lists → M6 tables → M7 math → M8
  EPUB/XHTML/XML/PML writers → M2 → M9). Rationale: the Adaptive
  Reconstruction Engine already captured ~85–90% of visual gain (M2 residual
  small/bounded per `report.json`), while semantic structure unlocks
  EPUB/XHTML/XML/PML + accessibility + editing + reading order at once.
  **Next recommended step: M3 — Baseline + Paragraph reconstruction.**
- **LayoutForge Specification** ([docs/spec/LFS-1.0.md](docs/spec/LFS-1.0.md)):
  the internal contract (Document Model, Typography, ReconstructionDecision,
  Adaptive Precision, Analytics, Validation, Export, Performance) between
  Engine/Viewer/Editor/Writers/Plugins — our EPUB-spec equivalent. Core
  sections normative now; structure/math/a11y reserved per milestone.
- **Golden Corpus** ([golden-corpus/](golden-corpus/README.md)): formalized
  12-category corpus (children-books … comics) with `manifest.json` +
  per-file baselines, and a discovery harness (`test_golden_corpus.py`) that
  converts any PDFs present and gates them against their baseline (empty →
  skipped). This becomes the release-over-release quality record.
- **Feature editions** ([docs/product/EDITIONS.md](docs/product/EDITIONS.md)):
  Community/Professional/Enterprise as capability bundles on the shared
  frozen engine (design intent, not built) — falls out of ADR-007.

**Milestone 1.7 — Engine Stabilization (SHIPPED, verified).** Froze the
reconstruction core before extending it (reviewer: "stop implementing new
capabilities … stabilize the core"). (1) **Frozen `ReconstructionDecision`
contract** — an immutable dataclass (mode · reason ·
reconstruction_confidence · expected_width · actual_width · width_error ·
tolerance) that every later stage *consumes* and none recomputes;
`AdaptiveReconstructionEngine.decide_word` is now pure and returns it. (2)
Renamed `confidence` → **`reconstruction_confidence`** everywhere (leaves
room for future ocr/table/reading-order confidences; `WordBox.from_dict`
tolerates the old key). (3) **Froze the engine public API** (`__all__` +
stability note). (4) **Per-stage timing + peak memory** (tracemalloc in
`PipelineEngine`) and a per-conversion **`report.json`**
(`services/conversion_report.py`: reconstruction profile + accuracy +
performance) — the telemetry to compare releases objectively (kerning % over
time). (5) **Benchmark + performance regression tests**
(`test_engine_stabilization.py`) and a permanent
**[Quality Gate](docs/design/QUALITY_GATE.md)** (visual fidelity ≥99.9%,
0 unexpected fallbacks, memory <+10%, 3000+ pages, corpus 100%). (6)
**ADR-007 Capability Architecture** records the modular direction (staged to
M4). M2 renamed **Precision Reconstruction** (glyphs are one strategy, not
the purpose). 94 backend tests. Files: `pipeline/engine.py`,
`pipeline/typography/adaptive_reconstruction.py`, `elements/textbox.py`,
`document.py`, `services/conversion_report.py`, `services/conversion_service.py`.

**Milestone 1.6 — Reconstruction Diagnostics (SHIPPED, verified).** The
engine is now explainable, not a black box. Every escalated object records
`reason` (`ReconstructionReason`: width_error/kerning/baseline/ligature/
rtl/vertical/rotation/font_subset/unknown) and an internal `confidence`
(0–1 engineering metric — NOT the user-facing score the Properties panel
deliberately avoids); both surface as `data-mode`/`data-reason` in HTML. A
per-document `reconstruction_profile` (counts by mode/reason + mean
confidence) is persisted in idm.json and logged. The engine was extracted
to its own module (`pipeline/typography/adaptive_reconstruction.py`,
renamed **Adaptive *Reconstruction* Engine** so the name grows with the
WORD→RUN→GLYPH→SVG→IMAGE ladder) with the pipeline layered into
single-responsibility phases — Geometry Normalizer / Typography Analyzer
(font metrics) / Adaptive Reconstruction — recorded as ADR-006. **Measured
on the dictionary:** 51,199 glyph words = 36,086 width_error + 13,583
kerning + 1,530 ligature, mean confidence 0.973; the "1910" page flags
exactly `HTML`/`Tim`/`T.`/`Wium` as `kerning`. M2's glyph engine will
*consume* these decisions, never recompute them. Also adds Architecture
Decision Records ([docs/adr/](docs/adr/README.md), ADR-001..006). 88
backend tests. Files: `core/enums.py`, `pipeline/typography/*`,
`elements/textbox.py`, `document.py`, `renderers/text_renderer.py`.

**Milestone 1.5 — Adaptive Precision Engine (SHIPPED, verified).** Inserted
before glyph reconstruction at the reviewer's insistence: escalating every
word to glyphs would make a 3,000-page book millions of glyph objects.
`ReconstructionMode` enum (WORD/RUN/GLYPH/SVG); each word is measured
(expected vs PDF-box width) and keeps cheap WORD level within tolerance,
escalating to GLYPH-flagged only when it doesn't; `mode` + `width_error` in
the IDM, `data-mode` in HTML so every object records its own precision.
**Measured on the Zoëga dictionary: 85% of 341,029 words stay WORD, 15%
flagged GLYPH** (51k, not 341k) — and on the "1910" page it auto-flags
exactly `HTML`, `Tim`, `T.`, `Wium` (the kerning-heavy words) with no
hardcoded list. M2's glyph reconstruction will run only on the flagged
fraction. The same detect→measure→escalate/fallback rule is documented as
first-class for tables (confidence-gated) and math (MathML→SVG→glyphs
ladder). Adds `docs/design/typography/12_ADAPTIVE_PRECISION.md`; 83 backend
tests. Files: `core/enums.py`, `elements/textbox.py`, `stages/normalize_idm.py`,
`renderers/text_renderer.py`.

**Milestone 1 — word-level positioning (SHIPPED, verified).** Root cause of
the residual ghosting: line-level width-fitting smeared a single spacing
correction across a line whose true width difference lived inside words
(kerning), so the overlay drifted against the raster (confirmed: reference
"1910" credits carried −0.9 to −1.4px word-spacing as a failing crutch).
Fix: capture exact per-word boxes (`page.get_text("words")`) into the IDM
(`WordBox` — the run/word layer), fit each word to its own box, and
word-pin each line (`<p>` container, absolutely-placed `<span class=lf-word>`
per word at its true x). Cross-word drift is now structurally impossible —
word starts are pixel-exact. Verified on the reference dictionary: the
title page ("A Concise Dictionary of Old Icelandic") and the ghosted
credit lines render crisp; residual is now sub-word kerning distribution
only (M2's glyph layer). Falls back to span rendering for rotated/RTL/
unresolved lines. 79 backend tests (html-generation assertions updated for
word-pinning).

### Fixed — justified-text spacing distribution + rotated-text placement (user multi-PDF round 3)

- **Word-spacing for justified text** (`compute_spacing`, ex-
  `compute_letter_spacing`): the width-fitting surplus was distributed
  per CHARACTER, visibly loosening word interiors on justified lines
  (dictionary columns carried up to 0.84px/char at 10pt). PDF
  justification carries its surplus BETWEEN words (Tw); the surplus now
  goes to CSS word-spacing when the text has spaces (identical
  semantics), and only spaceless runs use letter-spacing. The
  dictionary's title page and columns render crisp instead of smeared.
- **Rotated text placed by baseline origin** (`css_output`): rotated
  blocks were positioned by their rotated bounding box and spun around
  `top left`, landing on the wrong side of the anchor (the dictionary's
  90° margin thumb-letters). PDF rotates glyphs around the BASELINE
  START: the unrotated line is now placed so its baseline start sits on
  the PDF text origin, sized to the recovered run length, and rotated
  about exactly that point (`transform-origin: 0 <baseline>px`).
  Measured: the margin "A" lands within 0.6px of the PDF's true box.

79 backend tests passing (justified-distribution case added).

### Fixed — blank first preview + custom-encoded/incomplete font subsets (user multi-PDF round 2)

**Frontend — blank preview on first open**: the route-level `openProject`
re-fired when the pages list arrived; `openDocument` unmounts every live
iframe but React hosts didn't know to remount, leaving all pages blank
until navigation forced new mounts. Two belts: `WorkspaceService.
openProject` now skips redundant re-opens, and `PreviewPane` bumps a
document epoch on `DocumentOpened` that keys the page hosts (any real
re-open remounts them). Verified: fresh open paints immediately with
zero interactions.

**Backend — two more real-world font pathologies** (both books rendered
"fully broken" overlays):

- **Missing required tables** (`_ensure_required_tables`): PrinceXML
  subsets ship without OS/2 — browsers' OTS sanitizer rejects the whole
  file, silently dropping every block to fallback fonts (all seven
  fonts reported `status: "error"`). Sanitization now synthesizes
  missing OS/2 (metrics from hhea, all pairs consistent), name, post,
  and cmap presence.
- **Custom-encoded subsets** (`_reconcile_cmap_from_usage`): generators
  like PrinceXML/TeX re-encode embedded fonts — the file's cmap doesn't
  map the document's real Unicode text. Each font's cmap is now rebuilt
  from `page.get_texttrace()`, the exact (unicode → glyph id) pairs the
  PDF actually rendered — ground truth by construction.
- Plus **base-14 support**: non-embedded standard fonts (Times/
  Helvetica/Courier) map to metric-compatible local stacks
  (`font_naming._LOCAL_METRIC_STACKS`) and get width-fitting metrics
  from MuPDF's built-in tables (`Base14Metrics`).

Measured on the user's two test documents after reconversion: PrinceXML
sample — 0 font errors (was 5), average overlay width error 0.09px
across 88 blocks (worst 2.39px, was ~56px); 660-page dictionary page 9 —
0.04px average across 87 dense two-column blocks (worst 0.63px), with
the windowed viewer holding exactly 3 iframes. 78 backend tests passing.

### Fixed — image overlay no longer painted (user multi-PDF testing, pages 2/3/8)

First real-world multi-PDF test surfaced three defects on one book, all
one root cause: extracted images were painted as raw `<img>` overlays on
top of the background raster. The PDF composites images with clip paths,
soft masks, blend modes, and draw order that a raw bitmap can't
reproduce — so unclipped fragments doubled artwork (p2), rectangular
chunks covered the page (p3), and one full-page unmasked image hid
raster-only content entirely (p8 — "mirror text missing").

Fix (`image.html` + `ImageRenderer`): image elements render as INVISIBLE
hotspot `<div>`s — the raster stays the visual ground truth (same
principle as the documented text-layer decision), while the hotspot
keeps `data-object-id` (click-to-select → Properties, Phase 3 editor
anchors) and `data-src` (so an editor can materialize the bitmap when
actually editing). Assets are still extracted for the Explorer and
future EPUB packaging. Verified on the reported book: all three pages
now match the original; exactly one painted `<img>` (the background)
per page with the hotspots intact.

### Added/Fixed — Accuracy hardening + workspace/dashboard UX (pre-multi-PDF-testing pass)

Backend (conversion accuracy — all verified on a fresh conversion of the
reference book):

- **Sibling-subset completion** (`_complete_sibling_subsets`,
  extract_fonts.py): PDFs embed several subsets of one typeface cut from
  the same base font with the real outlines PARTITIONED between them
  (each keeps empty placeholders for the other's glyphs; one of the two
  ComicSansMS subsets even shipped with NO cmap). Browsers render an
  "existing but empty" glyph as nothing — seen as dropped letters
  ("just going" → "ust oin") on page 5. Same-family TrueType subsets
  with identical glyph count/upm now have outlines + advances copied
  across by glyph index and cmaps unioned, so every subset file is
  complete (39 outlines completed on the reference book; missing post
  tables synthesized). 2 new tests incl. the no-cmap case.
- **Unique CSS family per font resource** (`outputs/font_naming.py`,
  shared by css_output + text_renderer): `"Family lfXXXXXXXX"` — two
  subsets of one typeface can never shadow each other's @font-face;
  original family kept in the stack as local fallback.
- **Width fitting** (`normalize_idm.py`): per-block `letter_spacing`
  computed from the extracted font's real advances so rendered width ==
  the PDF's bbox width — reproduces the aggregate effect of Tc/Tw/Tz/TJ
  with CSS letter-spacing's identical trailing-advance semantics.
  Guards: skip rotated/RTL/low-glyph-coverage/implausible corrections.
  Measured: average overlay width error dropped 4–28× per page (e.g.
  page 12: 11.5px → 0.4px; page 5: 24.9px → 3.4px; worst 42px → ~6px).
  7 new tests.
- **Span-level font-size** (mixed-size lines: drop caps, superscripts)
  and **richer weight mapping** (thin/light/medium/semibold/extrabold/
  black → numeric CSS weights).

Frontend (UI/UX):

- **Bottom dock collapses to its tab strip and STARTS collapsed** — the
  canvas gets the height back (the "viewer is small, logs fill the
  bottom" complaint). Expand by clicking any tab or Ctrl+J; resizable
  when open; layout key versioned so the new default reaches everyone.
- **Thumbnail rail toggle** in the viewer toolbar (persisted).
- **Dashboard rebuilt per the approved hi-fi design**: whole-page drop
  target, live conversion card, production-summary tiles, recent
  projects as cards with real page-1 raster thumbnails and
  status-driven actions — all from `components/ui` primitives.

### Added — Phase 2 / Sub-phase 2C: Compare, Validation engine, grouped Properties, tabbed Logs, Conversion Monitor

Frontend-only; completes the Phase 2 workspace feature set. Item-by-item
detail + verification in `docs/PHASE2_IMPLEMENTATION.md` (2C table).
Highlights:

- **Compare** (center tab): Overlay with reconstruction-opacity slider +
  layer isolation, and Split view (source raster beside the live iframe,
  pan-synced by construction). Replaces the stabilization-phase
  `AccuracyDebugView`. Page/zoom context carries across mode switches.
- **Validation** (center tab): engine in a Web Worker — per-page,
  progressive, cancelable — checking layout bounds, empty text,
  non-web-embedded fonts, and missing assets from the IDM only. Findings
  persist in the Document Manager; clicking one jumps the Viewer to the
  page and highlights the object through the one selection pipeline.
  Proof it earns its keep: on a pre-CFF-fix conversion it automatically
  flags the exact page-26 fallback-font bug previously found by eye.
  `validate.run` command enabled (emits `validation:run` on the app bus;
  `CommandContext` gained `bus`).
- **Properties**: collapsible Geometry/Typography/Appearance/Metadata/
  Advanced groups via `DocumentManager.getObject`/`getFont`, including a
  "fallback — not embedded" font warning. No fabricated data.
- **Bottom dock**: Job log · Conversion Monitor (honest single-job view)
  · Application/Conversion/Performance tails (fetch-on-open + refresh).
- **Cleanup**: `ViewerDebugPanel`/`AccuracyDebugView`/`ComingSoon`
  removed; developer diagnostics now on `Ctrl+Shift+D`.
- **Architecture fixes** surfaced by verification: the workspace ROUTE
  now owns `WorkspaceService.openProject` (panels work when entered
  directly via `?panel=…`), and the viewer re-anchors on tab return
  (initial IntersectionObserver suppression + scroll-into-view), fixing a
  scroll-promotion cascade that lost the operator's page.

### Fixed — bare-CFF (Type1C) fonts now recovered as web fonts (page-26 doubling)

User-reported accuracy bug: the reference book's page 26 title ("Your
Story Book!", 42pt `BHEMPQ+HelveticaRounded-Bold`) rendered visibly
doubled — overlay text ghosting against the rasterized background.
Root cause: the font is embedded in the PDF as a **bare CFF font
program** (Type1C, 1.2 KB), which `ExtractFontsStage` deliberately
dropped as non-web-loadable; the browser substituted a fallback font
whose metrics diverge badly at display sizes.

Fix (`_wrap_bare_cff` in `extract_fonts.py`): rebuild the bare CFF into
a complete OpenType file — advance widths and bounds recovered by
drawing each charstring, cmap recovered from the AGL glyph names PDF
subsets use, outlines re-emitted through `T2CharStringPen` (flattening
subroutines so the rebuilt CFF is self-contained), sfnt tables
synthesized via `FontBuilder`. Wrapped fonts save as `.otf`; the CSS
generator already emits `format("opentype")`. Unparseable programs
still return None (same contract as `_sanitize_for_web`).

Follow-up (same page, reported after the wrap fix): the recovered font
loaded but the title still ghosted against the background — the wrapped
OTF's line metrics were synthesized from **glyph bounds** (737/-207 for
this 12-glyph subset), while the PDF's font declares ascender/descender
0.963/-0.214. NormalizeIdmStage derives `line_height` from MuPDF's
ascender/descender and the browser derives the baseline from the font
file's metric tables, so the mismatch painted every glyph ~4.6pt above
the raster. `_wrap_bare_cff` now reads the real metrics from
`fitz.Font(fontbuffer=…)` — the same parser extraction used — and writes
them identically to hhea, sTypo\*, and usWin\* (different platforms pick
different pairs). Measured result: title baseline 70.59px vs ground
truth 71.04px — the residual 0.45px is Chrome's integer-pixel ascent
rounding, the same sub-pixel tolerance as every other page.

Verified: 4 new unit tests (65 total passing), including the accuracy
contract "wrapped OTF line metrics == MuPDF metrics for the same
buffer"; fresh conversion shows `document.fonts` → `loaded` and page 26
rendering single-imaged at 200% zoom. Note: projects converted before
this fix retain their old output — re-run the conversion (re-import the
PDF) to regenerate.

### Added — Phase 2 / Sub-phase 2B: advanced document viewer

Frontend-only (no pipeline/generator/`IframeRenderer`-core changes). Full
item-by-item detail + verification results in
`docs/PHASE2_IMPLEMENTATION.md` (2B table).

- **Windowing with a hard iframe cap**: the engine maintains a contiguous
  strip of mounted pages around the anchor (`MAX_MOUNTED_PAGES = 9`),
  growing as the operator reads and evicting the end farthest from the
  anchor (≡ least-recently-visible for linear reading; long jumps reset
  the strip). `useViewerWindow` promotes the most-visible page via
  IntersectionObserver with a `"scroll"` navigation source so the canvas
  never scroll-fights the user; programmatic jumps scroll into view.
  Verified: exactly 9 iframes while paging 14× deep into a real document.
- **Thumbnail rail**: manually virtualized plain `<img loading="lazy">`
  rows reusing the page background rasters (no backend changes, no
  iframes); click navigates; follows the current page.
- **View modes**: Continuous / Single / Facing / Book — spread modes mount
  exactly their spread (`spreadFor`/`groupIntoSpreads`); `view.setMode`
  command enabled.
- **Zoom & keyboard**: Fit Page, preset-stepped `zoom.in`/`zoom.out`
  commands, editable go-to-page field; PgUp/PgDn/Home/End,
  Ctrl+= / Ctrl+- / Ctrl+0, Ctrl+F per the approved keyboard map.
- **Incremental document search** (Ctrl+F): debounced UI over the Document
  Manager's background-chunked search with progressive results;
  Enter/Shift+Enter cycle matches; jumps highlight the matched block
  inside the rendered page via its `data-object-id` and announce it
  through the same `SelectionChanged` event Selection uses — one
  selection pipeline, no parallel identity.

### Added — Phase 2: design-system tokens, dark theme, ui primitive library

Implements the approved product design package (`docs/design/`, ratified
2026-07-02) in the frontend. No backend changes.

- **`styles/tokens.css` extended** to the full design-system token set
  (docs/design/09_DESIGN_SYSTEM.md): radius scale (`--lf-radius-sm/-/lg`
  4/6/8px), type scale (`--lf-fs-xs..xl`), spacing (`lg`/`xl`), mono font,
  control metrics, `--lf-bg-gutter`, `--lf-selection-outline`,
  `--lf-compare-diff`, overlay shadow — shipped light values unchanged —
  plus the complete **dark theme** as a token swap under
  `[data-lf-theme="dark"]` (never a component fork). The Bootstrap
  variable bridge now covers both `data-bs-theme` values.
- **Theme service** (`theme/theme.ts` + `hooks/useTheme.ts`): persisted
  (`lf.theme`), applied before first paint (no light flash), keeps
  `data-bs-theme` in sync. Exposed as commands — `view.setTheme` /
  `view.toggleTheme` — so a future palette/keybinding gets theming for
  free; Settings gained an Appearance section (the first `components/ui`
  consumer) that dispatches them.
- **`components/ui/` primitive library** (Button, IconButton, Badge —
  the only way status renders, Tabs, Toolbar(+Separator/Spacer),
  Progress, Slider, EmptyState, Skeleton) styled exclusively from tokens
  in the new `styles/ui.css` (`lfui-` prefix; reference styling
  `docs/design/hifi/lf-mockup.css`). Tree/VirtualTable deliberately
  deferred to their first real consumers (2B/2C).
- **Hard-coded surface colors removed** (`bg-white`/`bg-light`/`#e9ecef`/
  `#fff8e6` → tokens or the new `.lf-surface` class) in Toolbar,
  PreviewPane, ProjectExplorer, PropertiesPanel, layout.css, shell.css.
  Per the approved design, the viewer gutter is now neutral-dark
  (`--lf-bg-gutter`) in BOTH themes so document colors read true; the
  page host itself stays literal white — the document is never themed
  (`IframeRenderer` untouched).
- **Verified**: `tsc -b` + `vite build` clean; real-browser pass at
  1440×900 against the live backend and the real 27-page project —
  theme toggles from Settings via commands, persists across reload and
  navigation, workspace + document render correctly in both themes,
  zero console errors, windowed iframe count unchanged.

### Added — Phase 2 / Sub-phase 2A: Production Publishing Workspace shell

Rebuilt the frontend from a single fixed CSS-grid layout into a Production
Publishing Workspace shell — a light-themed, resizable, docked desktop
application UI, architected as an extensible platform (command system,
app-wide event bus, plugin extension points, a Document Manager enforcing
Large Document memory rules) rather than a one-off viewer redesign. No
backend pipeline/extraction/generator/`IframeRenderer`-core changes.
Full architecture + Mermaid diagram in the new `docs/ARCHITECTURE.md`;
execution checklist in the new `docs/PHASE2_IMPLEMENTATION.md`.

- **Backend** (read-only; derived from already-persisted `idm.json` + DB +
  filesystem — no pipeline stage added):
  - `GET /api/projects/{id}/summary` (`SummaryService`,
    `schemas/summary.py`): one consolidated `ProjectSummary` — project,
    statistics (page/html/css/image/font/text-block counts,
    `disk_size_bytes`), manifest (pages/fonts/assets from `idm.json`, or
    `null` before the pipeline has produced one), health
    (`storage_ok`/`idm_ok`/`all_pages_rendered`), progress (latest job or
    `null`), warnings (e.g. a font file referenced by the IDM but missing
    on disk), and a small recent-`application.log` snippet.
  - `GET /api/logs?stream=application|conversion|performance&tail=N`
    (`LogsService`, `schemas/logs.py`): tails one of the three rotating log
    files. `stream` is a `Literal` type — FastAPI rejects anything else
    with a 422 before the handler runs, so only a fixed filename is ever
    read, never an arbitrary path.
  - `StorageService.logs_dir` property added (mirrors the existing
    `fonts_dir`/`images_dir` pattern) so both new services reach the log
    directory without reaching into `Settings` directly.
  - 7 new backend tests (`test_summary.py`, `test_logs.py`), including a
    project with no completed job yet (idm.json not written) to prove the
    summary endpoint degrades honestly — `manifest: null`, `idm_ok: false`
    — rather than crashing or fabricating data. 61 backend tests passing.
- **Command Registry** (`frontend/src/commands/`): `CommandRegistry` +
  `Command { id, title, group, run, enabled?, keybinding? }`. UI controls
  call `useCommand()` (`hooks/useCommand.ts`) instead of reaching into
  `ViewerEngine` or another panel directly — `navigate.*`/`zoom.*` wrap
  today's real engine calls; `view.*`/`validate.*`/`export.*` are
  registered now but `enabled: () => false` until 2B/2C/Phase 4 implement
  them, so they're discoverable without pretending to work.
- **App Event Bus** (`context/EventBusContext.tsx`): promotes the existing
  viewer `EventBus<T>` class to an app-wide bus (`project:selected`,
  `selection:changed` today — the set grows as 2B/2C add producers).
- **Document Manager** (`document/DocumentManager.ts`, `idmTypes.ts`): the
  single frontend owner of a project's `idm.json`. Lazily fetched, cached
  behind a 2-project LRU cap (`storeInCache` evicts the oldest), exposes
  `getPage`/`getObject`/`search` (chunked, yields to the event loop between
  20-page batches) so a 2,000-page document's search index never blocks a
  frame. Documented honestly: this is the seam, not full server-side
  streaming — the whole `idm.json` is still fetched once per project (no
  backend support yet for a partial fetch); true incremental/streaming IDM
  access is reserved for Phase 2.5.
- **Context providers** (`context/`, `app/AppProviders.tsx`): `WorkspaceContext`
  (wraps the existing `useProjectWorkspace` in one shared Provider instead
  of re-instantiating its polling loop per consumer), `ViewerEngineContext`
  (creates the `ViewerEngine` singleton once via `useRef`, above the
  router, so route changes never remount iframes), `DocumentManagerContext`,
  `CommandContext`. Provider order matters: `EventBus` is outermost since
  both `WorkspaceContext` and `ViewerEngineContext` publish onto it.
- **Router + shell** (`react-router-dom`, `layout/ShellLayout.tsx`,
  `layout/NavRail.tsx`, `routes/`): global routes `/dashboard`, `/projects`,
  `/conversion`, `/settings`, plus `/workspace/:projectId`. Compare,
  Validation, Logs, and Properties are **dockable panels/tabs inside the one
  workspace route** (`?panel=` on the URL is the source of truth), not
  separate page destinations — matching desktop publishing software rather
  than a CRUD dashboard. `NavRail`'s context group (shown only when a
  project is open) computes its own active-tab state from `?panel=` rather
  than relying on `NavLink`'s built-in `isActive` — which only compares
  pathname, so all four panel links share one pathname and would otherwise
  all appear active simultaneously.
- **Resizable docking layout** (`react-resizable-panels`,
  `layout/ProductionWorkspaceLayout.tsx`): nested `PanelGroup`s — outer
  vertical (main row over the bottom Logs dock), inner horizontal (Explorer
  | center tab strip | Properties). Every group has an `autoSaveId` so
  panel sizes persist to `localStorage` across reloads (verified).
- **IDE-style Project Explorer** (`panels/ExplorerPanel.tsx`,
  `panels/ProjectTree.tsx`): `Source → Pages → Resources
  (Fonts/Images/CSS) → Output (HTML/Manifest) → Reports`, built from
  `GET .../summary`. Deliberately caps listed items at 20 with a "+N more"
  note instead of rendering one DOM node per page/font — a 2,000-page,
  50,000-image document must never force this tree to dump tens of
  thousands of nodes (Large Document Architecture memory rules, honored
  starting now rather than deferred to 2B).
- **Dashboard** (`routes/DashboardPage.tsx`): drag-and-drop + browse upload,
  recent projects (sorted by `updated_at`), statistics cards computed
  client-side from the already-fetched project list (no extra network
  calls), the one actively-tracked conversion job, and an
  `application.log` snippet via the new logs endpoint. "Active Conversion"
  intentionally reflects `useProjectWorkspace`'s real capability (one
  tracked job) rather than presenting a multi-job queue UI with nothing
  behind it — a true queue view is Conversion Monitor's job in 2C.
- **Design tokens** (`styles/tokens.css`, `shell.css`, `viewer.css`):
  `--lf-*` custom properties + `--bs-*` overrides under
  `<html data-bs-theme="light">`; desktop density (`0.875rem` base font,
  compact controls). `layout.css` (Phase 1) is retained unchanged — panel
  *content* keeps its existing styling; the new files only cover shell/
  workspace/dock chrome.
- **`ComingSoon` component** (`components/ComingSoon.tsx`): shown for
  Compare/Validation until 2C — an honest "planned for sub-phase 2C" rather
  than a fake or broken panel.
- Retired `components/AppLayout.tsx` — its logic is now split across
  `ShellLayout` (chrome) and `WorkspacePage` (panel assembly).

Verified end-to-end with a headless browser and a real PDF upload (zero
console errors): all four global routes navigate correctly; upload → project
opens at `/workspace/:id`; the IDE Explorer tree renders real page/font/asset
counts; center-dock tab switching works and Compare/Validation show the
honest placeholder; panel resize **persists across a full page reload**
(`autoSaveId` + `localStorage`); navigating away from the workspace and back
leaves **exactly one iframe per mounted page** — the existing StrictMode
duplicate-mount generation guard in `ViewerEngine.mountPage` holds under the
new routing/remounting conditions.

### Fixed — Each preview page rendered twice (duplicate stacked iframes)

After the iframe rendering fix above, every page showed its content
twice, stacked vertically. Cause: `React.StrictMode` (`main.tsx`)
double-invokes effects on mount in dev. `ViewerEngine.mountPage()`
synchronously appended a new `<iframe>` into the host element and only
recorded the page as mounted (`this.mounted.set(...)`) *after* its
`await renderer.load(url)` resolved. When StrictMode fired the mount
effect a second time before the first call's `await` finished, the
existing "clear before mounting" guard found nothing recorded yet and
let a second iframe get appended to the same host.

Fixed with a per-page generation counter in `ViewerEngine`: incremented
synchronously at the start of every `mountPage()` call, plus an
immediate `host.innerHTML = ""` before creating the renderer. After the
`await`, a call checks whether it's still the latest generation for
that page — if a newer call started in the meantime, the stale one
discards its own iframe and returns without touching shared state.
Verified with a headless browser under the same dev/StrictMode
conditions that reproduced the bug: exactly one `<iframe>` per page host.

### Redesigned — Single iframe rendering path; self-contained relative-URL HTML

**The definitive root cause** (found by instrumenting the running viewer,
not guessing): `@font-face` rules injected inside a Shadow DOM `<style>`
tag never register in `document.fonts` — the browser measured
`document.fonts` as an empty set, so `await document.fonts.ready` resolved
instantly, the page painted with fallback-font glyph metrics, and the real
font swapped in afterward, shifting/collapsing every line. Meanwhile the
backend-**served** page (verified headless) rendered perfectly. So the
HTML/CSS/fonts were always correct; only the Shadow DOM rendering path was
broken.

**The fix** — one rendering path, matching what a browser does natively:

- **Frontend now renders each page in a same-origin `<iframe>`**
  (`IframeRenderer.ts`) pointing at the served
  `/static/projects/{id}/pages/page_XXXX.html`. The iframe is a real
  document: it resolves the page's relative URLs, loads `@font-face` fonts
  at the document level (so `contentDocument.fonts.ready` is meaningful and
  awaited before the page is considered ready), and paints identically to
  opening the file directly. Deleted `ShadowRenderer.ts`, `PageLoader.ts`,
  and the `applyWidthCorrections()` / visibility-gate hacks entirely.
  `Selection` and the Accuracy Debug layer toggles now operate on the
  iframe's `contentDocument` (same-origin, fully accessible).
- **Generator reverted to relative, self-contained URLs**
  (`../resources/...`, `../fonts/...`): a project workspace now renders
  identically opened from disk (`file://`), served by the backend, or in
  the iframe — with zero per-renderer URL rewriting. This also restores the
  direct-file-open workflow that absolute `/static/...` URLs had broken.
  (`paths.py` `resource_href`, `css_output.py`, `image_renderer.py`,
  `html_output.py`.)
- `common.css` now resets `html, body { margin: 0 }` so `.lf-page` sits at
  the iframe origin (the UA default 8px body margin would otherwise offset
  the page).
- Verified end-to-end with a headless browser on a freshly-uploaded PDF:
  the preview iframe reports `QikkiReg=loaded`, text-block rendered width
  matches the CSS/PDF width (119 vs 118.5px), no failed resources, no
  console errors, and click-to-select returns the correct IDM object id.

### Fixed — Font/width mismatch in Shadow DOM viewer vs direct HTML view

HTML viewed directly in a browser rendered correctly (font and positions
right). The same page in the React Shadow DOM viewer showed text overlap
and the wrong font. Two separate root causes:

1. **GentiumPlus font not sanitized**: the certificate project's font
   file (`GentiumPlus`, 54KB) was written with raw PDF-embedded bytes
   (unsanitized), causing browser OTS to silently reject it and fall back
   to `sans-serif`. The retroactive sanitization script had run before this
   project was uploaded, so it wasn't covered. Fixed by re-running
   `fontTools.TTFont().save()` on the file in place — no re-upload needed.
   Added a note that any project uploaded while an old backend was running
   needs this pass; the running pipeline now sanitizes automatically.

2. **`applyWidthCorrections` measuring fallback-font metrics, not real
   font metrics**: one `requestAnimationFrame` is not enough time for
   `@font-face` fonts to finish loading (network fetch + parse +
   rasterize), so `scrollWidth` was read with `sans-serif` metrics, a
   wrong `scaleX` was applied, then the real font loaded on top — making
   things worse than no correction at all. Fixed: now `await
   document.fonts.ready` before the `requestAnimationFrame`, so
   corrections are only measured and applied after fonts are confirmed
   loaded. (`document.fonts` is a shared `FontFaceSet` that includes fonts
   declared inside Shadow DOM `<style>` tags in Chrome and Firefox.)

### Fixed — Text width mismatch causing visual overflow and overlap

HTML text blocks rendered wider than the PDF-measured bounding box because
the browser's actual glyph metrics for the loaded font differ from what
PyMuPDF calculated — which compounds across characters and causes text to
bleed into neighboring blocks, making the overlay look doubled against the
background. Fixed with browser-side scaleX correction:

- `text_block.html` template now includes `data-width="{{ bbox_width }}"` on
  every `<p>` (the PDF-measured line width from `bbox.width`).
- `ShadowRenderer.applyWidthCorrections()`: after layout, queries all
  `.lf-text-block` elements, reads `scrollWidth` (actual rendered glyph
  width) vs `data-width` (expected), and applies `transform: scaleX(expected
  / actual)` whenever the difference exceeds 0.5% — forcing each text block
  to exactly fill the PDF-measured space regardless of font-metric differences.
- `ViewerEngine.mountPage()`: calls `applyWidthCorrections()` inside a
  `requestAnimationFrame` callback so layout is fully committed before
  `scrollWidth` is read (reading it before layout would return 0 or stale
  values, applying wrong scale).

### Fixed — Per-word/per-run color not preserved (multi-span lines)

User reported: colored words within a line rendered as a single flat
color (e.g. `"Monkey Pen's"` in blue / `"Vision is to..."` in black /
`"free children's"` in orange all rendered blue). Diagnosed: real PDF
line had **3 spans with 3 different colors** in PyMuPDF's dict; our
extraction previously took only `spans[0]`'s color for the whole line
and concatenated all text under it — confirmed in practice:
`"Monkey Pen's Vision is to provide thousands of free children's "` is
genuinely one PDF line with 3 spans of colors `3967946`, `0`,
`13786919`.

- `TextSpan` dataclass added to IDM
  (`pipeline/elements/textbox.py`): `text`, `font_id`, `font_size`,
  `color` — one entry per PyMuPDF span within a line, preserving
  per-run styling.
- `TextBlock.spans: list[TextSpan]` added; the existing `text`/
  `font_id`/`font_size`/`color` block-level fields now mirror the
  first span for backward-compatible line-level approximations (search,
  plain-text export) without breaking any existing code paths.
- `ExtractTextStage` now builds `TextBlock.spans` from all spans in
  the line (each with its own color/font resolution), not only
  `spans[0]`.
- `TextRenderer` passes the full spans list to Jinja; `text_block.html`
  now renders one `<span style="color:...; font-family:...">` per span
  (inline styles, which override the parent `<p>`'s CSS color/font).
- XSS-escaping test updated to mutate the span's text, not only the
  block's text field, since the renderer now reads from `spans` directly.
- Tests (`test_multispan_color.py`): constructs a PDF with 3 colored
  text runs on one baseline (via `fitz.insert_text` + `get_text_length`
  offsets), asserts 3 `TextSpan`s extracted with correct colors, asserts
  generated HTML contains exactly 3 `<span>` elements with distinct
  inline color styles inside a single `<p>`. 54 backend tests passing.

### Fixed/Added — Phase 2A: Layout Accuracy investigation

Diagnostic order followed exactly as directed (background image content →
IDM-vs-HTML element counts → first-five TextBlock dump → hierarchy
verification → 1:1 mapping check), no fix attempted until root cause
identified:

- **Confirmed clean (no bug)**: extraction creates exactly one
  `TextBlock` per PDF line (`extract_text.py` iterates `block.lines`,
  never the parent block or per-span); HTML generation creates exactly
  one `<p>` per `TextBlock` (`page_renderer.py`, single list
  comprehension). IDM text-block count matched generated `<p>` count
  exactly (2 and 2) on the test PDF — ruled out hierarchy duplication and
  rendering duplication entirely.
- **Confirmed bug #1 (architectural, left as-is per explicit direction)**:
  `page_0001_bg.png` was opened and visually inspected — it already
  contains "By T. Albert" / "Illustrated by: ..." fully rasterized, plus
  decorative title art. `RenderBackgroundsStage`'s `get_pixmap()` call has
  no mechanism to exclude text. The IDM's separately-extracted text is
  then overlaid on top of a background that already contains it. Not
  fixed — removing text from the background before the overlay is
  accurate would make output look worse per explicit instruction.
- **Found and fixed bug #2 (the dominant contributor to "larger/shifted"
  text)**: used `document.fonts` in a real browser to check actual
  `@font-face` load status — the font used by the test PDF's title page
  reported `status: "error"`, NOT `"loaded"`. Browser had silently
  substituted `sans-serif`, producing a measured ~17% width mismatch
  against the PDF-derived box. Root cause: PDF-embedded font subsets are
  frequently valid enough for a PDF renderer but fail browser OTS
  sanitization (confirmed: `fontTools` could parse the font fine,
  `fontTools.TTFont(...).save()` resaving the *same bytes* — recomputing
  checksums and normalizing the table directory — made
  `document.fonts` report `status: "loaded"`). Fixed in
  `ExtractFontsStage` (`_sanitize_for_web`): every extracted `ttf`/`otf`
  font is now re-saved through fontTools before being written; formats
  that were never web-loadable to begin with (bare `cff`, etc.) are no
  longer written at all rather than served as a file that will only fail
  silently in the browser.
- IDM `TextBlock` expanded with `origin_x`/`origin_y`, `ascender`,
  `descender` (real PyMuPDF span values, not derived) and reserved
  `horizontal_scale`/`render_mode` fields (documented as not-yet-extracted
  — `Tc`/`Tw`/`Tz`/`Tr` live in raw content-stream operators that
  `get_text("dict")` doesn't expose).
- `NormalizeIdmStage.line_height` now computed from real
  `(ascender - descender) * font_size` instead of a flat `font_size *
  1.2` guess, falling back to the guess only when metrics are unavailable.
- `common.css`'s `.lf-text-block` changed from `white-space: pre-wrap` to
  `nowrap`: a width mismatch (from font substitution) combined with
  wrapping turned a small horizontal overflow into much worse multi-line
  height/position corruption (confirmed: a 2-word title rendered at 2x
  the expected height before this change, 1x after).
- **Accuracy Debug View** (`AccuracyDebugView.tsx`,
  `ShadowRenderer.applyAccuracySettings`, `ViewerEngine.setAccuracySettings`):
  Background-only / Overlay-only / Combined modes + overlay opacity
  slider, added as a permanent diagnostic, not a one-off debugging hack.
  Used to directly confirm the font fix: Background-only (ground truth)
  and Overlay-only (our reconstruction) now show matching fonts and
  closely matching text position.
- Tests: font sanitization (valid TTF round-trips and stays parseable,
  non-web formats rejected, corrupt input handled gracefully — using an
  in-memory minimal TTF built via `fontTools.fontBuilder` so the test has
  no external file dependency), new `TextBlock` field population,
  ascender/descender-derived `line_height`. 52 backend tests passing.
- Re-verified end-to-end on a **fresh upload** (not a manually-patched
  file) of the same real-world PDF that exhibited the bug: font now
  reports `status: "loaded"`; Background-only vs. Overlay-only comparison
  in the Accuracy Debug View confirms matching fonts and position.

### Fixed — Root cause of `/api/version` and `/static/.../.static_ok` 404s

- Both endpoints were correctly implemented and registered in the
  repository; the 404s came from a real, live backend process (`uvicorn
  --reload`, PID 500) that had been running since before these endpoints
  existed. Its `--reload` file watcher had stopped picking up changes (for
  reasons not fully diagnosed — possibly the long-running watch session
  predating several rounds of file additions), so it kept serving a build
  several tasks old: no `/api/version`, no `/api/projects/{id}/pages`, and
  an older `/api/health` shape missing `storage_ok`.
- This corrects an earlier misdiagnosis from the prior stabilization pass:
  a process on port 8000 (PID 13392) had been assumed to be an orphaned,
  unkillable kernel socket because `tasklist`/`Stop-Process` reported it
  as not found. It was not orphaned — `uvicorn --reload` spawns a
  *separate child worker process* (visible via
  `Get-CimInstance Win32_Process | Select ProcessId,ParentProcessId`) that
  actually holds the listening socket; killing only the parent reloader
  left the child running and the port occupied. Killing the full process
  tree (parent + child) freed the port for good.
- Added an explicit, named startup self-check (`_run_startup_self_check`
  in `main.py`) distinct from the full route dump: logs `[OK] /api/version`,
  `[OK] /api/health`, `[OK] Static mount`, or `[FAIL] ... is NOT
  registered` if any are missing from `app.routes`.
- `.static_ok` is now only written if it doesn't already exist (was
  unconditionally overwritten on every startup before).
- Added `test_version_and_static_marker_contract_returns_200`: an explicit
  integration test that fails loudly if either endpoint returns anything
  but 200, separate from the more general checks already in place. 49
  backend tests passing.
- **Process-hygiene takeaway for future `--reload` use**: if a long-running
  `--reload` session seems to be ignoring code changes, restarting it
  fully (not just trusting the watcher) requires killing both the reloader
  *and* its spawned worker — `Get-CimInstance Win32_Process -Filter
  "Name='python.exe'" | Select ProcessId,ParentProcessId,CommandLine` finds
  both.

### Added — Phase 1 final hardening pass

- `GET /api/version` (`version`, `build` — server start time, `git_commit`
  — best-effort, `null` outside a git repo, `api_version`).
- `GET /api/health` extended with `storage_ok`.
- Startup route validation: every registered route is logged
  (`[OK] GET /api/projects/{id}/pages`, etc.) to `application.log`, plus a
  `.static_ok` marker file written into `storage/projects/` so the
  frontend can confirm the static mount actually serves files.
- Frontend `environment/` module: `checkEnvironment()` (backend reachable
  → API version matches `EXPECTED_API_VERSION` → static mount → storage),
  surfaced as four toolbar badges (Backend/Storage/Static/API) with a
  manual recheck button, plus a blocking red banner for the two failures
  severe enough nothing else can be trusted (backend unreachable / API
  version mismatch) — explicit instruction was "never fail silently."
- Guarded project-open sequence (`environment/PreviewError.ts`): version →
  health → the real request. A failure now renders a specific
  Reason/Expected/Suggestions block in the preview pane instead of an
  empty "no pages" state indistinguishable from "nothing selected."
- `ApiError` (carries HTTP status + URL) added to the API client so
  callers can branch on *why* a request failed, not just that it did.
- Tests: 4 new backend tests (`storage_ok`, version shape, static marker
  serving, full expected-route-set registration). 48 backend tests
  passing.
- **Fixed a real bug found during verification**: the startup route log's
  `✓` character broke `RotatingFileHandler` on Windows' default (non-UTF8)
  file encoding — `logging` caught the `UnicodeEncodeError` internally and
  silently dropped the log line instead of crashing, so the app kept
  running but `application.log` lost that line. Fixed by adding
  `encoding="utf-8"` to all three log handlers and switching the startup
  log symbol to ASCII (`[OK]`) so console output isn't at the mercy of the
  terminal's codepage either.
- Verified all four hardening scenarios live in a browser: clean
  environment (all four badges green, normal upload/preview flow
  unaffected), and a forced API-version mismatch (`API_VERSION=2`)
  correctly shows the red `API ✗` badge and the blocking mismatch banner
  with no layout breakage.

### Added — Phase 1.5: Stabilization

- Investigated the reported "preview doesn't work" risk before any new
  feature work, per explicit instruction to stop and stabilize. Findings:
  - The viewer code itself was already correct as of Task 6 (confirmed by
    re-running its verification, which passed).
  - Identified the most likely real-world cause: an old backend process
    left running on port 8000 from earlier in development, serving code
    from before the `/pages` endpoint and static mount existed. Any
    browser session pointed at that stale process would see the viewer's
    correct "no pages" empty state — indistinguishable from "broken"
    without server-side visibility. This is an environment/process-hygiene
    issue, not an application bug.
  - Separately surfaced a genuine OS-level anomaly on the dev machine: a
    listening socket on port 8000 attributed to a PID that no longer
    exists (confirmed via `tasklist`/`taskkill`), survives process kills,
    and requires either an elevated-terminal kill or a reboot to clear —
    documented for awareness, not a code fix.
- Added a single state machine to `ViewerEngine`
  (`idle → opening_project → loading_assets → rendering → ready`, or
  `→ error`) replacing what would otherwise be scattered booleans, plus a
  `DiagnosticsSnapshot` (state, mounted pages, missing assets, last error)
  emitted via a new `DiagnosticsChanged` event.
- Added structured per-page logging (`viewer/diagnostics.ts`,
  `[Viewer] Opening Page` → `HTML Loaded`/`CSS Loaded` → `Shadow DOM
  Mounted` → `Ready`, or an error at any step) so a future load issue is
  diagnosable from the browser console alone.
- Added non-blocking image-load tracking: every `<img>` inside a mounted
  page's Shadow DOM is watched for `error` events, recorded as a "missing
  asset" — visible without ever delaying the page's `ready` state (images
  load progressively, same as any normal web page).
- Added a **temporary** `ViewerDebugPanel` (toggle in the preview
  toolbar): current state, mounted pages, zoom, missing assets, last
  error. Explicitly marked for removal once preview reliability is no
  longer in question.
- Re-verified end-to-end with diagnostics active, on a clean backend
  instance, with no manual refresh or workaround beyond the
  already-documented port issue: upload → select → debug panel reaches
  `state: ready` → both pages mounted → zero missing assets → zero
  browser console errors. Screenshot confirms the actual PDF page content
  renders correctly.
- Explicitly deferred (per instruction: stabilize before any of this):
  Vitest setup, Alembic migrations, and any Task 7 feature work.

### Added — Phase 1 / Task 6: Viewer

- `frontend/src/viewer/`: a framework-agnostic viewer engine, not a
  temporary preview component — `ViewerEngine` (orchestrator),
  `PageLoader` (fetches generated HTML/CSS, rewrites relative paths to
  absolute static URLs), `ShadowRenderer` (mounts one page into an
  isolated Shadow DOM root), `NavigationManager` (next/prev/jump/first/
  last), `ZoomManager` (fixed percentages + fit-width/fit-page), `Viewport`
  (virtualization — only the current page ± 1 are ever mounted),
  `Selection` (click → nearest `data-object-id` ancestor → `SelectionInfo`),
  and a minimal typed `EventBus` (`ProjectOpened`, `PageLoaded`,
  `PageRendered`, `PageChanged`, `ZoomChanged`, `SelectionChanged`).
- `data-object-id` (the raw IDM UUID, no `tb-`/`img-`/`shape-` prefix)
  added to every generated element in `text_block.html`, `image.html`,
  `shape.html` — a future editor resolves a clicked element to its IDM
  object with zero DOM parsing.
- Backend: `GET /api/projects/{id}/pages` (page geometry + html/css/
  background paths) and a read-only static mount at
  `/static/projects/{id}/...` serving each project's generated output
  directly, so the frontend can fetch and inject it into a Shadow DOM.
- `PreviewPane` rewritten as a thin shell: clicking a project in
  `ProjectExplorer` opens it in the viewer; a toolbar drives navigation and
  zoom; `PropertiesPanel` renders whatever `SelectionChanged` last reported.
- Tests: 2 new backend tests (pages list shape, static file serving). 44
  backend tests passing. No frontend unit-test framework exists yet (noted
  as a gap); verified instead via `tsc` type-checking, a clean
  production build, and a full browser-driven pass (Playwright, used
  temporarily and removed afterward) that uploaded a real 27-page PDF,
  selected it, confirmed exactly 2 page hosts existed in the DOM
  (virtualization), navigated 1→2, changed zoom (scale 1→1.5), and clicked
  a real text block — the Properties panel correctly showed its IDM UUID.
- Fixed during verification: `PreviewPane` never showed any pages on first
  load. Root cause: `NavigationManager.jumpTo(1)` is a no-op when already
  on page 1 (the `useState` default), so `PageChanged` never fired and
  React never learned the engine had pages ready. Fixed by tracking the
  mounted-pages list as explicit state set directly after `openProject`,
  not recomputed inline during render from a non-reactive method call.

### Added — Phase 1 / Task 5: HTML Generation

- `HtmlOutputPlugin` (`backend/app/pipeline/outputs/html_output.py`): reads
  only `context.document` (the IDM), never PyMuPDF. Generates one semantic,
  layered HTML page per Page entirely via Jinja2 templates — no string
  concatenation. Each page has `background`/`images`/`shapes`/`text`/
  `overlay` layer `<div>`s, links `common.css` and its own `page_XXXX.css`,
  and every element keeps its IDM UUID as its DOM id (`tb-{uuid}`,
  `img-{uuid}`) matching the Task 4 CSS selectors exactly, plus `data-*`
  attributes (`data-page`, `data-type`, `data-font`, `data-asset`,
  `data-rotation`, `data-reading-order`, `data-alignment`,
  `data-writing-direction`) so a future editor can address any element
  without re-parsing.
- Renderers split by responsibility (`outputs/renderers/`): `TextRenderer`
  (`<p><span>`, accessible, autoescaped), `ImageRenderer` (resolves an
  `ImageElement`'s `src` from its referenced `AssetResource`),
  `ShapeRenderer` (renders `ShapeElement`s — no stage populates these yet,
  exists for forward compatibility), and `PageRenderer` (orchestrates the
  above and assembles their fragments into `page.html`).
- `HtmlValidator` (`outputs/html_validator.py`): fail-fast pre-write check
  for duplicate element ids and missing `src`/`href` file references —
  raises and aborts the stage rather than writing broken output.
- `GenerateHtmlStage`: thin Stage wrapper, persists each `Page.html_path`.
  Added to the pipeline after `GenerateCssStage`.
- Tests: layered/semantic markup assertions, text-content HTML escaping
  (XSS-safety), validator duplicate-id/missing-file/clean-pass cases,
  `Page.html_path` persistence, and an end-to-end assertion in the full
  upload→pipeline flow. 42 backend tests passing.
- Verified visually: rendered a generated page from the real 27-page test
  PDF in a browser — extracted text overlays the rendered background in
  the exact position it appears in the source PDF.

### Fixed

- `ExtractFontsStage` font-name resolution: `page.get_fonts()` returns the
  subset-prefixed basefont (e.g. `"MVTANU+QikkiReg"`) but
  `page.get_text("dict")` span names strip that prefix (e.g. `"QikkiReg"`),
  so every `TextBlock.font_id` was previously left `null` for subsetted/
  embedded fonts — 100% of text blocks were affected on a real-world test
  PDF. Fixed by registering both the full and stripped name in the
  font-lookup registry; added a regression test plus re-verification
  against the real PDF (0% unresolved, down from 100%).

### Added — Phase 1 / Task 4: CSS Generation

- `CssOutputPlugin` (`backend/app/pipeline/outputs/css_output.py`): the
  first output plugin — reads only `context.document` (the IDM), never
  PyMuPDF. Writes `resources/css/common.css` (shared rules + one
  `@font-face` per embedded font, keyed by font id) and one absolutely-
  positioned `resources/css/page_XXXX.css` per page (one rule per
  `TextBlock`/`ImageElement`, using bbox/font/color/alignment/rotation
  straight from the IDM — no layout computed here).
- `GenerateCssStage`: thin Stage wrapper that runs the plugin and persists
  each `Page.css_path`. Added to the pipeline after `PersistAssetsStage`.
- `OutputPlugin.generate` return type relaxed from `None` to `Any` so a
  plugin can return generated-artifact metadata (e.g. CSS's per-page paths)
  for its Stage to persist.
- Tests: common/per-page file generation, `@font-face` emission for
  embedded fonts (and its absence for non-embedded ones), rotated-text
  transform, `Page.css_path` persistence, and an end-to-end assertion that
  CSS exists in the full upload→pipeline flow. 36 backend tests passing.

### Added — Phase 1 / Task 3: Extraction

- IDM redesign per refined spec: `BoundingBox` (shared by every positioned
  element), `TextBlock` (bbox, font_id, font_size, color, alignment,
  rotation, reading_order, line_height, letter/word spacing, writing
  direction), `ImageElement`/`AssetResource` split (one deduplicated binary
  asset, many page placements), `FontResource` (family, weight, style,
  embedded, subset, encoding, filename), and `Page` (crop_box, media_box,
  fonts_used added). `Document`/every element now has `to_dict`/`from_dict`.
- `StorageService.save_idm`/`load_idm`: the full IDM is serialized to
  `storage/projects/{id}/idm.json` after extraction — the contract that
  lets later stages and output plugins reconstruct the Document without
  ever reopening the source PDF.
- Pipeline stages, in the refined order (Validate → Metadata → Render
  Backgrounds → Extract Fonts → Extract Images → Extract Text → Normalize
  IDM → Persist Assets):
  - `RenderBackgroundsStage`: rasterizes each page to PNG at a configurable
    DPI (`Settings.preview_dpi`, default 300; 72/150/300/600 supported).
  - `ExtractFontsStage`: discovers fonts per page (deduped by PDF xref),
    writes embedded font files, infers family/weight/style/subset from the
    PDF font name.
  - `ExtractImagesStage`: extracts embedded images, deduplicated first by
    xref then by content hash, with one `ImageElement` per placement so a
    repeated image is written to disk once.
  - `ExtractTextStage`: flattens PyMuPDF's block→line→span hierarchy to one
    `TextBlock` per line, resolving each block's font reference.
  - `NormalizeIdmStage`: assigns reading order (top-to-bottom/left-to-right)
    and fills missing line heights — the one place cross-element layout
    decisions belong, keeping extraction stages faithful/un-opinionated.
  - `PersistAssetsStage`: writes deduplicated `Asset`/`AssetPageLink` rows,
    updates each `Page.background_image`, and calls `save_idm`.
  - Every stage logs structured per-page lines (page number, counts,
    duration_ms) to `conversion.log` for debugging.
  - Per-page extraction failures are caught and logged without aborting
    the rest of the document (a corrupt page no longer fails the whole job).
- Database: `Asset` extended with `original_object_id` and a `details` JSON
  column (type-specific extras: dpi/color_space/has_alpha for images;
  family/weight/style/embedded/subset/encoding for fonts); new
  `AssetPageLink` table tracks every page referencing a deduplicated asset.
  `IAssetRepository` gained `get_by_hash`/`add_page_reference`/
  `list_pages_for_asset`; `IPageRepository` gained `update`.
- `ConversionService._build_stages` now wires the full 8-stage pipeline.
- Tests: per-stage unit tests (background rendering, font/image/text
  extraction, cross-page image dedup, rotated pages, empty pages, corrupt-page
  resilience via a monkeypatched `fitz.Page.get_text` failure), a
  `NormalizeIdmStage` reading-order test, a `PersistAssetsStage` dedup test,
  and a full end-to-end test that uploads a PDF with real text/images/fonts,
  runs the pipeline, then reconstructs the `Document` from `idm.json` alone
  to prove the IDM-without-the-PDF contract holds. 31 backend tests passing.

### Added — Phase 1 / Task 1: Setup

- Backend: FastAPI app skeleton (`backend/app/main.py`) with CORS, startup
  storage bootstrap, and DB initialization.
- Database: SQLAlchemy models for `Project`, `Job`, `Page`, `Asset`
  (`backend/app/models/`), SQLite session/engine setup (`backend/app/database/`).
- Pipeline architecture: backend-agnostic `PipelineEngine`
  (`backend/app/pipeline/engine.py`), `PipelineContext`, an Internal Document
  Model (`backend/app/pipeline/document.py` + `pipeline/elements/`: `Page`,
  `TextBlock`/`TextSpan`, `ImageElement`, `ShapeElement`, `FontResource`,
  `AssetResource`), and `Stage`/`OutputPlugin` base classes
  (`pipeline/stages/base.py`, `pipeline/outputs/base.py`) so future stages and
  output formats (EPUB, JSON, XML) plug in without touching the engine.
- API: `GET /api/health` endpoint.
- Logging: three rotating log streams — `application.log`, `conversion.log`,
  `performance.log` — wired via `backend/app/utils/logging_config.py`.
- Frontend: Vite + React + TypeScript + Bootstrap scaffold with the desktop
  shell layout (Toolbar, ProjectExplorer, PreviewPane, PropertiesPanel,
  LogPanel) and a typed API client; toolbar shows live backend connectivity.
- Infra: `docker-compose.yml` wiring backend (`:8000`) and frontend
  (`:5173`) services with a storage bind mount and backend healthcheck;
  per-service `Dockerfile`s; expanded `.env.example`.
- Tests: backend unit tests for the health endpoint and the pipeline engine
  (stage ordering, progress reporting, failure wrapping).

### Added — Pre-Task-2 architectural hardening

- Core: centralized `Settings` under `backend/app/core/config.py` +
  `settings.py` (replaces the old top-level `app/config.py`), with new
  configurable knobs (`max_upload_size_bytes`, `allowed_upload_extensions`,
  `log_level`, `preview_dpi`, `jpeg_quality`).
- Core: closed-set enums in `backend/app/core/enums.py` —
  `ProjectStatus`, `JobStatus`, `PipelineStage`, `AssetType` — replacing
  string constants previously declared inline on the ORM models;
  `Project.status`/`Job.status`/`Asset.type` are now native SQLAlchemy
  `Enum` columns.
- Repositories: `IProjectRepository`/`IJobRepository`/`IPageRepository`/
  `IAssetRepository` interfaces (`backend/app/repositories/interfaces.py`)
  with `SQLite*Repository` implementations (`backend/app/repositories/sqlite/`),
  so a future Postgres/S3/Redis-backed implementation is plug-and-play.
- Events: a lightweight in-process `EventDispatcher`
  (`backend/app/events/dispatcher.py`) with `ProjectCreated`,
  `UploadCompleted`, `JobStarted`, `StageCompleted`, `JobFinished`,
  `ProjectDeleted` event types; a default handler logs every event today.

### Added — Phase 1 / Task 2: Upload

- Validation chain (`backend/app/utils/upload_validation.py`,
  `filenames.py`, `streaming.py`): extension → MIME signature → PDF
  structure (rejects corrupt and password-protected PDFs) — all run
  *before* any project row or storage directory is created, and uploads
  are streamed to disk in chunks with a size limit enforced as they arrive
  rather than buffered fully in memory.
- `StorageService` (`backend/app/services/storage_service.py`): owns the
  per-project on-disk layout (`pages/`, `resources/{images,fonts,css}/`).
- `ProjectService.create_project_from_upload`: runs the validation chain,
  creates the `Project`, stores the source PDF, creates the `Job`, and
  publishes `ProjectCreated`/`UploadCompleted`.
- `ConversionService.run_pipeline`: builds the `PipelineEngine` with the
  current stage list (`ValidateStage`, `MetadataStage`), tracks job
  progress/stage in the DB as each stage completes, and transitions
  `Project.status` through `PROCESSING` → `READY`/`FAILED`.
- Pipeline stages: `ValidateStage` (defense-in-depth re-validation) and
  `MetadataStage` (reads document metadata + per-page dimensions into the
  IDM and persists `Page` rows).
- API: `POST /api/projects` (multipart upload, returns `project_id`/`job_id`
  and schedules the pipeline via `BackgroundTasks`), `GET /api/projects`,
  `GET /api/projects/{id}`, `DELETE /api/projects/{id}`, `GET /api/jobs/{id}`.
- Frontend: working "Upload PDF" control in the Project Explorer
  (`useProjectWorkspace` hook), live job-stage/progress polling rendered in
  the Log Panel, and status badges (created/processing/ready/failed) on each
  project.
- Tests: repositories, event dispatcher, upload validation, `ProjectService`
  (happy path + extension/password-protected rejection), `ConversionService`
  (success and failure status transitions), and a full API integration test
  driving the real multipart upload → job completion → project read →
  delete flow. 21 backend tests passing.
