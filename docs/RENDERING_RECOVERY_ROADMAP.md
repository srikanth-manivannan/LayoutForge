# Rendering Recovery Roadmap

**Status:** APPROVED with amendments · 2026-07-12 (review rating 9.5/10)
**Amendments folded in:** M-R0 expanded to a Benchmark & Certification
Platform; metric hierarchy (Typography/Layout/Semantic → Overall); Extraction
Accuracy metric family added; M-R2.5 Font Intelligence added; M-R8 Image
Reconstruction split out; Phase 3 restructured reading-order-first; developer
Benchmark Dashboard; binding corpus-completion rule (below).

> **Binding rule for every implementation milestone:** Do not optimize
> individual documents. A milestone is complete only when it demonstrates a
> statistically significant reduction of one or more failure clusters across
> multiple documents, with no regression in any other category. The benchmark
> corpus — never a single PDF — is the source of truth for engineering
> decisions.
**Scope:** Audit + roadmap only. No production code was modified for this
document. Implementation proceeds milestone-by-milestone after approval, under
the frozen architecture (ADR-009/011) and the Development Model (evidence-
driven, earliest-stage-first, regression-test-before-fix, cluster-driven).

**Honesty key used throughout:**
✅ CONFIRMED (observed in code or measured on a real document) ·
🟡 SUSPECTED (mechanism identified, not yet measured) ·
⚪ NOT OBSERVED (listed in the task brief but no evidence found; needs corpus
data before it becomes a work item) ·
⛔ NOT BUILT (known absent, by roadmap).

---

## 1. Current Architecture Review

The pipeline (all stages real and wired):

```
Extraction (PyMuPDF)                    extract_fonts / extract_images / extract_text
  → Geometry Normalizer                 typography/geometry_normalizer.py
  → Character-Spacing (Tc) analysis     typography/character_spacing.py   [new]
  → Adaptive Reconstruction             typography/adaptive_reconstruction.py
  → Tree Reconstruction                 stages/reconstruct_tree.py → Run/Word/Line/Paragraph/Region
  → Rich IDM Validation                 validation/idm_validator.py (strict when use_rich_tree)
  → Quality Accounting                  quality/accounting.py (ledger + scorecard)
  → CSS Generator                       outputs/css_output.py            [LEGACY PATH]
  → HTML Generator (legacy)             outputs/renderers/text_renderer.py  [PRODUCTION DEFAULT]
  → HTML Generator (semantic)           outputs/writers/html_writer.py   [flag-gated OFF]
  → Viewer                              frontend/src/viewer/* (iframe-per-page)
  → Workspace                           frontend/src/layout|panels|components
```

Assessment (agreeing with the external review): **architecture ~9.5/10,
rendering ~6.5–7/10.** The model, validation, quality accounting, RVF, and
viewer engine are production-grade. The *output* is not, because:

1. **The production default renderer is still the legacy word-pinned path.**
   The semantic writer exists, is validated, and reduces spans by 844 on the
   reference book — but `use_rich_tree=False`, so every screenshot users see
   is `<span class="lf-word">` output. ✅ CONFIRMED (`config.py`,
   `text_renderer.py:44-66`).
2. **The frontend has never met the Rich IDM.** `frontend/src/document/
   idmTypes.ts` contains no `regions`/`Paragraph`/`Run` types; Properties,
   search, and validation all read `text_blocks`. ✅ CONFIRMED (grep: zero hits).
3. **Quality metrics measure conservation and escalation, not geometry.**
   Character fidelity 100% coexists with visibly-wrong pages. The scorecard
   improved (73.7%→24.35% escalation) faster than the visual output because
   escalation counts *decisions*, not *pixels*. ✅ CONFIRMED (user observation
   + metric design).

---

## 2. Rendering Audit (backend, per pipeline stage)

### Extraction
| # | Finding | Status | Evidence |
|---|---|---|---|
| E1 | `Tw` (word spacing), `Tz` (horizontal scaling), `TL` (leading), `Ts` (rise) never extracted. `Tz` is common in InDesign exports. Fields reserved on `Run` but always default. | ⛔ NOT BUILT | `run.py` reserved fields; no extractor |
| E2 | Vector shapes never extracted (`ShapeElement` docstring: "No extraction stage populates this"). Overlay-only accuracy mode silently loses all vector art; only the background raster carries it. | ✅ CONFIRMED | grep `get_drawings` → none |
| E3 | Italic/regular font attribution split mid-word (`New York Time`\|`s`) — authored style or PyMuPDF artifact, unresolved (backlog 001b). | 🟡 SUSPECTED | idm.json + ROAD_TO_PHASE4 001b |
| E4 | fontTools warning `1 extra bytes in post.stringData array` on every conversion of the reference book — benign so far but unreviewed. | 🟡 SUSPECTED | every RVF run log |
| E5 | Missing characters at extraction: **none observed** — chars_lost = 0 on all measured documents; gate 0 enforced. | ⚪ NOT OBSERVED | RVF runs |

