# Phase 2A Wireframes — Index

Low-fidelity wireframes for the six approved Phase 2A deliverables.
Produced under the **Design Freeze** (see
[../00_DESIGN_OVERVIEW.md](../00_DESIGN_OVERVIEW.md)): no new
architecture, navigation, or workflow concepts appear here — only the
approved ones, translated into screens.

| # | Wireframe | Doc |
|---|---|---|
| 1 | Workspace — Proof Mode | [01_WORKSPACE_PROOF.md](01_WORKSPACE_PROOF.md) |
| 2 | Workspace — Compare Mode | [02_WORKSPACE_COMPARE.md](02_WORKSPACE_COMPARE.md) |
| 3 | Workspace — Validation Mode | [03_WORKSPACE_VALIDATION.md](03_WORKSPACE_VALIDATION.md) |
| 4 | Workspace — Accessibility Mode (P5 preview) | [04_WORKSPACE_ACCESSIBILITY.md](04_WORKSPACE_ACCESSIBILITY.md) |
| 5 | Dashboard (Launcher) | [05_DASHBOARD.md](05_DASHBOARD.md) |
| 6 | Import Center | [06_IMPORT_CENTER.md](06_IMPORT_CENTER.md) |

## Conventions

- Frame: 1440×900 design target; proportions in the ASCII frames are
  approximate, region relationships are exact.
- Content: the reference title — *children's book, 27 pages, 5 fonts,
  40 images* (SAMPLE_PROJECT.md). Large-document behavior (2,000 pages)
  is specified per screen in a "Scale check" section.
- `‹n›` markers are callouts, annotated below each frame.
- Every wireframe ends with a **Principles check** (against
  PRODUCT_PRINCIPLES.md) and **Open questions** for the review.
- Lo-fi means: layout, hierarchy, states, and interaction — no color, no
  type styling, no polish. Visual design comes after this review.

## Shared shell (identical in all four Workspace modes — drawn once)

```
┌────┬────────────────────────────────────────────────────────────────┐
│    │ QUICK ACTIONS:  [Import] [Compare] [Validate] [A11y] [Export]  │
│ N  │                                   [🔍 Search]  [⌘K Palette]    │
│ a  ├────────────┬──────────────────────────────────┬────────────────┤
│ v  │ EXPLORER   │ MODES: Proof|Compare|Validate|…  │ PROPERTIES/AI  │
│ R  │ (left dock)│        (center surface)          │ (right dock)   │
│ a  │            │                                  │                │
│ i  │            │                                  │                │
│ l  ├────────────┴──────────────────────────────────┴────────────────┤
│    │ BOTTOM DOCK: Job log | Application | Conversion | Performance  │
├────┴────────────────────────────────────────────────────────────────┤
│ STATUS BAR: project · page x/y · zoom · selection · env · job       │
└──────────────────────────────────────────────────────────────────────┘
```

Mode switches change ONLY the center surface + which contextual tools are
available. Page, zoom, and selection always carry across. Docks collapse
with `Ctrl+B` (left) / `Ctrl+J` (bottom); the right dock with `Ctrl+Alt+B`.
