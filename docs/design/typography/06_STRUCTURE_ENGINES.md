# 06 — Structure Engines: Columns, Lists, Footnotes, Images/SVG, Languages
(Deliverable 7 + supporting structure)

## Multi-column Layout Engine (Deliverable 7)

Detect columns so reading order and reflow are correct (newspapers,
journals, the dictionary's 2-up columns).

- **Detection:** x-projection histogram of body text across the page; deep
  stable gutters split the body into column Regions. Column count validated
  by consistency down the page (a gutter must persist across most rows).
  Guard against tables (04 runs first) and centered display text.
- **Reading order:** columns ordered left→right (LTR) / right→left (RTL);
  within a column, top→bottom. Running heads/feet and margin notes are
  their own Regions, ordered out of the body flow.
- **Spanning elements:** a full-width headline/figure crossing gutters is a
  body-region block between column groups (like PDF page-floats).
- **Output:** reflowable → CSS multicolumn or sequential sections in
  reading order; fixed-layout → positioned column Regions.

## Lists

- **Detection:** repeated line-leading markers — bullets (•, –, ▪),
  decimal (`1.`), alpha (`a)`), roman (`iv.`) — with a consistent hanging
  indent (marker in the gutter, text block indented). Nesting from indent
  depth.
- **Output:** `<ul>`/`<ol>` with `list-style-type` (decimal/lower-alpha/
  lower-roman); `<li>` holds a normal Block. `start` attribute preserved.

## Footnotes / Endnotes / Cross-references

- **Footnotes:** small-font Region below the body, above the page foot,
  often rule-separated; markers matched to superscript references in body.
- **Endnotes:** end-of-chapter/document note lists.
- **Cross-references:** intra-document targets (page/section) → real
  anchors (`<a href="#…">`) so EPUB/HTML navigation works.
- **Output:** `<a epub:type="noteref">` + `<aside epub:type="footnote">`
  (EPUB semantics), degrading to `<sup><a>` for plain HTML.

## Images / SVG / Shapes / Transforms

- **Images:** the background raster remains the visual truth for proofing
  (the shipped hotspot-div decision). For **reflowable/EPUB** output,
  images are materialized from extracted assets with detected role:
  background / inline / floating / anchored, plus **captions** (a small
  text block adjacent to a figure → `<figcaption>`). Clip/mask awareness is
  required before painting (never raw overlays — the documented rule).
- **SVG:** vector art from `get_drawings()` → real `<svg>` paths, shapes,
  gradients, clips, masks (crisp, scalable, tiny). Preferred over raster
  for line art (the "crown = two SVG elements" ideal).
- **Transparency/blend:** opacity, alpha, blend modes from drawing/image
  attributes → CSS `opacity`/`mix-blend-mode` (reflowable) or baked in the
  raster (fixed-layout).
- **Rotation/skew/transforms:** the shipped baseline-origin rotation fix
  generalizes; arbitrary affine transforms → CSS `transform: matrix(…)` on
  the container, Selection-safe (box swap for 90/270 already handled).

## Languages & scripts

- **LTR/RTL:** `writing_direction` per run (extracted); RTL width-fitting
  and word order (currently RTL skips fitting — a defined gap).
- **Vertical writing (CJK):** `writing-mode: vertical-rl`; detect from
  glyph advance direction.
- **CJK / Arabic / Hindi:** cmap + shaping-aware runs; Arabic joining and
  Indic clusters handled at the Glyph layer via the font's GSUB (the Font
  Metrics Engine exposes features). Mixed scripts → per-run direction/font.
- **Bidi:** Unicode bidi algorithm on mixed LTR/RTL lines for logical
  order in reflowable output.

Scripts are sequenced by demand in the roadmap; the model carries the
fields from day one so no rework is needed when each lands.
