# 09 — Design System

Extends the shipped `frontend/src/styles/tokens.css` (`--lf-*` tokens,
Bootstrap-5-compatible via `--bs-*` mapping). Rule zero: **components never
hard-code values — tokens only.** That is what makes dark mode a swap, not
a rewrite.

## 1 · Color

### Neutrals (light theme — shipped values kept)

| Token | Light | Role |
|---|---|---|
| `--lf-bg-canvas` | `#eef0f3` | app background behind panels |
| `--lf-bg-surface` | `#ffffff` | panels, cards, docks |
| `--lf-bg-sunken` | `#f7f8fa` | wells, input fields, page gutter |
| `--lf-border` | `#dde1e6` | default hairlines |
| `--lf-border-strong` | `#c7ccd3` | resize handles, emphasis |
| `--lf-text` | `#1f2328` | primary text |
| `--lf-text-muted` | `#5b6470` | secondary text |

### Dark theme (new — same token names under `[data-lf-theme="dark"]`)

| Token | Dark |
|---|---|
| `--lf-bg-canvas` | `#16181d` |
| `--lf-bg-surface` | `#1f2229` |
| `--lf-bg-sunken` | `#14161a` |
| `--lf-border` | `#31353d` |
| `--lf-border-strong` | `#454a54` |
| `--lf-text` | `#e6e8eb` |
| `--lf-text-muted` | `#9aa2ad` |

The **page canvas gutter stays neutral-dark in both themes** (like Acrobat/
Figma) so document colors read true; the rendered page itself is never
themed — it is the artifact.

### Accent & semantics (both themes; dark gets +1 lightness step where AA fails)

| Token | Value | Role |
|---|---|---|
| `--lf-accent` | `#2f6fed` | primary actions, active tab, selection |
| `--lf-accent-subtle` | `#e8f0fe` / dark `#1c2b4a` | selected rows, hovers |
| `--lf-success` | `#1f8a52` | Ready, Pass |
| `--lf-warning` | `#b8791a` | Warning findings |
| `--lf-danger` | `#d1373f` | Failed, Error |
| ◆ `--lf-selection-outline` | accent @ 2px | canvas object selection |
| ◆ `--lf-compare-diff` | `#c026d3` (magenta) | Compare difference emphasis — must not collide with semantic colors |

Contrast: all text/background pairs meet WCAG 2.1 AA (4.5:1; 3:1 for large
text and UI glyphs). We ship an a11y product — our own chrome passes first.

## 2 · Typography

| Token | Value | Use |
|---|---|---|
| `--lf-font-ui` | system stack (`-apple-system, "Segoe UI", Roboto, …`) | all chrome |
| `--lf-font-mono` | `ui-monospace, "Cascadia Mono", Consolas, monospace` | logs, ids, geometry values |
| `--lf-fs-xs/sm/md/lg/xl` | 11 / 12.25 / 14 / 16 / 20 px | badges/dense · panel text (shipped 0.875rem body) · body · panel titles · screen titles |

Weights 400/500/600 only. Document fonts never leak into chrome; chrome
fonts never leak into the rendered page.

## 3 · Space, radius, elevation

- **Spacing:** 4px base — `--lf-density-xs/sm/md` = 4/8/12px (shipped) +
  `--lf-density-lg/xl` = 16/24px (new). Desktop density: 28px control
  height, 32px panel-header height, 24px tree rows.
- **Radius (resolves the 8px-vs-6px conflict):** two-tier scale —
  `--lf-radius-sm: 4px` (inputs, badges, dense controls), `--lf-radius: 6px`
  (buttons, tabs — shipped value, unchanged), `--lf-radius-lg: 8px` (cards,
  modals, floating panels — satisfies the brand requirement where radius is
  actually visible).
- **Elevation:** flat by default; `--lf-shadow-panel` (shipped) for docks;
  one stronger `--lf-shadow-overlay` for palette/menus/toasts. No other
  shadows — "professional, minimal."

## 4 · Iconography

Lucide only, 16px in dense chrome / 20px in NavRail, `stroke-width: 1.75`,
`currentColor`. Fixed icon-per-concept registry (page, font, image, css,
output, report, validate, compare, export, a11y…) — one concept, one icon,
every surface.

## 5 · Motion

Fast and functional: 120ms ease-out for hovers/tabs; 200ms for dock
collapse; progress animations linear and honest. No entrance animations on
panels; `prefers-reduced-motion` collapses all of it to 0ms.

## 6 · Component standards (`components/ui/` primitives)

Button (primary/secondary/ghost/danger; sm 24px, md 28px) · IconButton
(28px hit area, tooltip mandatory) · Tabs (CenterDock style: 2px accent
underline) · Tree (24px rows, chevrons, count badges) · VirtualTable
(virtualized by default) · Badge (the status taxonomy from IA §states — the
ONLY way status is rendered) · Slider (keyboard-steppable) · Progress
(linear determinate; stage-list variant) · EmptyState (icon + one sentence
+ one action) · Skeleton (never spinners for content areas) · Toast
(bottom-right, non-blocking, action button).

All primitives: visible focus ring (`2px --lf-accent` offset 1px), full
keyboard operability, ARIA roles — measured against WCAG 2.1 AA.

## 7 · Voice & microcopy

Calm, specific, operator-grade. Errors = *what failed + where + one next
step* (PreviewError pattern is the template). Buttons are verbs ("Import
PDF", "Run validation"). Counts are exact ("27/27 pages pass"). No
exclamation marks, no "oops".

## 8 · Governance

`tokens.css` is the single source of truth; PRs adding hex values outside
it are rejected. New components start as primitives or compose them.
Dark-theme parity is a release gate for every new surface.
