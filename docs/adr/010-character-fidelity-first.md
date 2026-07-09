# ADR-010: Character Fidelity First

**Status:** Accepted · 2026-07-09 · (invoked the ADR-009 "serious flaw" clause)

## Context

User testing surfaced invisible characters in rendered output ("much" →
"mu h", "couldn't" → " ouldn't"). Root cause chain: a subset missing both
`post` and `cmap` crashed `_ensure_required_tables` (fontTools "illegal use
of getGlyphOrder()"), the sanitizer swallowed the error and **silently
dropped the font**, the sibling-subset merge then had no outline donor, and
the surviving subset's cmap mapped those characters to **empty glyphs** —
which browsers paint as *nothing* (per-character font fallback triggers only
on a MISSING cmap entry, never on a mapped blank).

Two lessons, one systemic: (1) any single font bug can silently destroy
text; (2) nothing in the pipeline *guaranteed* text visibility. Pixel
accuracy is worthless if a character disappears.

## Decision

1. **Character fidelity = 100% is the PRIMARY Quality-Gate criterion**,
   ahead of visual fidelity. A character may be *substituted* (rendered
   visibly in a fallback font — counted, reported), **never lost** (painted
   as nothing or silently dropped).
2. **Structural guarantee, not a check**: after cmap reconciliation and the
   sibling-subset merge, `_purge_blank_mappings` unmaps every cmap entry
   that still points at an empty non-whitespace glyph. Browsers then fall
   back visibly for exactly those characters. An invisible character is
   impossible by construction.
3. **Fidelity accounting**: the reconstruction profile counts
   `chars_total` / `chars_substituted` / `chars_lost` (≡ 0); `report.json`
   carries a first-class `fidelity` section; the Quality Gate lists
   Character fidelity 100% / Unicode fidelity 100% as gates 0 and 1,
   with font/reading-order/table/math fidelity KPIs beneath.
4. **Truth source clarification** (correcting a plausible misdiagnosis):
   text content was never reconstructed from measurements — Unicode comes
   from the PDF glyph stream (PyMuPDF extraction + texttrace reconciliation)
   and measurements are used *only* for positioning. The gap was glyph
   *paintability* in the served font files; that is what this ADR closes.
   The escalation ladder (WORD→RUN→GLYPH→SVG→IMAGE, ADR-002) remains the
   mechanism for the cases fonts cannot serve at all.

## Consequences

- The exact regression (no-post/no-cmap subset) is fixed (synthesized glyph
  order + seeded cmap) and pinned by test; the purge and the accounting are
  pinned by tests.
- Measured on the reported book: 8,219 chars, **0 lost, 0 substituted**
  (the merge recovered every needed outline); glyph escalation fell to
  0.98% (mean confidence 0.9986) as a side effect of restoring the subset.
- "Typography Fidelity" slots before M3 in the roadmap as demanded — but
  as this hardening milestone (fidelity gate + guarantee), not a rewrite of
  extraction, which is already glyph-stream-sourced and frozen (ADR-009).
- Follow-ups tracked: CFF blank-charstring detection (currently exempt from
  the purge), Validation-panel surfacing of substituted characters, and
  per-page extracted-vs-rendered Unicode diffing in CI when the Golden
  Corpus gains real documents.
