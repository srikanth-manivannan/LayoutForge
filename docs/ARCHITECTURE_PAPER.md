# LayoutForge: Architecture & Rationale

**Status:** Living paper · 2026-07-10

This is the *why* behind LayoutForge — the load-bearing design decisions, not
the implementation. It is the document to hand a new engineer (or a reader of
an open-sourced LayoutForge) so the architecture can be understood, extended,
and revisited deliberately. Implementation detail lives in
[docs/design/](design/00_DESIGN_OVERVIEW.md); the decisions themselves in the
[ADRs](adr/README.md); the normative model in [LFS-1.0](spec/LFS-1.0.md).

## What LayoutForge is

LayoutForge is **not a PDF-to-HTML converter**. It is a **document compiler**:
it lifts a PDF into a rich semantic model of the document, then generates many
output formats from that one model. Framed as a compiler, the pieces are
familiar:

| Compiler | LayoutForge |
|---|---|
| Lexer / Parser | PDF extraction (glyphs, fonts, images) |
| AST | Rich IDM (Document → Region → Paragraph → Line → Run → Word → Glyph) |
| Semantic analysis | Typography + Document Intelligence reconstruction |
| Optimizer | Adaptive Reconstruction (cheapest precision per object) |
| Code generators | Writers (HTML, Fixed-Layout, EPUB, XML, PML) |
| Test harness + golden files | Rendering Validation Framework + corpus |

Everything below follows from taking that framing seriously.

## Why a Rich IDM (not a flat list of positioned lines)

The original model was a flat list of absolutely-positioned lines — it
*screenshotted* layout. That caps accuracy at "looks about right" and cannot
express meaning: no paragraphs, no reading order, no tables, no headings. Every
downstream capability we want — reflowable EPUB, semantic XML, accessibility,
editing, search, AI — needs **structure**, and structure has no representation
in a flat model. So the IDM is a **tree** whose leaves carry measured metrics
and whose interior nodes carry meaning. Build the meaning once; every consumer
reads it. ([ADR-001](adr/001-rich-document-model.md), [ADR-011](adr/011-parallel-rich-idm-migration.md))

## Why a compiler architecture (staged, one-way)

The pipeline is a strict one-way sequence, each stage handing the next a
*fully valid* model:

```
Extraction → Validation → Typography Reconstruction → Semantic Reconstruction → Writers
```

Each stage has one job and one guarantee: extraction guarantees 100% character
fidelity; typography guarantees correct runs, baselines, spacing, fonts;
semantic reconstruction guarantees paragraphs, lists, tables, reading order;
writers only serialize. **If a later stage would have to repair an earlier
one, the bug belongs to the earlier stage.** This is what keeps the renderer
from silently papering over extraction defects — the failure mode that makes
converters un-debuggable. ([ADR-006](adr/006-pipeline-layering.md), [ADR-011](adr/011-parallel-rich-idm-migration.md))

## Why a writer abstraction (renderers, not exporters)

An *exporter* is a one-off that reaches back into the source and improvises.
A *writer* is a pure function from the model to a format. LayoutForge has
writers: `RenderEngine → Writer`, dispatched by target through a
`WriterContext`. A writer **never knows another format exists** and never
reads the source PDF. Adding EPUB/XML/PML is registering a writer — it cannot
touch the engines or the model. This is the difference between a codebase that
supports five formats and one that rots into five divergent converters.
([ADR-005](adr/005-thin-writers-over-shared-model.md))

## Why semantic HTML (spans as style, not position)

The legacy renderer emitted a `<span>` per word, absolutely positioned — a
screenshot in markup. The semantic writer emits `Region→<div>`,
`Paragraph→<p>`, `Line→<span class="lf-line">`, and a `<span>` **only when a
run's style genuinely changes** — plain text otherwise, exactly like Word,
InDesign, or EPUB. A `<span>` is a *style boundary*, never a positioning unit.
Ownership is strict: paragraphs own layout metrics, lines own geometry, runs
own only visual style. The result is editable, reflowable, accessible HTML with
a fraction of the nodes and a handful of deduplicated CSS classes for a whole
book. ([LFS §5](spec/LFS-1.0.md))

## Why visual font identity (not PDF font identity)

PDF font names lie: `ABCDEF+Arial`, `ArialMT`, `Arial-Regular`, `ArialPSMT`,
and `ArialSubset01` are all the same typeface. A run is *"the maximal sequence
of glyphs that renders identically"*, so run identity is derived from what the
reader sees — normalized family, weight, italic, color, size — with subset
names and font-object ids deliberately excluded. Genuine style changes still
split a run, even mid-word; subset-only splits merge. ([ADR-011](adr/011-parallel-rich-idm-migration.md))

## Why adaptive precision (cheapest reconstruction that works)

A 3,000-page book cannot afford glyph-level placement everywhere, and doesn't
need it. Each object is reconstructed at the **cheapest level within
tolerance** (word → run → glyph → SVG), recording *why* it escalated and a
confidence. Precision is spent only where measurement proves it necessary.
([ADR-002](adr/002-adaptive-reconstruction-engine.md))

## Why evidence-accumulating structure detection

Structure comes **only from layout evidence, never from PDF drawing
operators** — an operator marks rendering, not meaning. Paragraph/region
grouping accumulates *weighted* signals (baseline rhythm, spacing, indent,
alignment, font/language continuity, hyphenation, line fill, reading order),
like the Adaptive Reconstruction Engine, and every node records its confidence
and contributing signals. Detection is confidence-gated: below threshold, keep
the accurate positioned objects rather than assert a wrong structure.
([ADR-003](adr/003-confidence-gated-structure-detection.md))

## Why character fidelity is gate zero

The one inviolable invariant: **no character is ever lost, silently altered, or
painted blank.** Unicode comes from the glyph stream (measurements *position*
characters, they never *recover* them). Substitutions are permitted, counted,
and reported; `chars_lost` must equal 0 for every conversion. Every model→model
and model→output boundary re-checks it. ([ADR-010](adr/010-character-fidelity-first.md))

## Why stable IDs, created once

Every node gets a permanent id at creation and never regenerates it. Editing,
comments, AI suggestions, validation findings, compare mode, undo/redo, and
collaboration all need a fixed identity to point at. Retrofitting IDs later is
painful; minting them now is free.

## Why feature flags

Big architectural change ships **in parallel, never big-bang**. The Rich IDM
is generated alongside the legacy model; the semantic writer runs behind
`use_rich_tree` while legacy stays the default; the legacy path is deleted only
after the new one reaches proven parity. Flags (`use_rich_tree`,
`emit_semantic_html`, `emit_stable_ids`, `emit_debug_attributes`, …) replace
scattered boolean parameters and make every migration reversible.

## Why a Rendering Validation Framework

A compiler is only as trustworthy as its golden-output tests. RVF runs the real
pipeline over a real corpus (hundreds of diverse PDFs), measures fidelity /
structure / rendering / performance, diffs writers, and flags regressions
against a versioned baseline. Unit tests prove logic; the corpus proves the
compiler. This is permanent infrastructure, not a one-off script — it is how
the engine evolves safely as tables, math, and new formats land.
([backend/tools/rvf/](../backend/tools/rvf/README.md))

## The through-line

One model, built once, in stages that each guarantee their output; precision
and structure spent only where evidence demands; many formats generated by pure
writers over that model; every character preserved; every change shipped in
parallel and validated against a corpus. That is what makes LayoutForge a
document-reconstruction *platform* rather than another PDF converter.
