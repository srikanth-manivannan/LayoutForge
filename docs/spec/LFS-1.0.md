# LayoutForge Specification (LFS) 1.0

**Status:** Draft-Normative for the frozen core (M1–M1.7) · Reserved sections
marked per future milestone · 2026-07-04

LFS is the internal contract for LayoutForge's Rich Document Model and
reconstruction — the equivalent of the EPUB spec, but for our reconstruction
pipeline. It is the single agreement between the **Engine**, **Viewer**,
**Editor**, **Exporters/Writers**, and **Plugins/Capabilities**: each reads
and writes the model defined here and nothing implicit. Persisted form is
`idm.json`; a per-conversion `report.json` carries analytics/telemetry.

## 0. Reconstruction pipeline (normative shape)

```
Raw extraction (frozen)
   ↓  Raw IDM
Geometry Normalizer          reading order · baseline · line metrics
   ↓
Typography Analyzer          measure runs/words vs real font metrics
   ↓
Adaptive Reconstruction      cheapest level per object + ReconstructionDecision
   ↓
Document Intelligence Layer  ← §5, first-class: paragraphs · headings · lists ·
   ↓                            reading order · regions/columns · tables ·
Rich Document Model             figures/captions · footnotes · TOC/index ·
   ↓                            running heads/feet
Writers                      fixed-layout · HTML · XHTML · EPUB · XML · PML
```

The **Document Intelligence Layer** is the semantic heart (Phase 3): it turns
the geometric/typographic model into a model of *meaning*. Everything below
it (writers, accessibility, editing, AI) reads that meaning. Its detection is
confidence-gated (ADR-003) and it never alters the frozen core (ADR-009).

Conformance keywords: **MUST / SHOULD / MAY**. Anything marked *Reserved*
is not yet normative and lands with its milestone.

---

## 1. Document Model (normative)

```
Document
 └─ Page*                     number, width, height, rotation, background_image
     ├─ TextBlock*  (= Line)  bbox, origin, ascender/descender, line_height,
     │   ├─ TextSpan*         style runs: text, font_id, font_size, color
     │   └─ WordBox*          x, width, baseline_y, font_id, size, color,
     │                        letter_spacing, + ReconstructionDecision fields
     ├─ ImageElement*         bbox, asset_id, rotation, z_index  (hotspot)
     └─ ShapeElement*         bbox, kind, fill/stroke, z_index
 ├─ FontResource*             id, family, weight, style, embedded, subset, filename
 ├─ AssetResource*            id, type, path, hash, referenced_pages
 └─ reconstruction_profile    analytics (§7)

Reserved (added by milestone, ADR-001 incremental tree):
 Paragraph (M3) · Region/Column (M4) · List (M5) · Table/Row/Cell (M6) ·
 Math (M7) · Glyph (M2) · Note/Ref (M5) · SVG (future)
```

Rules:
- Every object **MUST** carry a stable `id` used as `data-object-id` in
  output — one identity, one selection pipeline (Viewer, Editor, Validation).
- Output writers **MUST** read only this model, never the source PDF
  (ADR-005). The model **MUST** be reconstructible from `idm.json` alone.
- The model **MUST** serialize forward-compatibly: unknown keys ignored,
  missing keys default (so an older `idm.json` still loads).

## 2. Typography (normative)

- **Metrics MUST be measured, never estimated** — from the embedded font
  file (fontTools) or, for base-14 standard fonts, MuPDF's built-in tables.
- **Positioning altitude:** the line container is absolutely positioned;
  inside it, words are pinned at their true x; the browser lays out within a
  word. Glyph pinning is used **only** where §4 escalation demands it.
- **Width fitting:** a word's rendered width **MUST** match its PDF box
  within tolerance, via letter-spacing (spaceless) or word-spacing
  (justified), computed from advances.
- **Baseline:** rotated text is placed by its **baseline origin**, not its
  rotated bbox. Line metrics come from the font's real ascender/descender.
- **Fonts:** every embedded font a page uses **MUST** produce a
  web-loadable file (missing = an *unexpected fallback*, a Quality-Gate
  failure); custom-encoded subsets **MUST** have their cmap reconciled from
  rendered ground truth; required sfnt tables **MUST** be synthesized if the
  subset omits them.
- **Character fidelity (ADR-010, gate 0):** no character may be lost,
  silently altered, or painted blank. A served font **MUST NOT** map a
  non-whitespace character to an empty glyph (such mappings are purged after
  the sibling-subset merge so browsers fall back visibly). Substitutions
  (fallback-font rendering) are permitted, counted, and reported
  (`fidelity` in `report.json`); `chars_lost` **MUST** equal 0 for every
  conversion. Unicode text **MUST** come from the glyph stream — never
  reconstructed from measurements (measurements position, never recover,
  characters).

