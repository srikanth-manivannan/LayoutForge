# SAMPLE_PROJECT — The Reference Title

Design around this real project, not an imagined one. It is the actual PDF
used for Phase 1/2A verification.

| Attribute | Value |
|---|---|
| Project | Children's picture book |
| Pages | 27 |
| Fonts | 5 embedded (subset, required fontTools sanitization) |
| Images | 13 embedded + 27 page-background rasters |
| Layout | Fixed layout, full-bleed art, display type over images |
| Output today | Per-page HTML + shared/per-page CSS + manifest |
| Output future | Fixed-layout EPUB |

## What this title exercises

- Text positioned over images (proofing overlay is essential)
- Display fonts where fallback substitution is instantly visible
- Page backgrounds that already contain the rasterized text (the known,
  deliberate duplication — see README "Layout Accuracy phase")
- Small enough to proof fully; real enough to break naive font handling

## What this title does NOT exercise (design for these anyway)

- Scale: a 500–2,000 page textbook (windowing, thumbnail virtualization)
- Multi-column body text, tables, footnotes (scientific/education PDFs)
- RTL / CJK scripts
- Reflowable output

The benchmark corpus in ARCHITECTURE.md ("Production-First benchmark
corpus") is the long-term test set; this children's book is the daily
design reference.

## Walkthrough (the demo script every screen must support)

1. Dashboard shows the book as a recent project, status Ready.
2. Open → Workspace: Explorer shows Source / 27 Pages / 5 Fonts / 40 Images
   / CSS / Output / Reports as summarized counts.
3. Viewer renders page 1 pixel-accurately; Next/Prev < 50ms; zoom 150%.
4. Compare tab: overlay source raster vs. reconstruction, drag opacity.
5. Validation tab: all pages pass except two with missing-glyph warnings.
6. Properties: click a headline → Geometry/Typography groups populate.
7. Export: HTML package downloads; EPUB listed as Phase 4, disabled.