### Typography measurement / Adaptive Reconstruction
| # | Finding | Status | Evidence |
|---|---|---|---|
| T1 | **Width comparison is definitionally mismatched**: `word.width` is PyMuPDF's *ink bounding box*; `natural_text_width` is a *pen-advance sum*. Measured: constant ~2px gap per word regardless of glyph count. Current fix is a calibrated tolerance (`word_tolerance_px()` = 2.0 + 0.08/glyph) — a **band-aid that widens the blind spot**: real sub-2px errors are now invisible. The root fix is to measure each word's *actual advance extent* from `get_texttrace` origins (already parsed for Tc) and compare advance-to-advance, letting the tolerance drop to ~0.25px. | ✅ CONFIRMED | scaling measurement 2026-07-11; `adaptive_reconstruction.py` |
| T2 | **Tc tracking is estimated per-span (median)**; individual words drift ±4px from the span median (`kitchen` -4.04 ×4, `stinking.` -5.24) → 253 words still escalate. Per-word actual-advance measurement (same fix as T1) eliminates the estimate entirely. | ✅ CONFIRMED | remaining-escalation characterization |
| T3 | **Kerning mismatch with the browser**: `natural_text_width` deliberately excludes kerning ("no kerning — CSS default") — but the CSS default `font-kerning: auto` DOES kern OpenType fonts in all modern browsers, and the generated CSS never sets `font-kerning: none`. Measured widths and browser widths systematically disagree on kerned fonts. Same for ligatures (`font-variant-ligatures` unset; browser may form `fi` ligatures extraction counted as 2 chars). | ✅ CONFIRMED | `font_metrics.py:99-101`; grep CSS → no kerning/ligature control |
| T4 | Mixed-size lexical words (`Tot theToad`, +102/+128px) unhandled — a Word spanning runs of 115/60/115px has no meaningful single width fit. Backlog 003. | ✅ CONFIRMED | ROAD_TO_PHASE4 003 |
| T5 | RTL/vertical/rotated lines get **no width fitting at all** (`reconstruct_line` returns None for RTL; rotation handled only by the legacy CSS transform path). No bidi model. | ⛔ NOT BUILT | `adaptive_reconstruction.py:_compute_line_spacing` |
| T6 | Escalation reasons LIGATURE/KERNING classified from cheap text heuristics (substring "fi" etc.), not from font GSUB/GPOS tables. | ✅ CONFIRMED | `classify_reason()` |

### Rich IDM / builders
| # | Finding | Status | Evidence |
|---|---|---|---|
| M1 | Region Builder emits exactly one `body` region per page — no columns, headers, footers, margins. Reading order is naive top-to-bottom (row-tolerance sort). Multi-column documents will interleave. | ⛔ NOT BUILT (Phase 3 WP3) | `region_builder.py`, `geometry_normalizer.py` |
| M2 | Paragraph scorer has 6 signals of the ~15 specified (missing: list markers, hanging indent, widow/orphan, language continuity, bullet/number patterns, column). Roles are always `p` — no headings. | ✅ CONFIRMED | `paragraph_builder.py` `_SIGNALS` |
| M3 | Validator lacks several planned checks: `overlapping_words`, `invalid_word_bbox`, `run_bbox_mismatch`, `duplicate_unicode`, `unicode_order_change`, `fragment_cycle`. | ✅ CONFIRMED | `idm_validator.py` vs Rule-10 list |
| M4 | Paragraph-level `space_before/space_after/first_line_indent` computed only trivially; `leading` = median line leading. Paragraph *rhythm* (baseline grid) not modeled. | ✅ CONFIRMED | `paragraph_builder.py` |

### HTML/CSS generation
| # | Finding | Status | Evidence |
|---|---|---|---|
| H1 | **Legacy renderer is the production output**: one absolutely-positioned `<span>` per word, per-word letter-spacing, `left:` offsets — reconstruction logic living in the renderer, which ADR-011 forbids. This is the direct cause of "paragraphs split into excessive spans". | ✅ CONFIRMED | `text_renderer.py`, `css_output.py` |
| H2 | **Semantic writer has no fixed-layout mode.** It emits pure reflow (no page geometry), so it cannot yet replace the legacy path for pixel-faithful viewing — paragraphs need `position:absolute` + baseline-derived `top` before the flip. | ✅ CONFIRMED | `html_writer.py` (no geometry emitted) |
| H3 | Semantic writer ignores `Run.letter_spacing` (measured Tc is on the model but never emitted as CSS `letter-spacing`), and ignores `Line.baseline_y` (lines are inline `<span>`s). | ✅ CONFIRMED | `html_writer.py` `_run_declarations` |
| H4 | Legacy line-height fallback = `font_size × 1.2` when metrics missing; per-line `<p>` makes true paragraph line-height impossible. | ✅ CONFIRMED | `geometry_normalizer.py`, `css_output.py` |
| H5 | No kerning/ligature CSS policy (see T3) — must be decided once and enforced in both writers, matched to whatever the measurement assumes. | ✅ CONFIRMED | grep |
| H6 | Images: no working-copy size policy (LFS §7a reserved, Phase 2.8); originals served at full resolution (135MB book). No SMask/clipping audit yet. | ⛔ NOT BUILT / 🟡 | `image_renderer.py`, LFS §7a |

