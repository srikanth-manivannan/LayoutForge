# ADR-007: Capability Architecture

**Status:** Accepted (direction) · **Not yet implemented** · 2026-07-04

## Context

Reconstruction concerns are multiplying — typography, tables, math, SVG,
and later OCR, accessibility, AI. If each is wired ad-hoc into the pipeline,
the engine becomes a tangle, and enterprise customers can't enable only what
they need. The system needs a modular seam before that logic accumulates.

## Decision

Organize reconstruction as **Capabilities** behind a registry. Each
capability is a self-contained module owning its slice across the pipeline:

```
Capability Registry
 ├─ Typography      (SHIPPED as pipeline/typography — the reference capability)
 ├─ Tables
 ├─ Math
 ├─ SVG / Vector
 ├─ OCR
 ├─ Accessibility
 └─ AI

Each capability owns: detection · normalization · reconstruction ·
                      validation · rendering contribution · export
Each is: independent · confidence-gated (ADR-003) · toggleable.
```

The Semantic Analyzer phase (ADR-006) becomes "run the enabled capabilities
in dependency order." Writers (ADR-005) stay format-neutral; capabilities
contribute nodes to the Rich Document Model, not format-specific output.

## Consequences

- **Modularity**: adding Math or OCR is a new capability, not surgery on the
  pipeline. Enterprise builds enable a subset.
- **Nears a plugin system**: a stable Capability interface + registry is one
  step from third-party/enterprise plugins.
- **Staging (deliberate):** implementing the registry now would be premature
  — only Typography exists, so a registry would wrap a single member. The
  Capability interface is **extracted when the second capability (Tables,
  M4) needs it**; `pipeline/typography/` is already shaped as the reference
  capability (self-contained detection/measurement/decision/render seams).
  This ADR fixes the direction so later capabilities are built to fit it.
- Aligns with the frozen `ReconstructionDecision` contract (ADR-002): each
  capability emits decisions in a shared vocabulary (`mode`, `reason`,
  `*_confidence`) — hence the specific `reconstruction_confidence` name,
  leaving room for `ocr_confidence`, `table_confidence`, etc.
