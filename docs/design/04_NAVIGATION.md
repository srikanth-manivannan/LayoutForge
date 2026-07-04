# 04 — Navigation Model

## Three navigation layers

```
Layer 1  GLOBAL     NavRail (left, 64px, icon+label)
                    Dashboard · Projects · Import · Settings
                    ────────────────────────────────
                    contextual group (visible when a project is open):
                    Viewer · Compare · Validation · Logs
                    [Phase 5 adds A11y · Phase 4 adds Export · Phase 7 adds Admin]

Layer 2  WORKSPACE  Workspace MODES (CenterDock; ?panel= in URL is source of truth)
                    Proof(Viewer) | Compare | Validate | [Edit P3] | [A11y P5] | [Export P4]
                    + always-on docks: Explorer (L) · Properties/AI (R) · Logs/Monitor (B)

Layer 3  DOCUMENT   Inside the Viewer:
                    page nav (‹ › / PgUp PgDn / go-to-page) · thumbnails rail ·
                    zoom / fit / view-mode · incremental search (Ctrl+F) ·
                    [future] minimap
```

## Workspace Modes (product principle)

The workspace has **modes**, not pages: `Proof · Compare · Validate ·
[Edit] · [Accessibility] · [Export]`. Switching mode changes the center
surface and which contextual panels/commands are available — **the shell
never changes** (exactly like VS Code's Explorer/Search/Git/Extensions
activity switch). Mechanically, a mode = a CenterDock tab + its panel set +
its command group; `?panel=` carries it in the URL today (may be renamed
`?mode=` when 2C lands — one mechanism either way). Every mode inherits
page, zoom, and selection from the previous mode — that is what makes the
inner loop free.

## Rules

0. **Dashboard is the launcher.** `Start → Dashboard → open project →
   Workspace`, and from then on the Workspace *is* the product (like
   Figma/VS Code/IntelliJ). You return to the Dashboard only to switch
   titles or check the floor's status — nothing in the production loop ever
   routes through it. It stays one NavRail click away, never auto-shown.
1. **One workspace per project.** `/workspace/:projectId` hosts everything
   about a title. Compare/Validation/etc. are tabs, never routes of their
   own. (2A decision — locked.)
2. **URL = restorable state.** Route + `?panel=` (+ future `&page=&zoom=`)
   reconstructs the working context. Refresh never loses your place.
3. **NavRail contextual group == center tabs.** Clicking "Compare" in the
   rail focuses the Compare tab of the open workspace — same target, two
   affordances (rail for mouse-first users, Ctrl+1..9 for keyboard).
4. **Back means back.** Browser back returns Dashboard ↔ Workspace without
   remounting the ViewerEngine (singleton survives navigation — verified).

## Keyboard map (reserved now, shipped incrementally)

| Keys | Action |
|---|---|
| `Ctrl+K` | Command palette (rides Command Registry) |
| `Ctrl+1..5` | Center tabs: Viewer/Compare/Validation/A11y/Export |
| `PgUp / PgDn`, `Home / End` | Page navigation |
| `Ctrl+= / Ctrl+- / Ctrl+0` | Zoom in / out / fit-width |
| `Ctrl+F` | Document search |
| `Ctrl+B` / `Ctrl+J` | Toggle Explorer / bottom dock |
| `F8` | Next validation finding |
| `Ctrl+Z / Ctrl+Shift+Z` | Undo / redo (Phase 3) |

All shortcuts are declared as `keybinding` on commands — never wired ad hoc
to components — so the palette, menus, and docs stay in sync automatically.

## The ≤3-click audit (worst cases)

| Task | Clicks |
|---|---|
| Fresh PDF → conversion running | 2 (Import → drop) |
| Dashboard → proofing page 12 of a book | 3 (project card → Compare tab → page) |
| Validation finding → object properties | 1 (click the finding) |
| Anywhere → any command | 2 (Ctrl+K → Enter) |
