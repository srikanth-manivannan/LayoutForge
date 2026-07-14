# Road to Phase 4 — Validation / Reality Check

**Status:** Open · started 2026-07-10

Phase 3 is **complete**: the Rich IDM is the canonical model, the compiler-style
writer architecture and semantic HTML writer ship behind a feature flag, and
[RVF](../backend/tools/rvf/README.md) is permanent validation infrastructure.

This phase adds **no features and no abstractions.** The architecture is frozen.
The only work is proving it against reality:

```
Corpus → RVF → find reality → fix the EARLIEST incorrect stage → regression test → repeat
```

Phase 4 (delete the legacy writer) begins only when the exit targets below hold
across a real, diverse corpus.

## Exit targets (quality, not implementation)

| Metric | Target |
|---|---|
| Unicode fidelity | ≥ 99.99% |
| Character loss | 0 |
| Semantic parity (HTML ↔ IDM tree) | 100% |
| Pipeline failures | < 1% |
| CSS-rule growth | stable |
| Span reduction | stable |
| Regression count | 0 |

## Two rules — enforced

1. **Never patch the renderer first.** For every bug, walk the pipeline and fix
   the *earliest* stage that is actually wrong:
   `Extraction → Typography → Rich IDM → Semantic Tree → Writer → HTML`.
   If the writer would have to repair the model, the bug is upstream.
2. **Every bug becomes a regression test before it is fixed.** Capture the
   offending PDF (or a minimal repro) as a test, watch it fail, then fix. A bug
   is never fixed without being captured forever.

## How to run

```powershell
# from backend/
./.venv/Scripts/python.exe -m tools.rvf "E:\Corpus" --out rvf_report --baseline rvf_baseline.json
```

Open `rvf_report/index.html`; `FAIL` rows and low scores become entries below.

## Reality backlog

Each failing or low-scoring corpus document is one line. This is the engineering
backlog — reality, not guesses.

| ID | Document type | Symptom | Suspect stage | Regression test | Status |
|----|---------------|---------|---------------|-----------------|--------|
| 001 | Children's book (Jim Benton) | `word_crosses_run_boundary` ×10: PyMuPDF word `Times` lands in run `New York Time`; `Tot␣theToad` spans 3 runs | **Word Builder** — `WordBox` came straight from PyMuPDF `get_text("words")` | `test_word_builder::test_word_spanning_two_runs_becomes_fragments_not_a_split` | **Fixed** (Phase 2.6) |
| 001a | (same) | `JIM`/`BENTON` attached to the blank ` ` run | **Run Builder** — `_attach_words` ignored size | `test_word_builder::test_mixed_size_word_is_one_word_multiple_fragments` | **Fixed** (Phase 2.6, `_attach_words` removed) |
| 001b | (same) | `New York Time`(italic) + `s Bestselling author`(regular) split mid-word — real authored style or PyMuPDF mis-attribution? | **Extraction** (font attribution) — the word is now correctly modelled as fragments regardless; only the *visual* italic/regular boundary remains to confirm vs the source PDF | TBD | Investigate |
| 002A | Children's book (proj 08faa71f) | Escalation tolerance `WORD_TOLERANCE_PX = 0.3px` is *absolute per word*. First hypothesis (accumulated per-glyph noise, scales with glyph count) was WRONG — measured: the residual is a near-CONSTANT ~2px regardless of word length (1–13 glyphs), the signature of a measurement-DEFINITION gap: `word.width` is PyMuPDF's ink bounding box, `natural_text_width` is our pen-advance sum — a word's last glyph overhangs its own advance by a roughly constant amount per font/size | **Adaptive Reconstruction Engine** — tolerance must reflect the real bbox-vs-advance gap, not scale with glyph count | `test_typography_reconstruction_v1` (tolerance shape); `test_reconstruction_diagnostics`/`test_adaptive_precision` (recalibrated) | **Fixed** — `word_tolerance_px()` = 2.0px floor + 0.08px/glyph, calibrated from measured percentiles |
| 002B | (same) | Genuine `Tc` tracking on ~21% of *display* spans (median ~1.9px/glyph, 2.57 on the title) was un-extracted, so the engine "fixed" it with per-word letter-spacing instead of recognizing it as real typography | **Extraction/Typography Analyzer** — Tc effect not measured. First matching approach (per-line, y-baseline-only) failed almost entirely (3.7% match rate) — `get_texttrace()` spans are NOT one per visual line; same-style consecutive lines merge into one span with no separator. Fixed by page-level substring matching (flatten to one char stream, locate each line's text, anchored by baseline y) | **Extraction/Typography Analyzer** — Tc effect not measured; then a matching-algorithm bug | `test_character_spacing` (matching + estimator + the multi-line-span regression case) | **Fixed** — `typography/character_spacing.py`, consumed by `decide_word` |

**Measured result on the reference document (both fixes together):**
glyph escalation **73.7% → 24.35%** (>3× reduction), mean confidence **0.861 →
0.921**, mean width error **4.98px → 1.85px**. Target (<10% escalation,
>0.99 confidence, <0.25px width error) **not yet met** — the gate correctly
reports `overall_pass=False`; this is honest, not a regression. Remaining
253 escalations are explained, not mysterious: natural per-word variance
around each span's median tracking estimate (small, plausible residuals,
confidence 0.85–0.87 — correctly reconstructed, just no longer "free");
legitimate kerning/ligature cases; and issue 003 below.

