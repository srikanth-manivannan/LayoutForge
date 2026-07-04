# 04 — Table Reconstruction Engine (Deliverable 5)

Goal: recover semantic `<table><thead><tbody><tr><td>` from positioned
text + ruling lines, not a grid of absolutely-placed cells.

## Inputs

- Text runs/words with x-extents (from M1).
- **Ruling lines** — PyMuPDF `page.get_drawings()` gives vector strokes;
  horizontal/vertical segments are candidate cell borders. Fills →
  cell/zebra backgrounds.
- Whitespace columns — for borderless tables, gaps in the x-histogram of a
  region's words are column boundaries.

## Detection

1. **Ruled tables:** cluster h-lines (row separators) and v-lines (column
   separators); their intersections define the cell grid. A cell = the
   text whose bbox falls in a grid rectangle.
2. **Borderless tables:** build an x-projection histogram of word left/right
   edges across candidate rows; stable low-density bands = column gutters.
   Rows from baseline clustering (03). Require ≥ N aligned rows to avoid
   misclassifying prose.
3. **Header detection:** first row with distinct weight/rule below, or
   repeated across pages → `<thead>`.

## Spans

- **colspan:** a cell whose text/bbox crosses ≥2 column bands with no
  interior v-line.
- **rowspan:** a v-adjacent empty grid cell under a tall cell with no
  interior h-line.
- **Nested tables:** a cell whose content itself passes table detection →
  recurse (the Cell holds `blocks`, which may include a Table).

## Cell content

Each cell runs the **full block pipeline** (paragraphs, lists, math,
images) — a Cell is just a small Region. Alignment (`text-align`) from word
positions within the cell; vertical alignment from baseline position in the
cell box; padding from text-to-border distance.

## Output

Semantic table with `role="table"`, `scope` on headers, `colspan/rowspan`
attributes, and a CSS grid/`border-collapse` layout. Fixed-layout mode may
additionally pin cell text; reflowable mode lets the table lay out.

## Fallback

Confidence-gated: if grid inference is ambiguous, fall back to positioned
text (current behavior) rather than emit a broken table. "No broken tables"
(Output Quality) means *never emit a table we're not confident in*, not
"detect every table."

## Validation hooks (08)

Row/column count consistency, no overlapping cells, every grid rect
covered, header present for data tables.