### Fidelity measurement itself
| # | Finding | Status | Evidence |
|---|---|---|---|
| Q1 | **No geometry metrics.** Nothing measures baseline error, word drift, paragraph drift, line-height deviation, or overlay difference — the exact things users perceive. The scorecard can pass while the page looks wrong (metric improved faster than visuals). | ✅ CONFIRMED | `quality/accounting.py` |
| Q2 | RVF aggregates are corpus-wide only — no per-category breakdown (escalation by category, width-error distribution), no failure clustering. Statistics exist per document but aren't clustered. | ✅ CONFIRMED | `tools/rvf/runner.py:_aggregate` |
| Q3 | No browser oracle and no pixel regression (Playwright not installed — deliberate, greenlit for after corpus stability). | ⛔ NOT BUILT | requirements.txt |

---

## 3. Frontend + Workspace Audit

The viewer/workspace is **stronger than the task brief assumed**. Several
listed defects are already designed away:

| Brief item | Audit result |
|---|---|
| "Frontend preview differs from generated HTML" | ⚪ NOT OBSERVED — the viewer loads the *actual generated page HTML* into a same-origin iframe (`IframeRenderer`); one rendering path for direct-open/served/preview by construction. |
| "Shadow DOM / iframe inconsistencies" | ⚪ NOT OBSERVED — Shadow DOM is explicitly avoided *because of* its @font-face quirks (documented in `IframeRenderer.ts`). |
| "Font loading inconsistencies" | ⚪ NOT OBSERVED — every mount awaits `contentDocument.fonts.ready` before reveal. Residual risk: `@font-face` descriptors (`css_weight`) mismatching actual font file weights would mis-match at *selection* time, not load time. 🟡 worth a corpus check. |
| "Viewer rendering differs from browser rendering" | ⚪ NOT OBSERVED — same document, same engine. Zoom is a pure CSS `transform: scale()` on a natural-size iframe (no reflow-based scaling drift). |

Real frontend gaps:

| # | Finding | Status |
|---|---|---|
| F1 | **Rich IDM invisible to the frontend**: `idmTypes.ts` has no regions/Paragraph/Line/Run/Word types; Properties panel, search index, and validation worker all consume `text_blocks`. When the semantic path becomes default, the whole inspection surface goes blind. | ✅ CONFIRMED |
| F2 | **Whole-file `idm.json` fetch**: `DocumentManager` downloads and parses the entire IDM per project (honest scope note in the code). The Rich tree makes idm.json substantially larger; for 3,000–10,000-page documents this is the primary memory/latency risk. Needs server-side page-slice endpoint. | ✅ CONFIRMED |
| F3 | `pages_semantic/` output is generated but not routed anywhere in the UI — no way to view or compare the semantic rendering. A legacy-vs-semantic compare view is a prerequisite for the default flip. | ✅ CONFIRMED |
| F4 | Validation panel surfaces the frontend validation worker's findings; the backend's `idm_validation` + `quality` scorecard (per-stage ledger, rendering fidelity) are not displayed. The "Paragraph reconstructed 94% · ✓ baseline ✓ indent" explainability story has no UI. | ✅ CONFIRMED |
| F5 | Wireframe parity: hifi mockups exist (`docs/design/hifi/` — dashboard, import-center, workspace-accessibility). Implemented: workspace shell, docking (react-resizable-panels, persisted), viewer, thumbnails, search, compare panel, validation panel, properties, logs, command registry. NOT audited pixel-by-pixel against mockups — a design-review pass with the mockups open is still owed (P2). | 🟡 |
| F6 | Virtualization: iframe cap (9) + IntersectionObserver promotion + contiguous strip is correct for continuous reading. Constraint: no full-document proportional scrollbar (strip is only mounted pages) — long-jump UX relies on thumbnails/goto. Acceptable, but should be an explicit product decision. | ✅ CONFIRMED (design) |

---

## 4. Large Document Review (500 / 1k / 3k / 10k pages)

**Verified by design, NOT yet by measurement** — no large document has been
run since the Rich IDM landed. ✅ = bounded by construction; 🟡 = unverified.

