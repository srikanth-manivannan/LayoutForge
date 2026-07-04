# Golden Corpus

The permanent set of representative documents every engine release must
pass. This is one of LayoutForge's most valuable long-term assets: it turns
"looks good on my test file" into "provably good across the document classes
we serve." Gated by the [Quality Gate](../docs/design/QUALITY_GATE.md).

## Layout

```
golden-corpus/
  manifest.json          categories, intent, and per-file baselines
  children-books/        full-bleed art, display type over images
  magazines/             image-heavy, multi-column, pull quotes
  novels/                dense prose — paragraph rhythm, reflow
  dictionaries/          dense justified columns, abbreviations, italics
  textbooks/             mixed structure, figures, sidebars, tables
  government/            forms, tables, fixed layout, compliance
  math/                  equations, fractions, matrices, operators
  engineering/           diagrams, tables, units, scientific notation
  multilingual/          mixed scripts, accents, CJK
  rtl/                   Arabic/Hebrew — bidi, right-to-left
  newspapers/            many narrow columns, complex reading order
  comics/                irregular layout, speech bubbles, no body text
```

Each category directory holds source PDFs (not committed to git unless
license-clear; teams drop their own). The harness discovers whatever is
present — an empty corpus is skipped, not a failure — so the structure ships
now and fills over time.

## How it gates releases

The regression harness (`backend/tests/test_golden_corpus.py`) walks every
category, converts each PDF through the frozen pipeline, and asserts the
per-file **baseline** in `manifest.json` still holds:

- reconstruction profile within its recorded band (`glyph_fraction`,
  `mean_reconstruction_confidence`),
- **zero unexpected font fallbacks**,
- performance within budget (no order-of-magnitude regression),
- (as milestones land) structure/validation expectations per category.

Baselines are recorded from `report.json` when a document is first added and
updated deliberately (with justification) when the engine legitimately
improves — that history *is* the release-over-release quality record
(kerning 18% → 11% → 4%).

## Adding a document

1. Drop the PDF into the right category directory.
2. Convert it once; copy the relevant `report.json` figures into
   `manifest.json` as the file's baseline (with a one-line note on what it
   stresses).
3. Commit the manifest entry. The harness now guards it forever.