| 003 | (same) | `Tot theToad` (+128px, +102px width error) — a single lexical word spans THREE runs at wildly different font sizes (115/60/115px) | **Word Builder / display typography** — a genuine mixed-size lexical word, unrelated to Tc/tolerance; needs its own investigation (drop-cap-like or decorative-text pattern) | TBD | Open |
| 004 | Same PDF, first run through `golden-corpus/` (real corpus workflow) | `mean_width_error_px` scorecard failure classified as **P1/release-blocking** (`category=Quality, stage=unknown`) instead of joining its Rendering-fidelity siblings at P2 | **RVF issue classifier itself** (`tools/rvf/issues.py`) — the metric was added to the quality scorecard's `_TARGETS` but never registered in `_SCORECARD_META`, so it silently fell through to the generic default | `test_every_scorecard_metric_has_an_explicit_classification` (systemic — catches this class of bug for any future metric), `test_width_error_classifies_with_its_rendering_fidelity_siblings` | **Fixed** |
| 005 | Same PDF, cover page, ChauncyPro-Bold ("Makes"/"Mess") | Extracted web font's `cmap` maps `s` (U+0073) to glyph `s.salt` (gid 320, advance 11.70px) — but the PDF's own content stream uses TWO different glyphs for `s` at different positions: standard `s` (gid 84, advance 13.52px) for 2 of 3 occurrences, `s.salt` only for the 3rd (a deliberate InDesign "avoid duplicate glyph" stylistic-alternate substitution, confirmed via `get_texttrace()` per-glyph-id comparison against the original PDF-embedded font). A single cmap entry can't represent per-occurrence glyph choice; extraction picked the alternate, silently wrong for the other two — each short by 1.82px. Confirmed NOT a browser/shaping issue: HarfBuzz, Canvas `measureText()`, and the live DOM all agree with each other and with the (wrong) cmap choice; `hmtx` is otherwise byte-identical between the original embedded font and the extracted copy | **Extraction** — `_reconcile_cmap_from_usage()` in `extract_fonts.py` collected texttrace usage into a plain `dict[codepoint] = glyph_id`, so a codepoint seen with two different glyph ids across a document silently kept whichever was processed LAST, regardless of which was actually used more | `test_reconcile_cmap_picks_the_majority_glyph_not_the_last_seen`, `test_reconcile_cmap_picks_the_alternate_when_it_is_the_majority` | **Fixed** — usage is now `dict[codepoint] -> Counter[glyph_id]`; the cmap keeps the MAJORITY glyph per codepoint. Verified on the real book: `s` in "Mess" now advances 13.52px (correct standard glyph) instead of 11.70px (wrong alternate) |
| 006 | Same PDF, cover page (KGDancingontheRooftop `Tot`/`Toad`; ChauncyPro-Bold `k`→`e` in "Makes") | PDF content stream applies real, non-uniform per-glyph-pair `TJ`-array positioning (optical kerning) that compresses glyph advances below the font's own nominal `hmtx` metrics — up to 17px cumulative drift over 4 glyphs for `Tot theToad`. Confirmed present in BOTH fonts checked; neither font has `GPOS`/`kern` tables, so this data exists ONLY in the content stream, not recoverable from the font file. Current Run/Word-level (Unicode-text) reconstruction has no field for per-glyph-pair position deltas — only a single per-run `letter_spacing` scalar, the wrong shape for non-uniform pair data | **Extraction/Reconstruction** — a missing capability (no stage reads `TJ`-array per-glyph offsets at all), not a broken existing behavior | TBD | **Open — deferred (GLYPH mode / M2).** Store-only when implemented: capture the measurement in the Rich IDM so a future glyph-level compiler can consume it; do not build glyph rendering yet |

**Rendering-fidelity gate added (2026-07-11).** The quality scorecard now
includes `glyph_escalation_rate` (≤0.15) and `mean_reconstruction_confidence`
(≥0.95), plus `rendering.mean_width_error_px`. A model can conserve 100% of
characters yet render poorly; the gate used to report PASS on doc 002, now
FAILs it. Pixel-level rendering metrics (baseline / line-height / paragraph-
width / overlay error) require the visual layer (Playwright, greenlit).

**Phase 2.6 — Lexical Reconstruction (done).** Words are reconstructed from the
run stream (`word_builder.py`); PyMuPDF words are geometry hints only. A word
never crosses a run boundary as a unit — a mixed-style word (`Times`, `theToad`)
is ordered `WordFragment`s referencing runs. Words moved off `Run` onto `Line`;
`Run.words` removed (single source of truth). Validator (Phase 2.5) went from
**10 errors → 0** on doc 001 and now gates the semantic writer
(`strict=use_rich_tree`). New validator checks: `word_fragment_mismatch`,
`fragment_foreign_run`, `fragment_text_not_in_run`, `word_without_run`,
`run_without_word`.

