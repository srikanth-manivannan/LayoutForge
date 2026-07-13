# Render Instruction Layer (RIL) — Design

**Status:** DESIGN — approved in principle 2026-07-12, implementation awaits
go · supersedes the rejected "adaptive renderer" proposal from the Renderer
Geometry Investigation.

## Why the adaptive renderer was rejected (and this replaces it)

The investigation's selective-anchor ladder put decisions (anchor? threshold?
0.5px?) **inside the renderer** — recreating an "Adaptive Rendering Engine"
and violating the frozen rule *the renderer consumes decisions, never makes
them*. It also made the DOM non-deterministic around thresholds (0.49px →
flow, 0.51px → anchor) and would have had to be re-implemented per output
format.

The correction: **all intelligence stays in reconstruction.** The engine
emits deterministic *render instructions*; every renderer (HTML today —
XHTML/EPUB/SVG/PML later) is a pure compiler over the same instructions.

```
Rich IDM ──► Reconstruction (all decisions: existing engines + instruction builder)
                 │
                 ▼
           RENDER TREE (deterministic RenderInstructions, part of the model)
                 │
     ┌───────────┼───────────┬──────────┐
     ▼           ▼           ▼          ▼
   HTML        XHTML       EPUB       SVG …      (pure compilers, zero decisions)
```

## The instruction model

One instruction node per rendered element, produced by an **Instruction
Builder** that runs in the reconstruction phase (after ReconstructTree +
Adaptive Reconstruction; before any writer). It CONSUMES what the engine
already knows — `ReconstructionDecision`, `WordMeasurement`, `Run.rise`,
`Run.letter_spacing`, word/run origins, paragraph tree — and freezes the
outcome:

```
RenderNode {
  kind:          region | paragraph | line | run | word | glyph
  object_id:     stable id (selection pipeline)
  render_mode:   NORMAL | ANCHORED | ABSOLUTE | GLYPH      ← decided HERE, once
  origin:        (x, y) — absolute for ANCHORED/ABSOLUTE kinds
  baseline:      line baseline (lines carry it; runs inherit)
  rise:          measured baseline offset (px, + = up)
  tracking:      letter-spacing (px, applies across the whole node)
  style_ref:     deduplicated style id (Style Registry)
  children:      [RenderNode]
}
```

Renderer contract per `render_mode` (mechanical, no judgment):
- `NORMAL`   → emit in flow (text node / inline span).
- `ANCHORED` → emit in flow but at a fixed origin (`position:absolute; left`,
  baseline-derived `top`) — used where the engine determined flow diverges
  (run-boundary jumps, cumulative-residual resets, rise ≠ 0).
- `ABSOLUTE` → fully positioned block (lines, regions).
- `GLYPH`    → per-glyph placement (M2; until then renderers emit ANCHORED
  word + tracking, which is the current best available fidelity — the
  *instruction* already says GLYPH so renderers upgrade for free when M2 lands).

## Where each investigation finding lands (all engine-side)

| Finding (measured) | Instruction consequence | Decided by |
|---|---|---|
| Baseline rise (+10.86px `the`) | `rise` on the run node; mode ANCHORED | extraction (`measure_span_rises` ✅ shipped) → builder |
| Run-boundary jumps (−3.33px) | following run ANCHORED at measured origin | builder, from word/run x already in the IDM |
| Cumulative residual (0.28px/glyph × 38) | engine inserts ANCHORED word nodes at reset points it computes ONCE from `WordMeasurement`s | builder (deterministic — same input, same DOM) |
| Mixed-size line box | `baseline` on line nodes; renderers position lines BY BASELINE with pinned strut | builder + compiler contract |
| Paragraph-per-line DOM | RenderTree is built from `page.regions` (paragraph → line → run) — verified working: 189 lines → 58 paragraphs | builder input |

## Determinism guarantee

Thresholds still exist (they must — any decision has one) but they live in
ONE place, run ONCE, and their outcome is **persisted in the model** (the
Render Tree serializes with the IDM). Two renders of the same document are
byte-identical; two formats of the same document use identical geometry;
debugging reads the instruction, not renderer behavior.

## Rendering modes (product feature, not renderer logic)

Mode 1 *Production Preview* and Mode 2 *Pixel Proof* are **two instruction-
builder profiles** (loose/tight anchor policies), not two renderers. The
compiler is identical; only the instruction stream differs.

## Implementation plan (when approved)

1. `pipeline/rendering/instructions.py` — `RenderNode` + Instruction Builder
   (reconstruction side; consumes Paragraph tree + decisions; serializes).
