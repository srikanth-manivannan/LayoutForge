# 01 — The Rich Document Model (IDM evolution)

Deliverable 1 (part 2). This is the richer hierarchy the user proposed,
specified concretely against the codebase.

## Current vs target

```
CURRENT (flat, positioned lines)        TARGET (typographic tree)
Page                                    Document
 ├── TextBlock  (one PDF line)           └── Page
 │    └── TextSpan (style run)                ├── Region  (column | body | header | footer | margin)
 │    └── WordBox (M1, added)             │    └── Block
 ├── Image                               │         ├── Paragraph
 └── Shape                               │         │    └── Line
                                          │         │         └── Run    (one style)
                                          │         │              └── Word
                                          │         │                   └── Glyph
                                          │         ├── Table → Row → Cell → (Block…)
                                          │         ├── Math  (MathML tree)
                                          │         ├── List  → Item → (Block…)
                                          │         └── Figure (Image | SVG) + Caption
                                          ├── Image · SVG · Shape (page-level)
                                          └── Notes (footnotes/endnotes/refs)
```

Key change: the flat `TextBlock` list becomes a **tree** whose leaves carry
measured metrics. `TextBlock` is retained as the *Line* node (minimal
churn); Paragraph/Region/Run/Word/Glyph and Table/Math/List/Figure are new.

## Node definitions (backend dataclasses, `pipeline/elements/`)

Every node has: stable `id` (→ `data-object-id`, one selection pipeline),
`bbox`, optional `role` (semantic tag), and `to_dict/from_dict`.

- **Document** — metadata, page list, document-level notes, language(s).
- **Page** — geometry, rotation, background raster ref, `regions`,
  page-level figures/shapes, running head/foot refs.
- **Region** — a reading area: `kind ∈ {body, column, header, footer,
  margin, sidebar}`, `column_index`, `reading_order`. Multi-column lives
  here (06).
- **Block** — a paragraph, table, list, figure, or math display. Union
  type; `role` gives the semantic HTML tag (`p, h1..h6, blockquote, li, …`).
- **Paragraph** — `lines`, `alignment`, `first_line_indent`,
  `space_before/after`, `leading`, `baseline_grid_origin`, `style_ref`.
- **Line** — `baseline_y`, `ascent`, `descent`, `leading`, `line_index`,
  `runs`. (Not top/left — see 03.)
- **Run** — one contiguous style: `font_ref`, `size`, `weight`, `style`,
  `stretch`, `color`, `tracking`, `render_mode`, `features` (OpenType),
  `actual_width`, `expected_width`, `words`.
- **Word** — `text`, `x`, `width`, `letter_spacing` (fitted), `glyphs?`.
  (Shipped as `WordBox` in M1.)
- **Glyph** — `gid`, `unicode`, `advance`, `dx/dy` placement, `cluster`.
  Populated only when a word's metric residual exceeds threshold (M1.5
  flags it, M2 fills it), so we never store 100k glyphs we don't need.

Every node carries a **`mode`** (`ReconstructionMode`: WORD/RUN/GLYPH/SVG,
[12_ADAPTIVE_PRECISION.md](12_ADAPTIVE_PRECISION.md)) — a single paragraph
freely mixes WORD and GLYPH words with no special-casing, and each object
records how precisely it was reconstructed.
- **Table / Row / Cell** — `rowspan`, `colspan`, `is_header`, `align`,
  `valign`, `padding`, nested `blocks` (04).
- **Math** — a MathML subtree (05).
- **List / Item** — `list_type ∈ {bullet, decimal, alpha, roman}`,
  `marker`, nesting (06).
- **Figure** — `image|svg` + `caption` + `anchor` (06 images).
- **Note** — footnote/endnote/cross-ref with `marker` and `target` (06).

## Where reconstruction happens (new stages, after extraction)

The pipeline gains a **Reconstruction phase** between `NormalizeIdmStage`
and the output plugins — a set of analyzers that read the raw IDM and build
the tree. Each is independent and skippable (feature-flagged), so partial
support degrades gracefully to the current line rendering:

```
ExtractText/Fonts/Images → NormalizeIdm
   → ReconstructRuns        (M1: line → runs → words; shipped as WordBox)
   → ReconstructParagraphs  (M2: group lines into paragraphs; baseline grid)
   → ReconstructColumns     (M4: region/column detection, reading order)
   → ReconstructLists       (M5)
   → ReconstructTables      (M6)
   → ReconstructMath        (M7)
   → PersistAssets → Generate{Fixed, Semantic} output
```

Backend-agnostic `PipelineEngine` already supports adding stages without
touching existing ones — this is exactly the seam it was built for.

## Serialization & compatibility

- The tree serializes to `idm.json` as nested objects; `from_dict` stays
  backward-compatible (missing new keys → empty defaults), so old projects
  load and the frontend Document Manager reads slices as today.
- **Large-document rule preserved:** the tree is lazy/windowed exactly like
  the flat model — the Document Manager never parses the whole tree into
  React state; Glyph nodes exist only where needed (11).

## Why this unlocks all output formats

- **HTML/XHTML/EPUB** — Paragraph→`<p>`, Run→`<span>`, Table→`<table>`,
  List→`<ul/ol>`, Math→MathML, semantic `role`s → headings/blockquotes.
  Reflowable (EPUB) drops absolute positions; fixed-layout keeps them.
- **XML** — the tree *is* an XML document; the XML writer is a near-direct
  serialization with a published schema.
- **PML** (Palm Markup / project-specific) — a flat writer over the same
  tree (paragraphs, styles, page breaks).
- **Accessibility** — reading order (Region order), semantic roles, and
  the Math/Table structure are exactly what WCAG/EPUB-a11y need (Phase 5).
