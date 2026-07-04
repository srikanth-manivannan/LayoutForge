# Feature Editions (design intent)

Not to be built now — a lens for keeping capabilities modular. Because the
architecture is capability-oriented (ADR-007) and the engine core is frozen
behind a stable contract (ADR-002, LFS 1.0), editions fall out naturally as
**bundles of capabilities toggled on a shared engine** — no forks, no
per-edition code paths.

## The three editions

| | Community | Professional | Enterprise |
|---|---|---|---|
| Convert PDF → HTML | ✅ | ✅ | ✅ |
| Viewer · Compare · Validate | ✅ | ✅ | ✅ |
| Reconstruction diagnostics / report.json | ✅ | ✅ | ✅ |
| Visual editing (Phase 3) | — | ✅ | ✅ |
| Semantic export (EPUB / XHTML) | — | ✅ | ✅ |
| Accessibility (WCAG / EPUB-a11y) | — | ✅ | ✅ |
| Tables / Math capabilities | — | ✅ | ✅ |
| XML / PML export | — | — | ✅ |
| AI assist (alt text, fixes) | — | — | ✅ |
| Batch processing · watch folders · API | — | — | ✅ |
| Teams · roles · audit · SSO | — | — | ✅ |

## Why the architecture already supports this

- **Capabilities** (ADR-007) are the natural licensing unit — an edition is
  a registry configuration, not a build.
- **Thin writers over one model** (ADR-005) means EPUB/XML/PML are additive
  outputs gated per edition, not divergent codebases.
- **The frozen engine** (LFS 1.0) is identical across editions — precision
  and fidelity are never a paid tier; only *capabilities* differ.

## Design guardrail

When adding any capability, keep it independently toggleable and free of
assumptions about which other capabilities are enabled — so any edition
bundle is valid. This is already how ADR-007 requires capabilities to be
built; editions are simply the commercial expression of it. Nothing here
changes current scope — it only keeps future modularity honest.
