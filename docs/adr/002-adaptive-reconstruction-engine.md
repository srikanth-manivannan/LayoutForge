# ADR-002: Adaptive Reconstruction Engine

**Status:** Accepted · 2026-07-04

## Context

Word-level positioning (M1) fixed line-wide drift, but strongly-kerned
words (`HTML`, `Ti…`) still have sub-word residual. The obvious next step —
reconstruct every word from its glyphs — would turn a 3,000-page book into
millions of glyph objects, wrecking memory, selection, undo, hit-testing,
painting, and validation. Precision and scalability appear to conflict.

## Decision

Reconstruct each object at the **cheapest level that reproduces it within
tolerance**, escalating only where measurement proves it necessary:

```
WORD → RUN → GLYPH → SVG → IMAGE      (the precision ladder)
```

Every object records: `mode` (the level), `reason` (WHY it escalated —
kerning / ligature / width / RTL / …), and an internal
`reconstruction_confidence` (0–1 engineering metric for decisions and
diagnostics, **never a user-facing score**; named specifically to leave room
for future ocr/table/reading-order confidences). A single paragraph freely
mixes levels. Escalation is a pure measurement (`expected` from font metrics
vs `actual` PDF box), emitted as an immutable **`ReconstructionDecision`**
(frozen M1.7) that later stages CONSUME — glyph/precision reconstruction (M2)
never recomputes it.

The engine and its analytics (document profile: counts by mode/reason,
mean confidence) live in `pipeline/typography/adaptive_reconstruction.py`.

## Consequences

- **Measured, not assumed:** on the Zoëga dictionary, 85% of 341,029 words
  stay WORD, 15% escalate — auto-flagging exactly the kerning-heavy words
  with no hardcoded list. The expensive path runs on ~15%, not 100%.
- The name is deliberately broad ("Reconstruction", not "Precision") so it
  can grow to RUN/SVG/IMAGE decisions without renaming.
- The same detect→measure→escalate/fallback rule governs tables (ADR-003)
  and math (ADR-004) — a project-wide principle: never force a structure
  below confidence.
- `reason`/`confidence` make Validation and analytics explainable
  ("51k glyph words: 41k kerning, 6k ligatures").
