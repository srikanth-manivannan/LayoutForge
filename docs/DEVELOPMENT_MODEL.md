# LayoutForge Development Model

**Status:** Active · 2026-07-11 · supersedes architecture-first development

## The rule

> **LayoutForge Core v1 is frozen.** From this point on, no new architectural
> abstraction, pipeline stage, or model change is introduced unless a real
> document in the Reality Validation Framework proves it necessary. Every
> change must originate from corpus evidence, be traced to the earliest
> responsible stage, include a regression test, and improve measurable
> quality. **Architecture is no longer the driver; evidence is.**

Core v1 is complete: Rich IDM · Adaptive Reconstruction · Lexical
Reconstruction · Validator · Quality Accounting · RVF · Golden Corpus · LFS ·
ADRs · stable pipeline. 🔒

## The workflow

```
Corpus → RVF → Issue → Root Cause → Earliest-Stage Fix → Regression Test → Corpus again
```

Not `idea → architecture → implementation`. Every commit answers: *which real
document proved this was needed, and which is the earliest stage responsible?*

## Stage ownership

Each stage owns specific guarantees. **A later stage may never repair an
earlier stage** — if it would have to, the bug belongs to the owning stage.

| Stage | Owns |
|---|---|
| Extraction | Unicode fidelity (every character, from the glyph stream) |
| Font Resolution | Font identity (visual, not PDF-object) |
| Run Builder | Style continuity (visual-identity runs) |
| Word Builder | Lexical integrity (words from runs, fragments, no crossing) |
| Line Builder | Baseline geometry |
| Paragraph Builder | Paragraph semantics |
| Region Builder | Page semantics (reading areas, order) |
| Validator | Model correctness |
| Writer | Serialization only |

Examples: if the Writer sees bad words → fix the **Word Builder**. If the
Paragraph Builder sees missing Unicode → fix **Extraction**.

## Severity matrix

RVF classifies every issue automatically (`tools/rvf/issues.py`).

| Severity | Description | Fix before release |
|---|---|---|
| **P0** | Character loss, Unicode corruption, crash | Mandatory (release-blocking) |
| **P1** | Wrong font, wrong reading order, broken table, model-integrity error | Mandatory (release-blocking) |
| **P2** | Baseline drift, spacing error, image scaling | Before next minor |
| **P3** | Minor visual differences | Backlog |
| **P4** | Cosmetic / UI | When convenient |

P0 and P1 are **release-blocking**. This prevents polishing P3 tweaks while a
P0 Unicode issue is open.

## Issue lifecycle

Every RVF issue carries: `id`, `category`, `stage`, `severity`,
`release_blocking`, `page`, `message`, and lifecycle metadata `status`
(Open→Closed), `detected_by`, `regression_test`, `fixed_in`, `verified_by`.
Issue ids are deterministic (stable across runs) so an issue can be tracked
from detection to closure.

## Core v1 Certification

Before Phase 3 (Document Intelligence), the engine must **certify** against a
diverse corpus (`tools/rvf/certification.py`): 0 P0, 0 P1, 0 pipeline
failures, quality scorecard pass on every document, and legacy↔semantic
parity. Once green across categories (Publishing / Government / Academic /
Business / Engineering / Accessibility / International + performance + memory),
tag **LayoutForge Core v1.0 Certified** — the permanent baseline.

## Playwright (dev/CI only)

Introduced as a **development and CI dependency, never a runtime one**, to
measure DOM text, selection text, font loading, and pixel/layout regressions.
It becomes another validation layer on top of the static gates — not the first
line of defense.

## Asset Manager — data-driven, deferred

The 400k-px working-copy threshold (LFS §7a) is **chosen from corpus data**
(average/largest image, render time, memory), not guessed. Deferred until the
corpus answers.

## Product direction

The discipline above naturally splits the project into two products:

- **LayoutForge Core** — the certified reconstruction engine (reusable in
  services, APIs, future products).
- **LayoutForge Studio** — the app on top (proofing, editing, accessibility,
  export, AI, publishing workflows), evolving independently of the engine.
