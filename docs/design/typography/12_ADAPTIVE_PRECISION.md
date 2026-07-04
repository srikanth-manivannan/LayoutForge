# 12 — Adaptive Reconstruction Engine (Milestones 1.5 + 1.6)

See also [ADR-002](../../adr/002-adaptive-reconstruction-engine.md).

**The load-bearing scalability decision, inserted before glyph
reconstruction at the reviewer's insistence.** Reconstruct at the *cheapest
level that reproduces the object within tolerance*; escalate only where
measurement proves it necessary, **and record WHY plus a confidence** so the
engine is explainable. Without this, a 3,000-page book becomes millions of
glyph objects — fatal for memory, selection, undo, hit-testing, painting,
and validation. With it, only the ~5–15% of objects that need precision pay
for it. Named "Reconstruction" (not "Precision") because it will grow to
decide WORD → RUN → GLYPH → SVG → IMAGE.

## The precision ladder

```
WORD   ← default. Browser lays out the word at its pinned x.
 └ RUN    ← a whole style run laid out together (reserved).
    └ GLYPH  ← per-glyph placement; only escalated words.
       └ SVG    ← vector fallback when structure is unreconstructable.
```

Every object stores three things (M1.6), so the engine is explainable, not
a black box:

- **`mode`** (`core.enums.ReconstructionMode`) — the level; `data-mode` in HTML.
- **`reason`** (`core.enums.ReconstructionReason`) — WHY it escalated:
  `width_error · kerning · baseline · ligature · rtl · vertical · rotation
  · font_subset · unknown`; `data-reason` in HTML.
- **`reconstruction_confidence`** ∈ [0,1] — an internal engineering metric
  that the current reconstruction reproduces the object. **Not user-facing**
  (distinct from the fabricated UI confidence the Properties panel avoids);
  drives decisions and diagnostics. Named specifically (not just
  `confidence`) so it never collides with future `ocr_confidence`,
  `table_confidence`, `reading_order_confidence`, etc.

All four (`mode`, `reason`, `reconstruction_confidence`, `width_error`,
plus `expected/actual_width` and `tolerance`) are emitted as one **frozen
`ReconstructionDecision`** (M1.7) — every downstream stage (M2, validation,
analytics, editor) consumes that contract and never recomputes it.

A paragraph freely **mixes levels** (most words WORD, a few GLYPH) with no
special cases.

## The escalation algorithm (implemented, M1.5)

```
for each word:
    expected = Σ glyph advances (font metrics)      # measured, not estimated
    actual   = word box width (PDF ground truth)
    error    = actual − expected
    record width_error
    if |error| ≤ WORD_TOLERANCE:        mode = WORD   (no correction)
    elif correction implausible:        mode = GLYPH  (don't distort; flag)
    else:                               mode = GLYPH  (apply interim
                                                       letter-spacing; flag)
```

`WORD_TOLERANCE` is a single tunable (currently 0.3px total word width).
GLYPH-flagged words render today with the interim per-char letter-spacing
approximation (visually acceptable) and carry the flag so **M2 reconstructs
only them** per-glyph.

## Measured on real documents (data, not guess)

| Document | Words | WORD | GLYPH-flagged | Reasons (M1.6) | Mean conf |
|---|---|---|---|---|---|
| Zoëga dictionary (660 pp) | 341,029 | **85.0%** | 15.0% (51,199) | width_error 36,086 · kerning 13,583 · ligature 1,530 | 0.973 |
| "1910" credits page | 32 | 87.5% | 12.5% — `HTML` `Tim` `T.` `Wium` | all `kerning` | — |

The engine automatically identifies and **explains** the escalations with
no hardcoded list: on the "1910" page it flags exactly the kerning-heavy
words (caps runs, `Ti`/`Wi` pairs) as `kerning`; across the dictionary the
profile shows tracking-widened justified words dominate (`width_error`),
with real kerning and ligatures behind them. Dense scholarly text escalates
more (15%); prose escalates less (nearer the reviewer's 5%). The ratio is
document-dependent and the tolerance is tunable; the *framework* — and its
`reason`/`confidence`/profile diagnostics — is what makes the whole engine
scale and stay explainable.

## Document profile (analytics, persisted)

The per-document `reconstruction_profile` (counts by mode/reason + mean
confidence) is stored in `idm.json` and logged per conversion — the "gold
for improving the engine over time" the reviewer asked for, and a data
source for Validation ("51,199 glyph words: 36k width, 13.5k kerning,
1.5k ligature").

## Same principle, everywhere (not just words)

The reviewer's insistence generalizes to every reconstruction engine —
**detect, measure confidence, escalate/fall back, never force**:

| Engine | Default | Escalate/fallback when |
|---|---|---|
| Text | WORD | width/kern/baseline error > tolerance → GLYPH |
| Table (04) | keep positioned objects | detection confidence ≥ 95% → semantic `<table>` |
| Math (05) | positioned glyphs | confident parse → MathML; else SVG; else glyphs |
| Figure/art (06) | raster (proofing) | vector recoverable → SVG |

"Never destroy an unusual layout to force a structure" is now a first-class
rule: a low-confidence table stays as accurate positioned objects rather
than a wrong `<table>`.

## Pipeline layering (the reviewer's requested split)

Extraction stays frozen; semantic work is a distinct, debuggable phase:

```
Extraction        (PyMuPDF — frozen)
   ↓  Raw IDM     (pages · lines · spans · words · images · shapes)
Normalization     (reading order, baseline, line metrics, ADAPTIVE PRECISION)
   ↓
Semantic Analyzer (paragraphs · lists · tables · math · columns ·
   ↓               footnotes · captions · reading order)   ← M3+ stages
Rich IDM          (the typographic tree, mixed precision levels)
   ↓
Writers           (fixed-layout · HTML · XHTML · EPUB · XML · PML)
```

Raw IDM never changes; each Semantic Analyzer stage is independent,
feature-flagged, and confidence-gated, so a failure in one degrades to the
prior level rather than corrupting the document — which makes the whole
engine debuggable stage by stage.