| Concern | Status | Notes |
|---|---|---|
| Mounted iframes | ✅ | Hard cap `MAX_MOUNTED_PAGES = 9`; eviction farthest-from-anchor. |
| Scroll windowing | ✅ | IntersectionObserver promotion; contiguity invariant; suppression window on programmatic jumps. |
| Frontend IDM memory | 🟡❗ | Whole-file idm.json parse (F2). Rich tree inflates size ~2–3× (runs+words+fragments per line). A 10k-page IDM could be 0.5–2GB of JSON. **This is the #1 large-doc blocker.** |
| Backend pipeline memory | 🟡 | Whole `Document` held in memory through all stages; `to_dict` serializes at once. tracemalloc per-stage exists (good) but no budget asserted per page count. |
| RVF on big docs | ✅ | 135MB/40-page book: 275–356s/run. Extrapolated 3k pages ≈ hours per doc — corpus runs need `--dpi` low + page sampling option (roadmap item). |
| Search | ✅ | Chunked indexing (20 pages/tick), capped LRU. |
| Thumbnails | 🟡 | Served from full background rasters (300 DPI default) — a 10k-page thumbnail rail streaming full-res PNGs will thrash; needs the Phase 2.8 variant pipeline (thumbnail/preview/working/original). |

Exit criteria for this area: run one real 500+ page document end-to-end and
record per-stage time/peak-memory + viewer heap; then extrapolate honestly.

---

## 5. Rendering Recovery Roadmap (milestones)

**Governing rule (from the Development Model, sharpened for this phase):**
no fix ships unless it addresses a **cluster** — a failure signature measured
across multiple documents/categories in RVF — and every milestone's exit is a
*statistical* improvement on the corpus, not a better single book.

