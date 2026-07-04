# LayoutForge Studio — Product Design Package

Role: Principal Product Designer output, per the product brief. Design the
**product** first; visual mockups begin **only after this package is
approved**.

> **Status: APPROVED 2026-07-02** (product-level review, with refinements —
> all incorporated). Ratified refinements: **Workspace Modes** (04, 06),
> **Quick Actions bar** (06, 07), **Keyboard First** elevated to product
> principle, **AI is a panel not a chatbot** (06, 07, ../product/FUTURE.md),
> **Zero Context Switching**, **Dashboard is the launcher** (04 Rule 0,
> 06), and the constitution:
> [../product/PRODUCT_PRINCIPLES.md](../product/PRODUCT_PRINCIPLES.md) —
> 15 principles with **Production Accuracy First** as non-negotiable
> Principle 0. Wireframes are now unblocked.

## Reading order

| Doc | Deliverable |
|---|---|
| [01_PERSONAS.md](01_PERSONAS.md) | Who we design for (Priya · Marcus · Elena · David) |
| [02_INFORMATION_ARCHITECTURE.md](02_INFORMATION_ARCHITECTURE.md) | Domain objects, UI mapping, state taxonomy |
| [03_USER_JOURNEY.md](03_USER_JOURNEY.md) | End-to-end journey + the sacred inner loop |
| [04_NAVIGATION.md](04_NAVIGATION.md) | Three-layer nav model, URL state, keyboard map |
| [05_PRODUCT_MAP.md](05_PRODUCT_MAP.md) | Modules × phases × surfaces; product boundaries |
| [06_SCREEN_MAP.md](06_SCREEN_MAP.md) | Blueprint for every screen and panel |
| [07_COMPONENT_HIERARCHY.md](07_COMPONENT_HIERARCHY.md) | Component tree mapped to shipped code |
| [08_UX_PRINCIPLES.md](08_UX_PRINCIPLES.md) | Ten testable principles |
| [09_DESIGN_SYSTEM.md](09_DESIGN_SYSTEM.md) | Tokens, dark theme, primitives, governance |

Inputs: the 14 foundation docs in [../product/](../product/), the shipped
architecture ([../ARCHITECTURE.md](../ARCHITECTURE.md)), and the reference
title ([../product/SAMPLE_PROJECT.md](../product/SAMPLE_PROJECT.md)).

## The five design decisions this package commits to

1. **One Workspace, tabbed quality tools.** Compare/Validation/A11y/Export
   are center tabs sharing page/zoom/selection context — the Proof→Fix→
   Validate loop costs one keystroke per leg. (Locks in the 2A decision.)
2. **Growth by panels/commands/plugins, never by redesign.** Phases 3–7 map
   to new tabs, commands, and tree nodes inside the same shell.
3. **One selection model, one status vocabulary, one icon registry** across
   every surface.
4. **Scale-invisible UI**: counts not lists, virtualized everything,
   budgets as release gates.
5. **Two-tier theming on the existing tokens**: dark theme is a token swap
   (`data-lf-theme`), radius resolves as a 4/6/8px scale, the document
   canvas is never themed.

## Conflicts found in the brief → resolutions proposed

| Brief says | Reality | Resolution |
|---|---|---|
| Radius 8px | shipped `--lf-radius: 6px` | two-tier scale: 4/6/8 (sm/default/lg) — see 09 §3 |
| Dark + light theme | light only shipped | dark as token swap, release-gated parity — 09 §1 |
| 7 phases | ARCHITECTURE.md had 4 (+2.5) | reconciled in ../product/PHASE_ROADMAP.md |
| "Screens: Compare, Validation…" | 2A made them panels in one Workspace | kept as panels (stronger for the inner loop) — 04 §Rules |

## 🔒 DESIGN FREEZE (issued 2026-07-02, in force for Phase 2)

The approved architecture, product principles, navigation model, and
workspace concepts are **frozen for Phase 2**. During wireframing and
high-fidelity design, do **not** introduce new architectural concepts, new
navigation patterns, or major workflow changes — unless a critical
usability issue is discovered, in which case the issue and the proposed
change are documented here first and approved before any design work uses
them. The job now is translating the approved product architecture into a
coherent, production-ready user experience.

Standing trade-off rule: **never compromise document accuracy for UI
polish** (PRODUCT_PRINCIPLES.md, Principle 0). Prettier interface vs. more
reliable proofing → reliable proofing wins, every time.

## Phase 2A design deliverables — status

1. ✅ **Wireframes** ([wireframes/](wireframes/00_WIREFRAME_INDEX.md)) —
   six screens, approved 2026-07-02.
2. ✅ **High-fidelity mockups** ([hifi/](hifi/README.md)) — the same six
   screens as static HTML/CSS built directly on the design-system tokens;
   light + dark themes (token swap, document never themed — verified in
   browser). Open `hifi/index.html`. Awaiting review.
3. ⏭️ Component library (`components/ui/`) → dark-theme tokens PR →
   inner-loop prototype → React implementation.
