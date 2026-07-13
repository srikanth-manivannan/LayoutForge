# Architecture Decision Records

Short, dated records of the load-bearing architectural decisions behind
LayoutForge — the *reasoning*, not the implementation. As the project grows
toward EPUB/XML/PML and enterprise features, these preserve why the
architecture is the way it is, so decisions can be revisited deliberately
rather than eroded by accident.

Format per ADR: **Context → Decision → Consequences → Status.**

| ADR | Title | Status |
|---|---|---|
| [001](001-rich-document-model.md) | Rich Document Model | Accepted |
| [002](002-adaptive-reconstruction-engine.md) | Adaptive Reconstruction Engine | Accepted |
| [003](003-confidence-gated-structure-detection.md) | Confidence-Gated Structure Detection (tables) | Accepted |
| [004](004-mathml-fallback-strategy.md) | MathML Fallback Strategy | Accepted |
| [005](005-thin-writers-over-shared-model.md) | Thin Writers over a Shared Document Model | Accepted |
| [006](006-pipeline-layering.md) | Reconstruction Pipeline Layering | Accepted |
| [007](007-capability-architecture.md) | Capability Architecture | Accepted (direction; staged to M4) |
| [008](008-semantic-first-ordering.md) | Semantic-First Reconstruction Ordering | Accepted |
| [009](009-core-v1-platform-freeze.md) | Core v1.0 Platform Freeze | Accepted (LOCKED) |
| [010](010-character-fidelity-first.md) | Character Fidelity First | Accepted (primary Quality-Gate criterion) |
| [011](011-parallel-rich-idm-migration.md) | Parallel Rich-IDM Migration, Renderer Interface, Strict Pipeline | Accepted |

Design detail for each lives in [../design/typography/](../design/typography/00_OVERVIEW.md).
