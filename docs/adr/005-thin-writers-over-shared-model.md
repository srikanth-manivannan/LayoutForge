# ADR-005: Thin Writers over a Shared Document Model

**Status:** Accepted · 2026-07-04

## Context

LayoutForge must output HTML, XHTML, EPUB, XML, and PML (and later accept
EPUB/XHTML/XML as *inputs*). Implementing conversion logic per format would
duplicate typography/structure logic five ways and guarantee drift between
formats.

## Decision

One **format-neutral Rich Document Model** (ADR-001) is the hub. Every
output format is a **thin writer** (a visitor/serializer) over that model;
every future input format is a thin front-end that *populates* it. The
typography and structure engines never know which format is being written.

```
PDF ─▶ Rich Document Model ─▶ { HTML · XHTML · EPUB · XML · PML · fixed-layout }
        ▲
   (future) EPUB/XHTML/XML front-ends populate the same model
```

Two renderers share the model: **fixed-layout** (pixel-accurate proofing
overlay on the raster) and **semantic/reflowable** (structure-first).

## Consequences

- Adding a format never touches the engines — only a new writer.
- No conversion logic is duplicated; formats can't drift.
- Style deduplication and reading order are computed once, reused by all
  writers.
- The current per-page fixed-layout HTML/CSS is renderer A with the
  word/glyph layers; renderer B and the other writers are additive plugins
  (M8), export ZIP last per product sequencing.
