# DESIGN_SYSTEM — Foundation Constraints

These are the *input constraints* for the design system. The full token
spec and component rules live in
[../design/09_DESIGN_SYSTEM.md](../design/09_DESIGN_SYSTEM.md).

## Constraints

- **Primary color:** Blue (shipped accent: `#2f6fed`, `--lf-accent`)
- **Neutrals:** Gray scale (cool grays, shipped in `tokens.css`)
- **Radius:** 8px for surfaces/cards; smaller (4–6px) for dense controls.
  ⚠️ Shipped `--lf-radius` is 6px — the design system resolves this as a
  two-tier radius scale rather than a single value (see full spec).
- **Tone:** Professional. No excessive gradients, no decorative noise.
- **Framework compatibility:** Bootstrap 5, CSS-only (no Bootstrap JS) —
  `--bs-*` variables are mapped to `--lf-*` tokens, already in place.
- **Icons:** Lucide (single icon family everywhere).
- **Platform:** Desktop-first. 1440×900 design target, 1280×720 minimum.
- **Themes:** Light (shipped) + Dark (required). All colors flow through
  `--lf-*` tokens so dark mode is a token swap, never a component fork.

## Source of truth

`frontend/src/styles/tokens.css` is the single place color/spacing/radius
values live. Components never hard-code hex values.
