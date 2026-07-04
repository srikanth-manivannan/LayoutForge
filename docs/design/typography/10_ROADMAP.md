# 10 — Implementation Roadmap & Milestones (Deliverable 11)

Sequenced by **accuracy-per-effort** and dependency. Each milestone is
independently shippable, feature-flagged, and degrades to current behavior
if disabled. Milestones beyond M1.7 are **approval-gated**.

## ⭐ Execution order — SEMANTIC-FIRST (decided 2026-07-04, [ADR-008](../../adr/008-semantic-first-ordering.md))

The engine core (M1–M1.7) is frozen. The remaining work splits into
**semantic** reconstruction (structure) and **precision** reconstruction
(glyph placement). Precision (M2) is **postponed** behind the semantic
core, because the Adaptive Reconstruction Engine already captured ~85–90%
of the visual gain, whereas semantic structure unlocks EPUB/XHTML/XML/PML,
accessibility, editing, search, and reading order *all at once* — far larger
product impact. Milestone IDs are unchanged (ADRs/CHANGELOG reference them);
only the **order** changes:

```
M3 (paragraph) → M4 (columns/reading order) → M5 (lists/notes) →
M6 (tables) → M7 (math) → M8 (semantic writers: EPUB/XHTML/XML/PML) →
M2 (precision, the last visual mile) → M9 (scripts/i18n)
```

`report.json` shows the M2 residual is small and bounded (dictionary ~15%
GLYPH-flagged, mostly cosmetic), so deferring it costs little visual
fidelity while the semantic milestones build the product.

## M1 — Run/Word positioning ✅ SHIPPED (down-payment)

Word boxes in the IDM (`WordBox`), captured in extraction, per-word
width-fitting, word-pinned fixed-layout rendering. **Result:** killed the
line-wide ghosting on the reference documents; word starts pixel-exact.
Files: `elements/textbox.py`, `stages/extract_text.py`,
`stages/normalize_idm.py`, `renderers/text_renderer.py`, `css_output.py`.

## M1.5 — Adaptive Reconstruction Engine ✅ SHIPPED (reviewer-insisted prerequisite)

`ReconstructionMode` enum (WORD/RUN/GLYPH/SVG); per-word measure → keep
WORD within tolerance, flag GLYPH otherwise. Dictionary 85% WORD / 15%
GLYPH (341k → 51k, not 341k). Renamed from "Adaptive Precision" — the name
grows with the WORD→RUN→GLYPH→SVG→IMAGE ladder. [ADR-002](../../adr/002-adaptive-reconstruction-engine.md).

## M1.6 — Reconstruction Diagnostics ✅ SHIPPED (reviewer-insisted, before M2)

Every escalated object records **`reason`** (`ReconstructionReason`:
kerning/ligature/width/baseline/rtl/…) and an internal **`confidence`**
(engineering metric, not user-facing); `data-mode`/`data-reason` in HTML;
per-document **`reconstruction_profile`** (counts by mode/reason + mean
confidence) persisted in `idm.json` and logged. Engine extracted to its own
module (`pipeline/typography/adaptive_reconstruction.py`) with the pipeline
layered Geometry → Typography Analyzer → Adaptive Reconstruction → Semantic
([ADR-006](../../adr/006-pipeline-layering.md)). **Measured (dictionary):**
51,199 glyph = 36,086 width_error + 13,583 kerning + 1,530 ligature; mean
confidence 0.973. M2 **consumes** these decisions, never recomputes them.
Files: `core/enums.py`, `pipeline/typography/*`, `document.py`,
`renderers/text_renderer.py`.

## M1.7 — Engine Stabilization ✅ SHIPPED (reviewer-insisted hygiene iteration)

Froze the core before extending it: the **`ReconstructionDecision`** contract
(immutable dataclass — mode/reason/reconstruction_confidence/expected_width/
actual_width/width_error/tolerance) that every later stage consumes and none
recomputes; renamed `confidence` → **`reconstruction_confidence`** (room for
future ocr/table/reading-order confidences); froze the engine's public API
(`__all__` + stability note). Added **per-stage timing + peak memory**
(tracemalloc in `PipelineEngine`), a per-conversion **`report.json`**
(profile + accuracy + performance), **benchmark + performance regression
tests**, and a permanent **[Quality Gate](../QUALITY_GATE.md)**. Direction
for modularity captured as [ADR-007 Capabilities](../../adr/007-capability-architecture.md)
(staged to M4). 94 backend tests. Files: `pipeline/engine.py`,
`pipeline/typography/adaptive_reconstruction.py`, `elements/textbox.py`,
`services/conversion_report.py`, `services/conversion_service.py`.

## M2 — Precision Reconstruction (the last VISUAL mile — POSTPONED after the semantic core, ADR-008)

