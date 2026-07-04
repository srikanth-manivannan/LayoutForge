# 09 — Benchmark Corpus (Deliverable 10)

A fixed set of real documents, one per pathology, each with a target
accuracy and the rules (08) that gate it. This is the regression suite —
every typography change runs against it, and accuracy per class must not
regress. Extends the "Production-First benchmark corpus" in ARCHITECTURE.md.

## Corpus (each: source PDF + expected metrics, checked in)

| # | Class | Representative | Stresses |
|---|---|---|---|
| 1 | Children's book | Hide-and-Seek (reference) | display fonts, art-over-text, bare-CFF |
| 2 | Dictionary | Zoëga Old Icelandic (660 pp) | 2-column, justified, italics, thumb-index (rotated), large scale |
| 3 | Typography sample | PrinceXML "magic of Prince" | mixed weights, missing OS/2, custom encodings, SVG, floats |
| 4 | Novel / prose | any reflowable trade book | paragraph reconstruction, running heads, hyphenation |
| 5 | Magazine | multi-column feature w/ pull-quotes | columns, spanning figures, captions |
| 6 | Academic journal | 2-column paper w/ refs | columns, footnotes, cross-refs, small caps |
| 7 | Scientific / math | paper with display equations | MathML, sub/superscript, big operators |
| 8 | Mathematics book | textbook w/ matrices, roots | MathML depth, fractions, matrices |
| 9 | Government doc | form/report w/ tables | ruled + borderless tables, spans, headers |
| 10 | Table-heavy | spreadsheet-style PDF | nested tables, merged cells |
| 11 | RTL | Arabic/Hebrew page | RTL order, joining, bidi |
| 12 | CJK | Japanese vertical text | vertical writing, CJK metrics |
| 13 | Multilingual | mixed-script page | per-run direction/font, bidi |
| 14 | Scanned + OCR | image-only w/ text layer | raster-first, OCR text overlay |

(1–3 are in hand from user testing; the rest are acquired as their
milestone approaches.)

## Metrics recorded per document

- **Overlay-vs-raster** mean/max pixel difference per region (the headline
  accuracy number).
- Font-fallback count (target 0).
- Width-fidelity distribution (mean/95th-percentile px error) — the metric
  that moved 56px → 0.09px on the PrinceXML sample.
- Structure recall/precision (tables, lists, math, columns detected vs
  ground truth), where ground truth is hand-annotated once per doc.
- Conversion time + peak memory (11).

## Gating

CI fails if any class regresses beyond tolerance on its headline metric.
"99.99%" is defined operationally as the overlay-vs-raster metric per class,
tracked over time — not a single global claim.
