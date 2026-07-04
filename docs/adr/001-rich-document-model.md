# ADR-001: Rich Document Model

**Status:** Accepted · 2026-07-04

## Context

The IDM was a flat list of absolutely-positioned lines (`Page → TextBlock →
Span`). This screenshots the layout rather than reconstructing it, which
caps accuracy (intra-line drift) and cannot produce reflowable EPUB,
semantic XML, or accessible output — all stated goals. The remaining
~3–5% error is typography *reconstruction*, and structure (paragraphs,
tables, math, columns) has no representation at all.

## Decision

Evolve the IDM into a typographic **tree**:

```
Document → Page → Region → Block → Paragraph → Line → Run → Word → Glyph
                            (Table/Row/Cell · Math · List · Figure · Note)
```

Leaves carry measured metrics; every node has a stable `id`
(→ `data-object-id`, one selection pipeline) and a reconstruction `mode`
(ADR-002). `TextBlock` is retained as the *Line* node to minimize churn;
richer nodes are added incrementally per milestone. Extraction is frozen —
the tree is built by reconstruction stages that read the raw IDM.

## Consequences

- Unlocks all output formats from one model (ADR-005) and Phase 3 editing,
  validation, and accessibility (structure is what they need).
- Serialization stays backward-compatible (missing keys → defaults); the
  Document Manager's lazy/windowed access is preserved (large-doc rule).
- Glyph nodes exist only where needed (ADR-002), so the tree never explodes
  to millions of nodes.
- Introduced incrementally (M1 added `WordBox`; M2 `Glyph`; M3 `Paragraph`;
  …) — no big-bang rewrite.
