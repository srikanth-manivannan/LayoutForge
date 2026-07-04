# 07 — HTML/CSS Generation Strategy (Deliverable 8)

## Two renderers, one tree

The Rich Document Model feeds **two** generators (format writers are thin
over these):

### A. Fixed-Layout renderer (proofing + fixed-layout EPUB)

Pixel-accurate overlay on the background raster. Positioning altitude,
lowest safe first:

```
Paragraph/Line container   position: absolute   (baseline-anchored)
   Run                     inline span
      Word                 position: absolute; left: <x>   (M1 — shipped)
         Glyph             per-glyph dx when residual > threshold (M2)
```

Rules (several already shipped):
- Container absolute; **browser lays out inside** wherever measurement
  proves it safe (the user's guidance).
- Word pinned to its own x → cross-word drift impossible.
- Baseline from measured baseline_y − ascent (no line-height guessing).
- Unique `@font-face` family per font resource; metric-compatible stacks
  for base-14; no fallback fonts.
- Rotation about the baseline origin.

### B. Semantic/Reflowable renderer (EPUB reflowable, XHTML, HTML)

Structure over position:

```
<section role=region> <p> <span style="font…">run</span> … </p>
<table><thead>…  <ul><li>…  <math>…  <figure><img><figcaption>
```

Rules:
- No absolute positioning; CSS from paragraph styles (indent, leading→
  line-height, space-before/after, alignment).
- Semantic tags from `role` (h1..h6, blockquote, li, figure, aside).
- A shared **stylesheet of derived styles**: recurring run styles are
  deduped into CSS classes (`.s1{font:…}`) instead of per-span inline —
  smaller output, editable, EPUB-friendly.

## Format writers (thin serializers over the tree)

| Format | Writer notes |
|---|---|
| **HTML5** | either renderer; `<!doctype html>`, semantic tags |
| **XHTML** | XML-serialized HTML5, self-closing, namespaced — EPUB content docs |
| **EPUB** | XHTML content docs + nav (reading order from Regions) + fonts + OPF/NCX + `epub:type` semantics; fixed-layout OR reflowable profile |
| **XML** | direct tree serialization against a published LayoutForge schema |
| **PML** | flat paragraph/style/pagebreak writer over the tree |

Each writer is a visitor over the same model — adding a format never
touches the typography engine (format-independence, Principle 5).

## CSS strategy

- **Design tokens** for chrome only; document CSS is *generated* from
  measured styles, never themed (the document is the artifact).
- **Style deduplication:** hash run styles → shared classes; per-instance
  only geometry (fixed-layout) or nothing (reflowable).
- **Self-contained projects:** relative `../resources/...` URLs (shipped)
  so a page renders identically from disk, served, or in the iframe — the
  one golden path.
- **@font-face** from the sanitized/completed font files (all shipped font
  fixes feed this).

## Backward compatibility

The current per-page `page_XXXX.css` + `page_XXXX.html` fixed-layout output
is renderer A with the word/glyph layers added — no viewer change required.
Renderer B and the format writers are additive (new output plugins), gated
by milestone.
