# High-Fidelity Mockups — Phase 2A Design Deliverables

Static HTML/CSS mockups of the six approved screens, built directly on the
design system ([../09_DESIGN_SYSTEM.md](../09_DESIGN_SYSTEM.md)). Open
[index.html](index.html) in any browser — no build step, no server.

| File | Screen |
|---|---|
| `workspace-proof.html` | Workspace · Proof Mode (flagship) |
| `workspace-compare.html` | Workspace · Compare Mode (overlay state, drift visible) |
| `workspace-validation.html` | Workspace · Validation Mode (2-warnings state) |
| `workspace-accessibility.html` | Workspace · Accessibility Mode (Phase 5 preview) |
| `dashboard.html` | Dashboard (launcher) |
| `import-center.html` | Import Center (converting + failure states) |

## How these were built (and why it matters for implementation)

- **`lf-mockup.css` implements the design system verbatim** — the `--lf-*`
  tokens (light values identical to the shipped
  `frontend/src/styles/tokens.css`, plus the new dark set, radius scale,
  type scale, and control metrics). It is the reference for the real
  tokens PR and the `components/ui/` primitives.
- **Dark theme is a token swap** (`data-lf-theme="dark"` on `<html>`) —
  zero component-level overrides, proving the theming rule. Toggle lives
  bottom-right on every mockup (persisted in localStorage).
- **The document page is never themed.** The children's book page keeps
  its own colors in both themes; the canvas gutter is neutral-dark in both
  (Acrobat/Figma convention). Principle 0/13 made visible.
- **Content is the reference title** (*Sunny Day for Max*, 27 pages,
  5 fonts) plus the 890-page textbook for scale states.
- Icons are monochrome glyph placeholders; **production uses Lucide** per
  the design system (`stroke-width 1.75`, 16/20 px).
- The floating "All mockups / Theme" bar bottom-right is mockup chrome,
  not product UI.

## Approved-recommendation decisions baked in

Thumbnail rail on the left · editable page field in the mode toolbar ·
bottom dock present but shallow · difference emphasis off by default ·
AI drafts clearly labeled as reviewable suggestions · Failed state shows
stage-specific actionable errors.

## Not covered here (deliberately)

Projects list, Settings, command palette overlay, toasts, and the Split
state of Compare — they compose entirely from primitives shown on these
six screens and will be specified during component-library build-out.
