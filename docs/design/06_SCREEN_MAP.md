# 06 — Screen Map

Layout blueprints for every screen. (Text blueprints — visual mockups begin
only after this package is approved.)

## Shell (constant across all screens)

```
┌──┬──────────────────────────────────────────────────────┐
│N │  Screen content (router outlet)                      │
│a │                                                      │
│v │                                                      │
│R │                                                      │
│a │                                                      │
│i │                                                      │
│l │                                                      │
├──┴──────────────────────────────────────────────────────┤
│ Status bar: env health · job state · page/zoom (in ws)  │
└──────────────────────────────────────────────────────────┘
```

## 1 · Dashboard `/`

```
┌────────────────────────────────────────────────┐
│ Greeting + [Import PDF] primary action         │
│ (whole screen is also a drop target)           │
├───────────────────────────┬────────────────────┤
│ Active conversion         │ Production summary │
│ stage · progress · ETA    │ ready / failed /   │
│ (links → Monitor/Logs)    │ delivered counts   │
├───────────────────────────┴────────────────────┤
│ Recent projects — cards: thumbnail(P2B) · name │
│ · pages · status badge · [Open]                │
└────────────────────────────────────────────────┘
```
Answers in 5 seconds: *what's in flight, what's ready, what failed.*
**The Dashboard is a launcher, not a home base** — once a project opens,
the operator lives in the Workspace and only returns here to pick the next
title (Figma/VS Code pattern).

## 2 · Projects `/projects`

Toolbar (search · sort · [Import]) over a virtualized table: name · pages ·
status · updated · actions (Open / Export / Delete-with-confirm). Row
click = open workspace. Empty state teaches the drop-to-import gesture.

## 3 · Import `/conversion`

Large drop zone + file picker · upload stream progress · then live pipeline
stages (the same component the Conversion Monitor dock uses):
`Validate ▸ Metadata ▸ Backgrounds ▸ Fonts ▸ Images ▸ Text ▸ Normalize ▸
Assets ▸ CSS ▸ HTML`, each with state + duration. Failure shows the
specific stage + actionable error. Success shows **[Open workspace]**.

## 4 · Workspace `/workspace/:projectId` — THE screen

```
┌──┬─────────────────────────────────────────────────────┐
│N │ QUICK ACTIONS  Import·Compare·Validate·A11y·Export  │
│a │                              🔍 Search   ⌘K Palette │
├──┼──────────┬─────────────────────────────┬───────────┤
│v │ EXPLORER │ MODE: [Proof][Compare][Val…]│ PROPERTIES│
│R │          │ ┌─────────────────────────┐ │  / AI     │
│a │ Source   │ │ mode toolbar            │ │ Geometry  │
│i │ Pages 27 │ ├─────────────────────────┤ │ Typography│
│l │ Fonts 5  │ │                         │ │ Appearance│
│  │ Images 40│ │      PAGE CANVAS        │ │ Metadata  │
│  │ CSS      │ │   (thumbnails rail 2B)  │ │ Advanced  │
│  │ Output   │ │                         │ │           │
│  │ Reports  │ └─────────────────────────┘ │           │
├──┴──────────┴─────────────────────────────┴───────────┤
│ BOTTOM DOCK  [Job log][Application][Conversion][Perf] │
├────────────────────────────────────────────────────────┤
│ status: Book Title · page 12/27 · 150% · 1 selected    │
└────────────────────────────────────────────────────────┘
```
All splits resizable + persisted (✅). `Ctrl+B`/`Ctrl+J` collapse docks →
max canvas.

### Quick Actions bar (top toolbar — the complete list)

`Import · Compare · Validate · Accessibility · Export · Search · Command
Palette` — and nothing else. Each is a command dispatch (mode switch or
action); **everything else belongs in panels.** The bar is identical in
every mode; per-mode tools live in the mode toolbar inside the center
surface.

### Workspace Modes (center surface)

Modes change the center surface + available panels; the shell never
changes, and page/zoom/selection carry across every switch.

- **Proof (Viewer)** — canvas + page nav + zoom/fit/view-mode + search (2B).
- **Compare** — same canvas + mode switch (Overlay ⟷ Split) + opacity
  slider + difference emphasis. Inherits page/zoom from Viewer, always.
- **Validation** — findings table (severity · page · object · message) +
  [Run]/[Re-run changed] + progress; row click → jump + select.
- **Edit (P3)** — same canvas + edit handles, edit toolbar, undo/redo.
- **A11y (P5)** — reading-order list + canvas overlay + alt-text editor.
- **Export (P4)** — format cards (HTML ✅ · EPUB-FXL · EPUB-reflow) →
  options → async package build → download/history.
- **AI Assistant (P6)** — a right-dock panel (never a chatbot, never a
  screen): command launcher + reviewable results list. Commands: Fix
  Alignment · Find Missing Fonts · Generate Alt Text · Validate Reading
  Order — each dispatches through the Command Registry, so results are
  attributable and undoable.

## 5 · Settings `/settings`

Categories (left list · right form): General · Appearance (theme
light/dark) · Keyboard (rebindable commands) · Pipeline defaults · About
(version, licenses).

## Modals/overlays (the complete list — nothing else may be modal)

Delete confirmations · command palette · go-to-page · keyboard-shortcut
overlay (`?`). Long-running work is NEVER modal.