<!-- Add real rows as the corpus surfaces them. Keep IDs stable; they are
     referenced by regression tests and RVF report notes. -->

## Adopted roadmap (measured-quality first, 2026-07-11)

Reconstruction features are frozen; the focus is measured quality until the
scorecard is consistently green on a real corpus.

- **Phase 2.5 — Rich IDM Validator** ✅
- **Phase 2.6 — Lexical Reconstruction** ✅
- **Phase 2.7 — Measured Quality** ✅ per-stage conservation ledger
  (Expected/Observed/Delta/Confidence) + release scorecard in
  `document.quality` → `report.json` + RVF. Real book: every stage 100%,
  scorecard all PASS.
- **Phase 2.7b — Reality corpus** — run RVF over 500–1000 real PDFs by
  category (publishing / government / education / business / engineering /
  accessibility / international); every issue → backlog row → earliest-stage
  fix → regression test. *(Needs the user's corpus.)*
- **Phase 2.8 — Asset optimization** — 400k-px working copy (original kept
  lossless), font optimization, asset dedup (LFS §7a).
- **Phase 2.9 — Legacy retirement** — remove `TextBlock.spans`/`text_blocks`;
  Rich IDM becomes the only model the renderer consumes.
- **Phase 3 — Document Intelligence** (renamed from Semantic Reconstruction):
  WP1 paragraphs · WP2 lists · WP3 headings · WP4 reading order · WP5 captions ·
  WP6 footnotes · WP7 tables · WP8 math · WP9 accessibility · WP10 editing.
- **Phase 4+** — output formats: HTML/XHTML/EPUB/XML/PML.

**Core v1 architecture is declared complete and frozen** (ADR-009). From here,
effort goes to reality validation and earliest-stage fixes — not new
architecture — until the scorecard is consistently green on a diverse corpus.

## Milestone: Rendering Accuracy v1 (current focus)

Architecture quality ≠ output quality. This milestone closes the gap, driven by
evidence (diagnose → fix earliest stage → measure). Renamed from "fix the
measurement engine": once diagnosed, the defects were reconstruction
DECISIONS (a threshold, a missing typography operator), not the measurement
itself — so this is **Typography Reconstruction v1**.

**Guiding rule (added to LFS in spirit, enforced in code):** *The Adaptive
Reconstruction Engine must never compensate for missing document semantics.
If a PDF text-state operator (Tc, Tw, Tz, TL, Tr, Ts) has a measurable effect,
it must be reconstructed explicitly — as real typography on the model — before
any adaptive escalation is considered.*

1. **Honest rendering-fidelity gate** ✅ (glyph escalation + confidence + width
   error in the scorecard; doc 002 failed on introduction).
2. **Typography Measurement Diagnostic** ✅ (`typography_diagnostic.py`,
   per-doc `typography.json`, causes ok/tracking/scaling/kerning/metrics/
   **unknown** — never forced into a wrong bucket). Overturned the "font
   metrics broken" guess: metrics are fine; two independent causes found.
3. **Issue 002A — Adaptive Threshold** ✅ `word_tolerance_px()` — calibrated
   from measured data to a ~2px floor (the bbox-vs-advance definitional gap)
   + a mild 0.08px/glyph term, replacing the flat 0.3px constant.
4. **Issue 002B — Typography Operator Reconstruction** ✅ `character_spacing.py`
   measures genuine `Tc` from actual PDF glyph advances (`get_texttrace`,
   matched at PAGE granularity by locating each line as a substring of the
   page's flattened glyph stream, anchored by baseline y — any ambiguity
   bails out rather than guessing) and writes it to `TextSpan.letter_spacing`
   → `Run.letter_spacing`: real document typography, consumed by the Adaptive
   Reconstruction Engine as a known input, not re-derived from residual error.
   `Tw`/`Tz`/`Ts` fields reserved on `Run` (not yet extracted — no corpus
   evidence yet that they matter). **Measured result:** glyph escalation
   73.7% → 24.35%, mean confidence 0.861 → 0.921, mean width error 4.98px →
   1.85px — real progress, target not yet met (see issue 002A/002B row above
   and issue 003). The gate correctly reports FAIL; iterate before declaring
   this step done.
5. **Browser Measurement Oracle** (Playwright, dev/CI, not yet built): load
   HTML in headless Chromium, measure each run's `getBoundingClientRect()` +
   computed font/letter-spacing/line-height, compare to PDF geometry —
   independent ground truth for the measurement engine.
6. **Make the semantic run-based renderer the default** once rendering fidelity
   is green (it already emits runs; gated behind `use_rich_tree`, kept there
   until the corpus proves it — evidence first).
7. **Playwright pixel regression** — final visual verification.

### Success criteria (measurable)

| Metric | Target |
|---|---|
| Glyph escalation rate | < 10% |
| Mean reconstruction confidence | > 0.99 |
| Mean width error | < 0.25 px |
| Diagnostic `unknown` fraction | < 1% |
| Rendering fidelity (scorecard) | PASS |
| Visual regression (Playwright) | PASS |

Exit: HTML needs zero corrective styling beyond model-derived positioning.
