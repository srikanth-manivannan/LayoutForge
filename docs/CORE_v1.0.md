# LayoutForge Core v1.0 — LOCKED

**Status: FROZEN (2026-07-04, [ADR-009](adr/009-core-v1-platform-freeze.md)).**
The platform — not just the code — is frozen. No architectural refactoring
unless a serious flaw is discovered (which requires an ADR). All future work
*expands what the engine understands*; it does not change how it works.

```
LayoutForge Core v1.0
  ✓ LFS 1.0                         docs/spec/LFS-1.0.md
  ✓ Rich Document Model             ADR-001
  ✓ Adaptive Reconstruction Engine  ADR-002
  ✓ ReconstructionDecision          ADR-002 (frozen contract, M1.7)
  ✓ Document Profile / report.json  M1.6 / M1.7
  ✓ Viewer                          Phase 2 (2B)
  ✓ Compare                         Phase 2 (2C)
  ✓ Validation                      Phase 2 (2C)
  ✓ Workspace                       Phase 2 (2A)
  ✓ Quality Gate                    docs/design/QUALITY_GATE.md
  ✓ Golden Corpus                   golden-corpus/
  ✓ ADR-001 … ADR-009               docs/adr/

  STATUS: LOCKED
```

## What the freeze means

| Frozen (change only via ADR on a serious flaw) | Open (the work ahead) |
|---|---|
| The LFS 1.0 core sections | New *reserved* LFS sections (structure/math/a11y) |
| Rich Document Model shape + identity | New node types added incrementally (Paragraph, Table, …) |
| Adaptive Reconstruction Engine + contract | New capabilities that *consume* the contract |
| Pipeline layering (Geometry→Typography→Adaptive→Semantic) | Filling the Semantic layer (Phase 3) |
| Workspace / Viewer / Compare / Validation shells | New panels, writers, AI assist, accessibility |
| Quality Gate targets | New checks per capability |

## Company phase

This closes **Phase 1 (Engine)** and **Phase 2 (Workspace)**. The next work
is **Phase 3 — Semantic Reconstruction**: teaching the engine to understand
document *meaning* (paragraphs → tables → reading order → …). It is the heart
of the product and is scoped in months, not weeks.

## One-line definition

> LayoutForge Studio is a **document reconstruction platform** that
> transforms fixed-layout documents into production-ready structured
> publishing assets while preserving visual fidelity.

Everything built from here supports that sentence. Product framing —
pillars, markets, editions — lives in
[product/PRODUCT_PILLARS.md](product/PRODUCT_PILLARS.md),
[product/PRODUCT_VISION.md](product/PRODUCT_VISION.md), and
[product/EDITIONS.md](product/EDITIONS.md).
