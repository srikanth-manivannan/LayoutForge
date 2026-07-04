# ADR-008: Semantic-First Reconstruction Ordering

**Status:** Accepted · 2026-07-04

## Context

With the engine core frozen (M1–M1.7), two directions remain:

- **Precision reconstruction (M2)** — per-glyph placement to push visual
  fidelity from ~99.9% toward 99.99%.
- **Semantic reconstruction (M3+)** — paragraphs, columns, lists, tables,
  math, reading order.

The default assumption was M2 next (it only needs the frozen decisions).
But the product goal is a **multi-format publishing platform**
(PDF → HTML/XHTML/EPUB/XML/PML + accessibility + editing), and the
`report.json` telemetry shows the M2 residual is small: ~15% of words
GLYPH-flagged on a dense dictionary, mostly cosmetic (`HTML`, `Ti…`), and
the Adaptive Reconstruction Engine already captured ~85–90% of the visual
gain.

## Decision

**Do semantic reconstruction before precision reconstruction.** Execution
order becomes:

```
M3 paragraph → M4 columns/reading-order → M5 lists/notes → M6 tables →
M7 math → M8 semantic writers (EPUB/XHTML/XML/PML) → M2 precision → M9 i18n
```

Milestone IDs are unchanged (ADRs/CHANGELOG reference them); only the order
changes. M2 is *scheduled* later by priority, not blocked — it can be pulled
forward if a customer needs pixel-perfect proofing before reflowable output.

Rationale by impact:

| Work | User value | Cost | When |
|---|---|---|---|
| Paragraph / lists / reading order | ⭐⭐⭐⭐⭐ | low–med | now (M3–M5) |
| Tables | ⭐⭐⭐⭐⭐ | high | M6 |
| Math | ⭐⭐⭐⭐ | high | M7 |
| Precision (glyph) | ⭐⭐⭐ | very high | after M8 |

## Consequences

- Semantic structure unlocks EPUB/XHTML/XML/PML, accessibility, editing,
  search, and reading order **together** — the platform's long-term value.
- A small, bounded visual residual persists until M2; acceptable because
  `report.json` quantifies it and the Quality Gate tracks it.
- The Rich Document Model (ADR-001) grows structure nodes (Paragraph →
  Region → Table → Math) before the Glyph leaf — matching the new order.
- Guiding principle for all future work: *expand what the engine
  understands, rather than change how it works.*
