# ADR-009: Core v1.0 Platform Freeze

**Status:** Accepted · 2026-07-04

## Context

Over Phases 1–2 the codebase matured from a PDF→HTML converter into a
document reconstruction platform with a specified model (LFS 1.0), a
measured engine (Adaptive Reconstruction), a stable contract
(ReconstructionDecision), a workspace, a Quality Gate, a Golden Corpus, and
eight ADRs. Continued architectural churn now risks eroding that maturity.
The right move is to stop changing *how* the platform works and start
expanding *what it understands*.

## Decision

Declare **LayoutForge Core v1.0 — LOCKED**. The following are frozen; they
change only if a serious flaw is discovered, and any such change requires an
ADR:

- LFS 1.0 (the specification)
- Rich Document Model
- Adaptive Reconstruction Engine + `ReconstructionDecision` contract
- Reconstruction diagnostics + document profile / `report.json`
- Viewer · Compare · Validation · Workspace
- Quality Gate · Golden Corpus
- ADR-001 … ADR-008

**Still allowed (encouraged):** work that expands what the engine
*understands* — new Semantic/Document-Intelligence capabilities, new
writers, accessibility, AI — added *through* the frozen contracts and
capability seams, never by refactoring them. New normative LFS sections
(structure/math/a11y) extend the spec; they do not alter the frozen core.

Progress metric, from now on: **how much more the engine understands about a
document** — not how many algorithms or layers are added.

## Consequences

- Downstream consumers (Editor, Writers, Plugins) can build against a stable
  base without chasing refactors.
- The manifest of what's frozen lives in [../CORE_v1.0.md](../CORE_v1.0.md);
  the product framing (one-line definition, pillars, markets) in the product
  docs.
- Phase 3 (Semantic Reconstruction) is the sanctioned direction and is
  expected to take months, not weeks — it is the heart of the product.
- A regression that would require changing a frozen component is a signal to
  reconsider the change, not the freeze.