Renamed from "Glyph Reconstruction": glyphs are one *strategy*, not the
purpose — M2 decides the right precision (RUN / GLYPH / SVG / IMAGE) for each
flagged object. Formalize `FontMetricsEngine` (02) with **kerning**; add
per-glyph placement (`per_glyph_x`) **only for the GLYPH-flagged words**,
**consuming** the frozen `ReconstructionDecision` (never recomputing it), so
the expensive path runs on ~15% of words, not all. Eliminates the residual
on strongly-kerned display words (`HTML`, `Ti…`). *Exit:* PrinceXML +
dictionary width error < 1px worst-case (Quality Gate), glyph-object count
held to the flagged fraction. **Now scheduled after M8** — high engineering
cost, small remaining visual value versus the semantic milestones.

## M3 — Semantic Reconstruction  ★ PHASE 3, the heart of the product (months, not weeks)

Renamed from "Paragraph Reconstruction" (ADR-008 companion): the deliverable
is **Document Intelligence** — the engine understanding *meaning*, not just
one node type. This is Pillar 3 (Semantics), the pivot after which
publishing, accessibility, editing, search, and AI largely fall out of the
model. Delivered as work packages, each shippable and confidence-gated
(ADR-003):

- **WP1 — Paragraphs & Baseline Rhythm** — baseline grid (03), paragraph
  grouping, grid-anchored lines. *Exit:* prose reflows as `<p>` with rhythm.
- **WP2 — Headings & Lists** — heading hierarchy (role classification),
  semantic `<ul>/<ol>` (bullets/numbered/roman/alpha, nesting).
- **WP3 — Reading Order & Regions** — region/column detection, multi-column
  reading order, running headers/footers, TOC & index detection. *Exit:*
  dictionary/journal columns and newspaper flow in correct order.
- **WP4 — Tables** — ruled + borderless detection, rowspan/colspan, nesting,
  header detection → semantic `<table><thead><tbody>` (04).
- **WP5 — Figures & Captions** — figure/caption association, anchored/
  floating placement.
- **WP6 — Footnotes & References** — note/endnote/cross-reference anchoring
  (06), navigable links.

Each WP adds its node to the Rich IDM (ADR-001) and its checks to Validation
(08); none touches the frozen core (ADR-009). The Semantic Analyzer stage
(ADR-006) and the Capability interface (ADR-007) materialize here.

## M4 — MathML Reconstruction Engine  (formerly M7)

Staged: sub/superscript → fractions/roots → operators/matrices →
chemistry; SVG fallback (05). *Exit:* scientific/math benchmarks emit valid
MathML or honest SVG.

## M5 — Semantic renderer + format writers (EPUB/XHTML/XML/PML)  (formerly M8)

Renderer B (07) + writers; reading-order nav; style dedup. *Exit:*
reflowable EPUB from the reference book validates in EPUBCheck.
(Export packaging — the ZIP — lands here per user sequencing: last.)

## M6 — Scripts & i18n  (formerly M9)

RTL width-fitting/bidi, vertical CJK, Indic/Arabic shaping via GSUB (06).
*Exit:* RTL/CJK/multilingual benchmarks pass.

*(M2 — Precision Reconstruction — is detailed above but scheduled here, after
the semantic core: last visual mile, small remaining value. See ADR-008.)*

## Cross-cutting, every milestone

- Benchmark corpus (09) gates each exit criterion in CI.
- Validation rules (08) for the new structures land with their milestone.
- Large-document performance budgets (11) re-verified each milestone.
- The IDM tree (01) is introduced incrementally: M1 added `WordBox`; M2
  adds `Glyph`; M3 adds `Paragraph`; M4 `Region`; etc. No big-bang rewrite.

## Dependencies

```
M1 ✅ ─▶ M1.5 ✅ ─▶ M1.6 ✅ ─▶ M1.7 ✅  (frozen core)
                                  │
   semantic-first (ADR-008):     ▼
   M3 ─▶ M4 ─▶ M5 ─▶ M6 ─▶ M7 ─▶ M8 (EPUB/XHTML/XML/PML writers)
                                  └─▶ M2 (precision — last visual mile)
   M9 (scripts/i18n) after M2/M4
```

Note: M2 remains technically ready right after M1.7 (it only needs the
frozen decisions); it is *scheduled* later by product priority, not
blocked. Any milestone can be pulled forward if priorities change.

## Approval checkpoint

Shipped and frozen: M1–M1.7 (word positioning → adaptive reconstruction →
diagnostics → stabilization). **Next recommended step: M3 — Baseline engine
+ Paragraph reconstruction** — the entry point to semantic structure, which
unlocks reflowable/semantic output (EPUB/XHTML/XML/PML), accessibility,
editing, and reading order. M2 (Precision) is deliberately deferred to after
the semantic core (ADR-008).