**Ordering rationale:** measurement before correction (you can't fix what the
gate can't see) → typography root causes (earliest stage) → renderer flip →
oracle/pixel verification → UI → performance.

---

### M-R0 — Corpus & Benchmark Platform *(prerequisite; RVF becomes the permanent benchmark + certification system)*
- **Problem:** 1 document = smoke test. No per-category stats, no clustering,
  no developer dashboard, no per-family reports.
- **Root cause:** RVF aggregates corpus-wide only (Q2); corpus dirs empty.
- **Modules:** `tools/rvf/*` only (+ nothing in the engine).
- **Work — not "assemble a corpus" but build the platform around it:**
  (a) User supplies ≥100 PDFs across the `golden-corpus/` categories (agent
  cannot source licensed PDFs); (b) **per-category aggregates**: pass rate,
  escalation, confidence, substitution, width-error distribution
  (p50/p90/p99), span reduction, timings, memory; (c) **failure clustering**:
  issues grouped by (code, stage) with document + category coverage, so
  "affects N docs across M categories" is computed, and the significance rule
  (≥3 docs or ≥20% of a category) is machine-evaluated; (d) **report
  families**: category report, cluster report, typography report, font
  report, rendering report, performance report, certification report — all
  under one output tree; (e) **developer Benchmark Dashboard** (extends the
  existing `index.html`): per-category rows showing Rendering / Typography /
  Extraction / Performance / Pass rate / Regressions / Open issues; (f)
  **Extraction Accuracy** metric family (per doc + per category): unicode,
  characters, words, fonts resolved, images, shapes, metadata — so a defect
  is attributable to extraction vs rendering *by number*, not debate;
  (g) fix the artifact/name **collision bug** (two `doc.pdf` in different
  category folders currently overwrite each other's artifacts — keyed by
  filename, must key by corpus-relative path); (h) `--sample-pages N` for
  huge books (deferred until the corpus contains one).
- **Risk:** low (tooling only). **Dependencies:** user's PDFs for real
  signal; platform itself buildable now. **Effort:** M.
- **Validation:** dashboard shows category tables + cluster list on a
  categorized corpus; certification consumes the cluster rule.
- **Regression tests:** aggregate/cluster shape + name-collision tests.
- **Fidelity gain:** none directly — makes every later gain measurable and
  prevents single-document overfitting. `RVF → Benchmark Platform → Corpus
  Dashboard → Release Certification`.

### M-R1 — Document Fidelity Measurement Framework *(renamed per review — the missing metric layer, Q1)*
- **Problem:** scorecard passes on visibly-wrong pages; nothing measures what
  users perceive; no stable structure for future metrics.
- **Root cause:** all metrics are conservation/escalation counts.
- **Modules:** `quality/fidelity.py` (new, measurement-only),
  `tools/rvf/{metrics,trends,report}.py`.
- **Contract (per review):** every metric = `{current, target, pass,
  confidence, source}`; reserved slots exist now so score semantics never
  change; **gated scoring, never averaged** (overall = AND over critical
  family gates; trend score = weakest-link min); trend history per run;
  outputs = machine-readable summary.json + human-readable
  `quality_dashboard.html` (gauges, trends, categories, clusters,
  certification).
- **Work:** static (no browser) geometry metrics computed from the IDM vs the
  *emitted* CSS/HTML of the production path, organized as a **score
  hierarchy** (so Phase 3 slots in without redesign):
  - **Typography Score** — baseline error, tracking error, kerning error,
    word-spacing error, character-spacing error (px averages + p90);
  - **Layout Score** — paragraph rhythm/drift, line-height deviation,
    alignment, margins (columns join at Phase 3);
  - **Semantic Score** — reserved structure slots (paragraph accuracy,
    reading order, lists, tables) — populated as Phase 3 lands, present in
    the schema now;
  - **Extraction Score** — rolls up the M-R0 Extraction Accuracy family;
  - **Rendering Score** = weighted Typography + Layout; **Overall Score** =
    Rendering + Semantic + Extraction.
  Later (M-R5) the same geometry metrics are re-measured in a real browser.
  Add all to the scorecard with targets (initial: ≤0.5px avg, tightened to the
  approved table after calibration) and to RVF category aggregates + dashboard.
- **Risk:** low-medium (must not double-count the T1 bbox/advance confusion —
  define every metric advance-based). **Dependencies:** none. **Effort:** M.
- **Validation:** score correlates with the known-bad reference pages (title
  page must score worse than body pages before any fix).
- **Regression tests:** synthetic pages with injected drift of known size.
- **Fidelity gain:** none directly; converts "looks wrong" into numbers.

### M-R2 — Typography Measurement Engine v2 *(renamed per review — advances, tracking, Tc, kerning policy, tolerance, width fitting; T1+T2, the big one)*
- **Approval conditions (2026-07-12):** (1) extended drift diagnostics FIRST —
  per-page, per-font, per-reconstruction-reason statistics (mean/median/p95/
  max + worst-20 words) so improvement is verifiable at the right
  granularity; (2) strictly measurement + reconstruction logic — **the
  renderer is not touched** (semantic renderer changes wait for M-R4, after
  M-R2/M-R3 demonstrably reduce drift across the corpus).
- **M-R1 evidence (single-document corpus — do not over-generalize):**
  baseline_error 0.001px (baseline placement essentially exact *for the
  current corpus*), word_drift 1.936px ≈ tracking_residual 1.94px — near-
  identical values pointing at horizontal advance calculation, not
  positioning; line_height_deviation 1.71px (new signal, feeds M-R4).
- **Problem:** 24% escalation, 0.92 confidence, 1.85px width error; ±4px
  per-word tracking drift; 2px tolerance blind spot.
- **Root cause:** ink-bbox vs advance-sum comparison + per-span median Tc.
- **STATUS (2026-07-12): implemented + measured on the 1-doc corpus — NOT
  closable yet (binding rule needs multi-document evidence).** Results:
  word_drift 1.936 → **0.163px** (PASS ≤0.25); tracking_residual 1.94 →
  **0.0** (PASS); mean confidence 0.921 → **0.984**; drift p95 0.743px;
  the tracking cluster (n=359) now measures **0.063px mean**. Escalation
  moved 24.4% → **42.6%** — *not a visual regression*: removing the 2px
  bbox blind spot exposed a previously-invisible cluster. Drift-by-font
  isolates it exactly as designed: **ChauncyPro-Regular (n=765, median
  residual 0.282px, p95 0.70)** carries it — per-glyph placement genuinely
  non-uniform by ~0.3px (GPOS kerning in a handwriting face, or subset
  hmtx-vs-/Widths mismatch) — while Palatino-Roman body text measures
  **0.001px median** (the general algorithm is now near-exact). Remaining
  named clusters → M-R2.5/M-R3 (ChauncyPro residual, ligatures ~2–3px n=6),
  issue 003 (KGDancing mixed-size words), M-R4 (line_height_deviation 1.71px).
- **Modules:** `character_spacing.py`, `adaptive_reconstruction.py`,
  `normalize_idm.py` (all existing — no new abstractions).
- **Work:** the texttrace char stream (already matched per line for Tc) also
  yields each word's **actual advance extent** (first-glyph origin →
  last-glyph origin + last advance). Store it as the word's measured width;
  compare advance-to-advance; tighten `word_tolerance_px` toward a flat
  ~0.25px; per-word tracking replaces span-median estimates. Escalation then
  means "genuinely non-uniform internal geometry" only.
- **Risk:** medium — texttrace matching must stay bail-out-safe (it already
  is); words in unmatched lines keep today's behavior.
- **Dependencies:** M-R0 (prove it on clusters, not one book), M-R1 (geometry
  score must improve, not just escalation).
- **Effort:** M–L. **Validation:** corpus stats: escalation <10%, confidence
  >0.99, width error <0.25px *across categories*; geometry score improves.
