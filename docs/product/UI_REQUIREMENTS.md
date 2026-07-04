# UI_REQUIREMENTS — What Kind of Application This Is

## Identity

A **professional desktop application that happens to run in the browser** —
NOT a CRUD dashboard, NOT a marketing SaaS app, NOT a document website.

## Inspiration (in priority order)

1. **Adobe Acrobat** — document viewing, page navigation, proofing tools
2. **Adobe InDesign** — panels, properties, production mindset
3. **Visual Studio Code** — explorer tree, command palette, docks, status bar,
   keyboard-first, extensions
4. **Figma** — canvas + inspector layout, performance feel, in-browser polish

## Hard requirements

- **Dark and Light theme** (light is built; dark is a required deliverable —
  tokens.css must become theme-switchable, not forked)
- **Resizable panels** ✅ (react-resizable-panels, sizes persist via autoSaveId)
- **Dockable windows** ✅ (2A layout; future: drag-to-rearrange docks)
- **Keyboard friendly** — every command reachable without the mouse; command
  palette (Ctrl+K / Ctrl+Shift+P) rides on the existing Command Registry
- **Fast** — performance budgets are contractual, see PERFORMANCE.md
- **Minimal** — chrome earns its pixels; the document is the hero
- **Modern** — crisp, flat, precise; no skeuomorphism, no gradients-as-decor

## Anti-requirements (things we must never ship)

- Full-page spinners that block the workspace
- Modal dialogs for things a panel can do
- Web-style page reloads between production steps
- Mobile-first layouts (desktop-first; 1440×900 is the design target,
  1280×720 the minimum)
- Fabricated data in the UI (e.g., confidence scores that don't exist in the
  IDM — an existing, deliberate decision)
