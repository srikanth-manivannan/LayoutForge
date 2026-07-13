# ADR-011: Parallel Rich-IDM Migration, Renderer Interface, Strict Pipeline

**Status:** Accepted · 2026-07-10

## Context

ADR-001 chose the typographic tree (`Document → Page → Region → Paragraph →
Line → Run → Word → Glyph`) and said it would be built incrementally. In
practice the engine still generates HTML directly from the flat
`Page → TextBlock(line) → TextSpan/WordBox` model, which produces two
concrete defects observed in the field:

- **Span explosion** — the word-pinned renderer emits one absolutely
  positioned `<span>` *per word* (`<span>New</span><span>York</span>…`),
  and the fallback path emits one `<span>` per PyMuPDF span with no
  adjacent-run merge. A `<span>` is being used as a positioning unit, not a
  style boundary.
- **Metrics on the wrong node** — `letter_spacing`/`word_spacing`/
  `line-height` are carried per word/line, when they are properties a
  *paragraph* owns.

The renderer has also drifted into *fixing extraction*: it merges,
positions, and approximates. Every downstream format (XHTML, EPUB, XML,
PML), plus editing, accessibility, search, and reading order, needs the
paragraph/run tree — none of them naturally operate on `TextBlock`.

Two sequencing options were weighed (2026-07-10): ship a Run-Builder /
renderer fix on top of the flat model first, or migrate to the permanent
tree first. Migrating the renderer onto a model we intend to replace means
rewriting it — and later the EPUB/XML/PML writers, editor, and a11y engine —
a second time.

## Decision

**Migrate to the Rich IDM first, as an incremental *parallel* migration —
never a big-bang destructive rewrite.** Four phases, each shippable and
non-breaking:

1. **Introduce the Rich IDM in parallel.** Add `Region/Paragraph/Line/Run/
   Glyph` nodes (Word = existing `WordBox`) alongside the legacy
   `TextBlock` list on `Page`. Nothing generates them yet; nothing breaks.
2. **Generate both models from extraction.** A reconstruction stage builds
   the tree (the Run Builder merges adjacent glyphs into one run whenever
   every style attribute is identical); the legacy `TextBlock` list stays.
   Both are validated for 100% character fidelity.
3. **Move the renderer onto the tree.** `Paragraph → Line → Run → HTML`.
   Span explosion disappears by construction — spans become style
   boundaries, not positioning units. Legacy path kept behind a flag.
4. **Delete the legacy model.** Remove `TextBlock`/`TextSpan`/word-pinned
   rendering once the tree path is at parity on the golden corpus.

**Two structural constraints govern all four phases:**

- **Model ≠ renderer (extends ADR-005).** One Rich IDM feeds a renderer
  interface; HTML/XHTML/EPUB/XML/PML writers only *serialize* the model.
  A writer never decides where a paragraph begins, merges spans, or
  recovers a glyph.
- **Strict staged pipeline (sharpens ADR-006).** `Extraction → Validation →
  Typography Reconstruction → Semantic Reconstruction → Renderer`. Each
  stage hands the next a *fully valid* model with an explicit guarantee:
  Extraction → 100% character fidelity; Typography Reconstruction → correct
  runs, baselines, spacing, fonts; Semantic Reconstruction → paragraphs,
  lists, tables, math, reading order; Renderer → format serialization only.
  **If the renderer would have to fix something, the bug belongs to an
  earlier stage.**

## Consequences

- The permanent model is built once; the renderer and every future writer
  are written against it once. No throwaway Run-Builder-on-flat-model work.
- Phase 1 is purely additive: `Page.regions` defaults empty, `from_dict`
  tolerates its absence, so existing `idm.json` files and the Document
  Manager keep working untouched.
- The tree stays lazy/windowed and Glyph-sparse (ADR-001, ADR-002); it
  never explodes to millions of nodes.
- The renderer stops carrying reconstruction logic, which becomes testable
  in its own stage against the character-fidelity Quality Gate (ADR-010).
- Frozen core (M1–M1.7, ADR-009) is untouched: extraction and the Adaptive
  Reconstruction decisions are consumed, not rewritten.