- **Regression tests:** per-word advance measurement unit tests + reference-
  book cluster tests (`kitchen`/`stinking.` class).
- **Fidelity gain:** high — eliminates the dominant escalation cluster and the
  letter-spacing over-correction visible in output.

### M-R2.4 — Typography Cluster Analysis *(inserted per review 2026-07-12; investigation only, NO engine changes)*
- **Purpose:** make M-R3 evidence-driven. One report answering: which fonts
  contribute most residual drift? are problems concentrated in font
  *classes* (handwriting/serif/sans/display/typewriter)? what share of drift
  is kerning vs ligatures vs subsets? how does drift distribute (histograms,
  not just medians)?
- **Deliverables:** per-font cluster table (docs, words, median/p95 drift,
  escalation, reason breakdown %); per-font-class rollup; drift + escalation
  histograms (0–0.1 / 0.1–0.2 / 0.2–0.5 / 0.5–1 / >1 px); **GPOS/GSUB
  candidates** (probe the extracted font files for kern/GPOS/GSUB+liga —
  directly tests the ChauncyPro kerning-vs-widths hypotheses); worst fonts /
  most stable fonts. Emitted as `typography_report.json` + a dashboard
  section (this also delivers M-R0's promised "typography report" family).
- **Modules:** `tools/rvf/` only. **Effort:** S–M.

### M-R2.5 — Typography Knowledge Base *(renamed from "Font Intelligence" per review — broader than fonts: metrics, GPOS, GSUB, ligatures, kerning behavior, subset quirks, variable axes, fallback mappings, writing systems)*
- **Problem:** every conversion re-derives font behavior from scratch;
  recurring per-font quirks (subset gaps, tracking-prone faces, ligature
  formers, bad `post` tables like E4) are re-discovered per document.
- **Root cause:** no persistent font knowledge.
- **Modules:** new data under `tools/rvf/` (a *benchmark* asset, not an
  engine abstraction — the engine stays frozen; it may *read* the database
  as calibration input, exactly like base-14 metric tables today).
- **Work:** a font database accumulated across corpus runs, keyed by
  normalized family+style: unitsPerEm, ascender/descender, x-height, cap
  height, observed tracking distributions, average kerning effect, common
  ligatures, problematic glyphs, substitution history, subset coverage,
  variable-font axes. RVF's font report (M-R0) feeds it; the typography
  stages consult it for priors (e.g. "this face historically kerns hard →
  expect negative residuals").
- **Risk:** low-medium (must remain advisory — never override measurement).
- **Dependencies:** M-R0 (font report), M-R2 (advance-based measurement
  supplies clean observations). **Effort:** M.
- **Validation:** corpus re-run with the database populated shows reduced
  unknown-classification and escalation on repeat fonts.
- **Fidelity gain:** compounding — LayoutForge starts to "know" fonts.

### M-R3 — Browser Text Policy: kerning/ligatures *(T3/H5)*
- **Problem:** measurement assumes unkerned, browser kerns; ligatures
  uncontrolled → silent width + DOM-text drift.
- **Root cause:** no CSS text-rendering policy; never decided.
- **Modules:** `css_output.py`, `writers/html_writer.py` (+ LFS §2 one line).
- **Work (decision then ~20 lines):** either (a) `font-kerning: none;
  font-variant-ligatures: none` on text containers so output matches the
  advance-based measurement exactly — visually slightly looser but *provably*
  placed; or (b) model kerning/GPOS in measurement (large; defer). **Recommend
  (a) now**, revisit (b) if the corpus shows kerned-font clusters.
- **Risk:** low. **Dependencies:** M-R2 (same measurement definition).
- **Effort:** S. **Validation:** M-R5 oracle confirms browser width ==
  measured width within 0.25px.
- **Fidelity gain:** medium — removes an invisible systematic drift on every
  OpenType body font.

### M-R4 — Semantic Fixed-Layout Mode + Default Flip *(H1/H2/H3, kills span explosion in production)*
- **Problem:** production output is still word-per-span; semantic writer can't
  do fixed layout; measured Tc never reaches CSS.
- **Root cause:** semantic writer was built reflow-first; flip gated on
  fidelity that M-R2/M-R3 now provide.
- **Modules:** `writers/html_writer.py` (fixed-layout emission: positioned
  `<p>` per paragraph via bbox + baseline, `lf-line` retains `baseline_y`,
  runs emit `letter-spacing` from `Run.letter_spacing`), `generate_semantic_
  html.py`, then `conversion_service` default + legacy retirement (Phase 2.9)
  once parity holds.
- **Gate (unchanged from plan):** legacy↔semantic Unicode + geometry-score +
  visual diff parity on the corpus, THEN flip `use_rich_tree` default, THEN
  remove legacy renderer + `TextBlock.spans`.
- **Risk:** medium-high (this is the user-visible switch). **Dependencies:**
  M-R1..M-R3, F3 (compare UI) recommended first. **Effort:** L.
- **Validation:** corpus parity report; geometry score ≥ legacy on every
  category. **Regression tests:** writer geometry tests + corpus baselines.
- **Fidelity gain:** high (structural) — production HTML becomes semantic,
  span-minimal, paragraph-metric-driven.

### M-R5 — Browser Measurement Oracle + Pixel Regression *(Q3; dev/CI only)*
- **Work:** Playwright as dev/CI dependency. (a) Oracle: load generated page,
  `getBoundingClientRect` + computed style per run/word → compare to PDF
  geometry → browser-measured Geometry Score; (b) pixel diff vs background
  raster with per-page heatmaps + diff %, wired into RVF artifacts
  (`comparison.png`, per the earlier spec).
- **Risk:** medium (CI flakiness — mitigate: fixed viewport, font-ready waits,
  deterministic pages). **Dependencies:** M-R1 (metric definitions), any time
  after M-R2. **Effort:** M–L.
- **Validation/gain:** the final arbiter for "Rendering Fidelity > 99%".

### M-R6 — Frontend: Rich IDM surface + compare + quality UI *(F1/F3/F4, P2)*
- Add regions/Paragraph/Run types to `idmTypes.ts`; Properties shows
  paragraph confidence + signals ("94% · ✓ baseline ✓ indent"); route
  `pages_semantic/` into a legacy-vs-semantic compare view (reuses
  ComparePanel); surface backend `quality` scorecard + `idm_validation` in the
  Validation panel; design-review pass against `docs/design/hifi/` mockups
  with a checklist (F5).
- **Effort:** M–L across several sessions. **Dependencies:** none hard;
  compare view ideally before M-R4's flip.

### M-R7 — Large Documents *(P3; F2, §4)*
- Server-side IDM page-slice endpoint (`/projects/{id}/idm/pages/{n}`) +
  DocumentManager consuming slices; run + record a real 500–1000-page
  document (per-stage time/memory + viewer heap) before optimizing further.
- **Dependencies:** corpus contains at least one big document. **Effort:** L.

### M-R8 — Image Reconstruction & Publishing-Grade Asset Fidelity *(split out of "assets" — publishing customers care about image fidelity nearly as much as text)*
- **Problem:** image handling is minimal: bbox + z-index + raw asset. No
  audit of transparency or color pipelines; no working-copy policy.
- **Scope:** SMask/soft masks · transparency + blend modes · clip paths ·
  ICC profiles · CMYK→sRGB conversion · JPEG2000 decode · vector shapes/SVG
  extraction (E2 — today overlay-only mode loses all vector art) · asset
  variants per LFS §7a (thumbnail / preview / working ≤400k px / original
  preserved losslessly, thresholds set from corpus image statistics).
- **Modules:** `extract_images.py`, `image_renderer.py`, a shapes extractor
  (fills the long-reserved `ShapeElement`), asset manifest.
- **Risk:** medium (color management is subtle). **Dependencies:** M-R0
  (corpus image statistics decide thresholds and priorities — audit first:
  how many corpus docs actually use SMask/CMYK/JPX?). **Effort:** L–XL,
  cluster-gated per sub-feature.
- **Validation:** image-region pixel diff (M-R5 infrastructure) + per-format
  decode tests. **Fidelity gain:** high for image-heavy categories
  (children's books, magazines, comics).

### Phase 3 — Document Intelligence *(restructured: reading order drives everything)*
Approved order (replaces the WP1-first sequence):
```
Reading Order → Regions/Columns → Paragraphs → Lists → Headings
  → Tables → Math → Footnotes → References → Accessibility → Export
```
Rationale: paragraphs grouped before reading order is settled must be
regrouped when it changes; reading order and regions are the coordinate
system for every other structure. Semantic Score slots (M-R1) fill in this
order. **Entry to Phase 3 is gated** — see §9.

---

## 6. Category Map (Phase 3 of the brief)

| Category | Items | Milestone |
|---|---|---|
| Typography measurement | T1, T2, T6 | M-R2 |
| Kerning/tracking/ligatures | T3, H5 | M-R2 + M-R3 |
| Font metrics | T1 (definition), E4 (post table noise) | M-R2 / triage |
| Baseline / line-height | H3, H4, Q1 | M-R1 + M-R4 |
| Run/Word builders | T4 (mixed-size words), M3 (validator checks) | after M-R2 (cluster-gated) |
| Paragraph reconstruction | M2, M4 | Phase 3 WP1 (gated) |
| HTML/CSS generation | H1, H2, H3 | M-R4 |
| Viewer / Frontend / Workspace | F1–F6 | M-R6 |
| Performance / large docs | F2, §4 table, H6 | M-R7 |
| Tables / MathML / RTL / vertical / SVG(E2) / a11y | — | Phase 3+ (gated) |

## 7. Priorities

- **P0 (rendering corruption / char loss / reading order / broken fonts):**
  **none currently open.** Char loss = 0 enforced; fonts resolve 100% on
  measured docs; reading order untested on multi-column (will surface via
  corpus → then becomes P0). P0s from the corpus preempt everything.
- **P1 (typography):** M-R2, M-R3, then M-R4. Issue 003 joins M-R2's cluster
  work only if the corpus shows the mixed-size-word pattern in >1 document.
- **P2 (viewer/workspace/compare/validation UI):** M-R6.
- **P3 (performance/memory/large docs/assets):** M-R7.
- Measurement milestones M-R0/M-R1 are priority-zero *enablers* — they gate
  everything because they define truth.

## 8. Testing + Regression Strategy

Five tiers, from cheapest to most authoritative:
1. **Unit** (pytest, per module) — every bug fix lands with a failing-first
   test; systemic tests preferred over point tests (e.g. the scorecard↔
   classifier consistency test pattern).
2. **Golden corpus baselines** (`golden-corpus/manifest.json`) — per-file
   bands on escalation/confidence/geometry score, updated only deliberately.
3. **RVF corpus runs** — per-category aggregates + cluster list + regression
   detection vs baseline; CI-facing exit codes. **Cluster rule:** a fix is
   accepted only if its target cluster shrinks with statistical significance
   (≥3 documents or ≥20% of a category) and no other cluster grows.
4. **Browser oracle** (M-R5) — geometry ground truth.
5. **Pixel regression** (M-R5) — perceptual ground truth, heatmaps.

Every issue keeps the RVF lifecycle (deterministic id, severity, stage,
regression_test, fixed_in) — the backlog lives in `ROAD_TO_PHASE4.md` +
`issues.json` artifacts, not in heads.

## 9. Exit Gates (before Phase 3 / Document Intelligence)

Per the external review, all of the following on **≥100 PDFs across all
categories**:
- 0 × P0, 0 × P1 open
- Character loss = 0; unexpected font substitutions = 0
- Rendering Fidelity (pixel diff, M-R5) > 99%
- Avg glyph escalation < 10% (per category, not just corpus mean)
- Geometry metrics stable across categories (no category >2× corpus median)
- No recurring cluster affecting multiple document types

## Phase R-1 — Rich IDM Renderer Migration *(user-ordered 2026-07-12, preempts M-R2.5/M-R3)*

Field evidence (real converted book): the viewer's HTML was still the legacy
word-pinned renderer — `use_rich_tree=False`, `pages_semantic/` unrouted, so
NO backend improvement was ever visible. Additionally the word-span builder
had a **quote-escaping bug**: font-family stacks contain `"` inside a
double-quoted `style` attribute, so the browser truncated the style at the
first inner quote — **font-family, font-size, and letter-spacing were
silently dropped from every word span** (root cause of the garbled overlay).

Change (renderer files only; extraction/typography/reconstruction/validator/
quality untouched): `TextRenderer` now consumes the **Rich IDM Run Builder**:
positioned `<p>` per line (baseline placement measured exact), browser lays
out text inside; base run = plain text styled by the paragraph; `<span
class="lf-run">` ONLY on genuine style change; letter-spacing applied across
whole runs; all attribute values escaped; `lf-word`, per-word `left:`, and
`data-word-pinned` deleted. CSS: `font-kerning:none; font-variant-ligatures:
none` on text blocks (matches the measurement model; M-R2.4 proved served
fonts carry no GPOS/GSUB anyway). Known trade: word starts are no longer
pinned — M-R2 measurements (~0.16px/word median) say drift stays sub-pixel;
verified on the corpus, monitored by the fidelity gate.

## 10. Implementation Order (approval-gated, one at a time)

```
M-R0   Benchmark & Certification Platform   [platform now; real signal needs user's PDFs]
M-R1   Visual Geometry Score + score hierarchy + Extraction Accuracy
M-R2   advance-based typography measurement  ← biggest fidelity payoff
M-R2.5 Font Intelligence (font knowledge database)
M-R3   kerning/ligature policy
(corpus re-run: verify clusters shrink; recalibrate targets — gate before any renderer work)
M-R6a  compare view (semantic vs legacy in the workspace)
M-R4   semantic fixed-layout + default flip + legacy retirement
M-R5   browser oracle + pixel regression
M-R6b  remaining frontend (Rich IDM surface, quality UI, design review)
M-R7   large-document scaling
M-R8   image reconstruction + publishing-grade assets
→ Exit gates (§9) → Phase 3 Document Intelligence (reading-order-first)
```

**Approved 2026-07-12 with the amendments recorded in the header.
Implementation proceeds milestone-by-milestone; each milestone closes only on
corpus-level statistical evidence per the binding rule.**
