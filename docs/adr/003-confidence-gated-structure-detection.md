# ADR-003: Confidence-Gated Structure Detection

**Status:** Accepted · 2026-07-04

## Context

PDF discards structure — a table is just positioned text and ruling lines;
there is no `<table>`. Reconstructing structure is inference, and inference
is sometimes wrong. Emitting a *wrong* `<table>` (or list, or column split)
destroys an unusual layout and is worse than not detecting it — especially
for the complex production PDFs that are a primary target.

## Decision

Every structure engine (tables first, then lists/columns) follows
detect → **measure confidence** → escalate or fall back:

```
detect structure → confidence ≥ threshold ?
   yes → emit semantic structure (<table>/<ul>/columns)
   no  → keep the accurate positioned objects (current behavior)
```

"No broken tables" (the quality target) means *never emit a structure we
are not confident in* — not "detect every structure." This is ADR-002's
adaptive rule applied above the glyph level.

## Consequences

- Unusual/ambiguous layouts are preserved as accurate positioned objects
  rather than mangled into a wrong structure.
- Confidence + reason are recorded on structure nodes too, so Validation
  can report "3 tables emitted, 1 low-confidence region kept positioned."
- Thresholds are tunable per structure type and measured against the
  benchmark corpus, not guessed.
- Applies to tables (M6), lists/columns (M4/M5); math has its own richer
  ladder (ADR-004).
