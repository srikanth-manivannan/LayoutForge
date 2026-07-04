# Typography Reconstruction Engine — Architecture (v2)

Status: **design — approval-gated.** Milestone 1 (word-level positioning)
is implemented and verified; Milestones 2+ are designed here and await
sign-off before implementation, per this project's design-first discipline
([../00_DESIGN_OVERVIEW.md](../00_DESIGN_OVERVIEW.md) freeze rules).

## The thesis

LayoutForge's remaining ~3–5% error is **typography reconstruction**, not
extraction. The extraction pipeline (PyMuPDF → IDM) is correct and is not
redesigned. The work begins at the IDM.

The root cause of the residual error is **altitude**: we positioned every
*line* independently and fitted its width with one line-level spacing
value. When a line's true width difference lives *inside* words (kerning,
per-glyph advances), a single line-level correction smears across the line
and the overlay drifts against the raster — visible as ghosting/doubling
(confirmed on the reference "1910" credits page: single-font lines carrying
−0.9 to −1.4px word-spacing as a failing crutch).

The fix is to reconstruct the document's **typographic hierarchy** and
position at the right altitude for each layer:

```
Paragraph  → absolute container, browser layout inside where safe
   Line     → baseline + leading (baseline grid), not top/left
     Run    → one style; measured, not estimated
       Word → pinned to its own x (kerning stays inside the box)
         Glyph → per-glyph advance for the last mile
```

## The twelve deliverables (index)

| # | Deliverable | Doc |
|---|---|---|
| 1 | Typography Reconstruction Architecture | this file + [01_IDM_MODEL.md](01_IDM_MODEL.md) |
| 2 | Baseline Reconstruction Engine | [03_BASELINE_AND_PARAGRAPH.md](03_BASELINE_AND_PARAGRAPH.md) |
| 3 | Paragraph Reconstruction Algorithm | [03_BASELINE_AND_PARAGRAPH.md](03_BASELINE_AND_PARAGRAPH.md) |
| 4 | Font Metrics Engine | [02_FONT_METRICS_ENGINE.md](02_FONT_METRICS_ENGINE.md) |
| 5 | Table Reconstruction Engine | [04_TABLE_ENGINE.md](04_TABLE_ENGINE.md) |
| 6 | MathML Reconstruction Engine | [05_MATH_ENGINE.md](05_MATH_ENGINE.md) |
| 7 | Multi-column Layout Engine | [06_STRUCTURE_ENGINES.md](06_STRUCTURE_ENGINES.md) |
| 8 | HTML/CSS generation strategy | [07_HTML_CSS_GENERATION.md](07_HTML_CSS_GENERATION.md) |
| 9 | Validation rules | [08_VALIDATION_RULES.md](08_VALIDATION_RULES.md) |
| 10 | Benchmark corpus | [09_BENCHMARK_CORPUS.md](09_BENCHMARK_CORPUS.md) |
| 11 | Implementation roadmap + milestones | [10_ROADMAP.md](10_ROADMAP.md) |
| 12 | Performance for very large documents | [11_PERFORMANCE.md](11_PERFORMANCE.md) |
| ★ | **Adaptive Precision Engine (M1.5)** — the scalability spine | [12_ADAPTIVE_PRECISION.md](12_ADAPTIVE_PRECISION.md) |

## Principles (extend PRODUCT_PRINCIPLES.md for typography)

1. **Reconstruct structure, don't screenshot lines.** The IDM carries a
   real typographic tree, not a flat list of positioned lines.
2. **Measure, never estimate.** Every run knows its `actualWidth`,
   `expectedWidth` (from font metrics), `baseline`, and `advanceWidth`.
   Spacing is *derived* from metrics, never hardcoded.
3. **Position at the lowest safe altitude — adaptive precision.**
   Paragraph container is absolute; inside, let the browser lay out unless
   measurement proves a glyph needs pinning. Pin words always; escalate a
   word to glyph-level **only when its measured error exceeds tolerance**.
   Never convert every word to glyphs — a 3,000-page book would become
   millions of glyph objects. This is the non-negotiable scalability
   decision (M1.5); see [12_ADAPTIVE_PRECISION.md](12_ADAPTIVE_PRECISION.md).
   The same detect→measure→escalate/fallback rule governs tables, math,
   and figures (never force a structure below confidence).
4. **The raster is ground truth for proofing; the tree is ground truth
   for output.** Fixed-layout proofing overlays the tree on the raster
   (pixel accuracy); reflowable output (EPUB) emits the tree as semantic
   HTML. Same IDM, two renderers.
5. **Format-independent core.** The typography engine produces a
   *presentation-neutral* reconstructed document; format writers
   (HTML/XHTML/EPUB/XML/PML) are thin serializers over it.
6. **Every layer is inspectable and editable.** The tree is the substrate
   for Phase 3 visual editing, validation, and accessibility.

## Format independence (the shape)

```
            ┌─────────────── Extraction (unchanged) ───────────────┐
  PDF ──────▶ PyMuPDF ──▶ raw IDM (Page·TextBlock·Image·Shape)
            └──────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │  TYPOGRAPHY RECONSTRUCTION    │   (new; begins at IDM)
                    │  raw IDM → Rich Document Model │
                    │  runs·words·glyphs·paragraphs  │
                    │  ·columns·tables·math·lists    │
                    └──────────────┬───────────────┘
                                   │  Rich Document Model (format-neutral)
        ┌──────────┬──────────┬────┴─────┬──────────┬──────────┐
     HTML       XHTML       EPUB        XML        PML     (fixed-layout
   writer      writer      writer      writer     writer    proofing view)
```

Future INPUTS (EPUB/XHTML/XML/HTML/PML) become alternate *front-ends* that
populate the same Rich Document Model, so the typography engine and all
output writers are reused unchanged.

## What is already true in the codebase (do not rebuild)

- Extraction stages, background raster (ground-truth composite), font
  pipeline (sanitization, bare-CFF wrapping, sibling-subset completion,
  cmap reconciliation, base-14 metrics, required-table synthesis).
- Font metrics access via fontTools + MuPDF (the Font Metrics Engine
  formalizes what several fixes already use ad hoc).
- The viewer's windowed rendering, selection pipeline, Compare/Validation.
- **Milestone 1 word-pinning** — the run/word layer, retrofitted into the
  current renderer as `WordBox` (see 01 + 10).