## 3. Reconstruction Decision (normative — frozen contract, ADR-002)

Every reconstructed object carries a `ReconstructionDecision`:

| Field | Meaning |
|---|---|
| `mode` | WORD · RUN · GLYPH · SVG · IMAGE (the level used) |
| `reason` | none · width_error · kerning · baseline · ligature · rtl · vertical · rotation · font_subset · unknown |
| `reconstruction_confidence` | [0,1] internal engineering metric — **not user-facing** |
| `expected_width` / `actual_width` / `width_error` | measurement, px |
| `tolerance` | the threshold in force, px |

Consumers (Editor, Validation, Analytics, M2) **MUST** read this contract
and **MUST NOT** recompute their own interpretation. The decision is
immutable. Confidence names are domain-specific
(`reconstruction_confidence`, and future `ocr_confidence`,
`table_confidence`, `reading_order_confidence`) — a generic `confidence`
**MUST NOT** be introduced.

## 4. Adaptive Precision (normative — ADR-002)

Reconstruct at the **cheapest level within tolerance**; escalate only where
measurement proves it necessary; record `reason` + `reconstruction_confidence`.
A single container **MAY** mix levels. Implementations **MUST NOT** escalate
whole documents to glyph level unconditionally.

## 5. Document Intelligence Layer — Reserved (Phase 3 / M3, first-class)

*Reserved-normative (fills per M3 work package).* The semantic model of the
document — the pivot after which publishing, accessibility, editing, search,
and AI fall out. Detection is **confidence-gated** (ADR-003): a structure is
emitted only above threshold; below it, the accurate positioned objects are
kept (never a wrong structure). Nodes and their producing work package:

| Node | Produces | WP |
|---|---|---|
| Paragraph | `<p>` with baseline rhythm | WP1 |
| Heading / List | hierarchy · `<ul>/<ol>` | WP2 |
| Region / Column · reading order · running head/foot · TOC/index | correct flow | WP3 |
| Table / Row / Cell | `<table><thead><tbody>`, spans | WP4 |
| Figure / Caption | associated, placed | WP5 |
| Note / Reference | anchored, navigable | WP6 |
| Math | MathML ladder (ADR-004) | M4 |

Every node carries a stable `id` (one selection pipeline) and a
confidence/reason in the ReconstructionDecision vocabulary (§3), so editing,
validation, and AI read one contract.

## 6. Math — Reserved (M7)

*Reserved.* Fallback ladder (ADR-004): full MathML → partial MathML → SVG →
cropped raster. Malformed MathML **MUST NOT** be emitted.

## 7. Analytics & Telemetry (normative)

- `reconstruction_profile` (in `idm.json`): `words`, `by_mode`, `by_reason`,
  `glyph_fraction`, `mean_reconstruction_confidence`.
- `report.json` (per conversion): the profile + accuracy summary +
  per-stage timing and peak memory. Releases **SHOULD** be compared on this
  telemetry (e.g. kerning% over versions).

## 8. Validation — normative surface, rules grow per milestone

Validation reads the model and reports findings `{severity, category, page,
objectId, message}` via the one selection pipeline. Categories: layout,
text, fonts, assets today; structure/table/math/accessibility as their
milestones land. Confidence-gated structures report their gate outcome.

## 9. Accessibility — Reserved (Phase 5)

*Reserved.* Reading order, alt text, semantic tagging, WCAG/EPUB-a11y
conformance — built on the structure model (§5) and the one selection
pipeline.

## 10. Export / Writers (normative principle — ADR-005)

One format-neutral model; every format is a **thin writer** over it. Two
renderers share the model: fixed-layout (pixel-accurate proofing) and
semantic/reflowable. Adding a format **MUST NOT** touch the engines.

## 11. Performance (normative — Quality Gate)

- Never hold the whole document in memory on the client; windowed viewer,
  lazy `idm.json`, capped caches. 3,000+ pages **MUST** work without
  architectural change.
- Per-stage peak memory recorded; growth **SHOULD** stay < 10% over the
  recorded baseline (Quality Gate).

## Versioning

LFS is versioned independently of the app. **1.0** freezes the core
(§§1–4, 7, 10, 11) as normative. Structure/math/accessibility (§§5, 6, 9)
become normative at **1.x/2.0** as their milestones ship. Breaking changes
to a normative section require an ADR and a spec version bump.
