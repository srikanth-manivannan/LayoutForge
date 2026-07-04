# PRODUCT_PRINCIPLES — The Constitution of LayoutForge Studio

Every future UI, product, and engineering decision is checked against
these principles. A feature that violates one needs an explicit,
documented exception — or a redesign.

Approved as part of the product design package (2026-07-02).

---

## Principle 0 · Production Accuracy First  ⟵ NON-NEGOTIABLE, OUTRANKS ALL

Every feature, optimization, or visual enhancement must preserve the
fidelity of the document. Rendering correctness, pixel accuracy, and
reliable production output always take precedence over visual effects,
animations, or UI polish. **What the operator sees in the workspace is
what will be exported** — the moment that trust breaks, the product is
worthless.

*Precedents already set:* the same-origin-iframe golden rendering path
(preview === standalone browser tab), fontTools sanitization over "ship it
broken", refusing to strip background text until the overlay is provably
accurate, never fabricating confidence data.
*Test:* for any proposed change, ask "can this alter a rendered pixel or
an exported byte?" If yes, it needs verification against the benchmark
corpus before merge.

---

## 1 · One Workspace

The product is a single Production Workspace, not a collection of pages.
Quality tools are panels inside it, never destinations outside it.
*Test:* the Proof → Fix → Validate loop never triggers a route change.

## 2 · One Selection

One selection model (`data-object-id` → `SelectionChanged`) feeds Viewer,
Properties, Validation, Accessibility, Compare, and future editing.
*Test:* exactly one selection code path exists (`viewer/Selection`).

## 3 · IDM is the Source of Truth

Every panel, exporter, validator, and AI feature reads the Internal
Document Model — never the PDF directly, never scraped DOM, never a
parallel model. `idm.json` is the contract.
*Test:* a new output plugin can be built from `idm.json` + disk alone.

## 4 · Virtualize Everything

Counts, not lists. Windows, not documents. Show "Pages (2,000)", render
20; show "fonts in use", not 500 rows. Hard caps + LRU eviction on
everything that scales with document size.
*Test:* memory and latency stay flat as page count grows 27 → 2,000.

## 5 · Never Block the UI

No modal spinners. Long work is asynchronous with visible, honest,
stage-level progress. Failures are specific and actionable.
*Test:* the operator can navigate pages while validation runs.

## 6 · Commands Before Buttons

Every action is a Command first; buttons, menus, shortcuts, the palette,
and plugins are just dispatchers. This is the seam for undo/redo,
keybindings, automation, and AI.
*Test:* every toolbar button's behavior is reachable via Ctrl+K.

## 7 · Progressive Rendering

Nothing waits for everything. Pages render as they're ready, search
indexes in background chunks, validation streams results page-by-page,
summaries load before details.
*Test:* first meaningful paint of a project never waits on full-document
work.

## 8 · Keyboard First

Everything accessible from the keyboard: every panel, every command, every
action, every search, every navigation. Operators live in this tool for
hours; the mouse is optional, never required.
*Test:* the full SAMPLE_PROJECT demo script runs without a mouse (canvas
object-picking excepted).

## 9 · Pixel-Perfect Output

Corollary of Principle 0, stated for output: exported HTML/EPUB reproduces
the source layout to the pixel. Fidelity bugs are release blockers, not
backlog items.
*Test:* Compare overlay at 100% opacity difference shows no drift on the
benchmark corpus.

## 10 · Accessibility by Design

Accessibility is a pipeline stage and a first-class module (Phase 5), not
an export option — and the application's own chrome meets WCAG 2.1 AA.
*Test:* a11y findings ride the same Validation/selection infrastructure as
layout findings.

## 11 · Large Documents First

2,000+ pages is the design assumption, not the stress case. Features are
designed against the large document and verified on the small one — never
the reverse.
*Test:* every new list/panel states its virtualization strategy in review.

## 12 · Extensible by Plugins

New capabilities arrive as commands + panels + events + plugins
(`exporters/`, `validators/`, `ai/`) — never as new app paradigms.
*Test:* a feature spec that can't be expressed as {commands registered,
panel mounted, events consumed/emitted} gets redesigned.

## 13 · Document Accuracy Over Visual Decoration

When UI polish competes with document legibility or rendering truth, the
document wins. The canvas gutter stays neutral, the document is never
themed, no effect ever overlays the page unless the operator asked for it
(Compare emphasis, selection outline).
*Test:* screenshot the canvas — nothing non-document is painted inside the
page bounds except explicit, operator-invoked overlays.

## 14 · Zero Context Switching

One window, one workspace, one selection, one command system. Never open
new browser tabs; never hand the operator to another application; never
require a second tool to finish the job the workspace started.
*Test:* Import → Deliver on the reference title happens in a single
browser tab.

---

## Companion rules (already ratified elsewhere)

- **Workspace Modes** — modes (Proof · Compare · Validate · Edit · A11y ·
  Export) change the available panels; the shell never changes. See
  [../design/04_NAVIGATION.md](../design/04_NAVIGATION.md).
- **Dashboard is the launcher** — after a project opens, the Workspace is
  the product; the Dashboard is where you pick the next title, not part of
  the production loop.
- **AI is a panel, not a chatbot** — AI ships as an assistant panel that
  runs commands (Fix Alignment, Find Missing Fonts, Generate Alt Text,
  Validate Reading Order); results are reviewable, attributable, and
  undoable like any other command.