2. Stage wiring after ReconstructTree; validator check: every text run of the
   Rich IDM appears in exactly one RenderNode (fidelity gate extension).
3. Rewrite `HtmlOutputPlugin` path as a pure compiler over the Render Tree
   (paragraph→line→run structure replaces one-`<p>`-per-line output).
4. Acceptance: browser-oracle comparison (M-R5) of instruction origins vs
   browser rects; the reference title page renders `the` raised and the
   title line without cumulative smear.

**Non-goals here:** no changes to Adaptive Reconstruction, extraction beyond
the shipped `rise`, validator core, or quality accounting.

---

## Implementation status (2026-07-12) — approved as the PERMANENT architecture, 8 rules binding

| Rule | Status |
|---|---|
| 1. Compiler reads only the Render Tree (never IDM nodes) | ✅ `html_compiler.py` — enforced forever by an AST import test |
| 2. Deterministic tree (same IDM → identical output) | ✅ tested (double-build byte equality) |
| 3. Real paragraphs (`lf-paragraph > lf-line > runs`) | ✅ shipped as the production `pages/` DOM |
| 4. Compiler never repairs | ✅ rise/rotation/baseline/tracking are tree data; builder computes ALL geometry (incl. baseline-exact line placement: LH ≥ every run box, strut pinned, top solved for the PDF baseline — the Mechanism-C fix) |
| 5. Every compiler uses the same tree | ✅ architecture in place; HTML is the only compiler so far — XHTML/EPUB/SVG/PML are additions, not redesigns |
| 6. RenderTreeValidator gates compilation | ✅ unicode multiset, node counts, id uniqueness, geometry presence |
| 7. Style Registry classes | ✅ deduplicated rules in `common.css` (`lf-p*/lf-r*`), filled deterministically at CSS time, reused at compile time |
| 8. Legacy renderer retired after parity | ✅ `text_renderer.py` + per-block `#tb` CSS **deleted**; parity = full suite + RVF gates on the (1-doc) golden corpus — corpus-scale parity still owed |

Derived-not-canonical: trees live in `context.scratch` for one conversion and
are never serialized. Builder v1 profile = "preview" (lines ABSOLUTE, runs
flow with rise/tracking); run-origin anchor corrections (measured boundary
jumps) are builder v2 — they need run-origin capture at measurement time.

**Success criteria still OPEN (honest):** semantic `pages_semantic/` writer
not yet unified onto the RIL; EPUB/XHTML/SVG compilers not yet written; span
reduction + geometry-score non-regression verified on ONE book, not a corpus;
per-word ChauncyPro-class residual (M2 GLYPH instructions) untouched.

---

## Phase R-2 amendment (2026-07-13) — the compiler produces SEMANTIC HTML, not PDF lines

Field evidence (copyright page): a 7-line paragraph compiled to 7 positioned
`lf-line` divs — a PDF renderer's output, not a document's. Corrected mental
model, now binding:

- **Lines and words are engine concepts.** They exist for measurement and
  reconstruction; **no compiler may emit an element for a Line.**
- **Every paragraph emits exactly one `<p>`** (positioned by its own box —
  region-level placement — with paragraph typography: measured line-height,
  text-align, first-line indent, `white-space: pre-wrap`). **The browser
  wraps the lines.**
- The Instruction Builder flattens each paragraph's lines into a single run
  sequence (line joins become one space — layout, not content), merges
  adjacent identical styles, and folds whitespace-only runs into base style.
  **A span is an HTML optimization for a style change — never a Run, never a
  word.**
- Tree validation: NON-whitespace unicode multiset equality vs the Rich IDM
  (no character lost or invented; join spaces are layout).
- Known, deliberate trade: browser wrap points may occasionally differ ±1
  word from the raster — the price of production-editable HTML. The raster
  remains a proofing backdrop; a pixel-proof instruction profile can exist
  later from the same tree if evidence demands it.

---

## Rule 0 (2026-07-13, permanent): one dimension, one owner

> A single layout dimension must never have two owners. If the PDF owns a
> paragraph's `top`, the PDF must also own its `height`. If the browser owns
> `height` (flow), the PDF must not assert a `height` at all.

Discovered via the Paragraph Layout Investigation: R-2 gave paragraphs
PDF-absolute `top` while handing `height` to browser flow — the two owners
never reconciled, causing paragraph overlap. The fix is not reconciliation
but **not letting one paragraph carry both kinds of geometry** — see
`docs/RENDER_MODE_CLASSIFICATION.md` for the resulting two-contract design
(fixed-layout vs. semantic-flow paragraphs, classified per-paragraph in
reconstruction, never decided by the compiler).
