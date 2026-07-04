# Product Pillars

Permanent. **Every future feature belongs to exactly one pillar.** If a
proposed feature fits none, it doesn't belong in LayoutForge; if it fits
several, split it. The pillars are the durable structure beneath the
changing roadmap.

| # | Pillar | Question it answers | Status |
|---|---|---|---|
| 1 | **Reconstruction** | *Understand the document* — what's on the page? | ✅ Core v1.0 (extraction → Rich IDM) |
| 2 | **Accuracy** | *Reproduce the document* — pixel-faithful to the source | ✅ Core v1.0 (Adaptive Reconstruction; M2 closes the last mile) |
| 3 | **Semantics** | *Understand meaning* — paragraphs, tables, reading order | ← Phase 3 (the heart of the product) |
| 4 | **Editing** | *Allow correction* — fix what reconstruction got wrong | Phase 3+ (rides the one selection pipeline) |
| 5 | **Publishing** | *Export* — HTML/XHTML/EPUB/XML/PML from one model | after Semantics (thin writers, ADR-005) |
| 6 | **Accessibility** | *Improve* — reading order, alt text, WCAG/EPUB-a11y | after Semantics (built on structure) |
| 7 | **Automation** | *AI* — understand, detect, repair, suggest | continuous, atop Semantics |

## How the pillars relate

Pillars 1–2 are **frozen Core v1.0**. Pillar 3 (Semantics) is the pivot:
once the Rich IDM carries meaning, pillars 5–7 largely fall out of it —
**one investment (a Paragraph, a Table), many products** (HTML, EPUB, XML,
accessibility, editing, search, AI). That is why Phase 3 is where the next
several months go.

## Where AI actually adds value (Pillar 7)

Not "fix CSS." Real value is **document understanding**: identify heading
hierarchy, detect captions, repair tables, recognize math, improve reading
order, suggest semantic tags. AI operates *on the Rich IDM through
capabilities* (ADR-007) — every suggestion is reviewable and undoable
(honest-UI rule), never auto-applied.

## Feature intake rule

For any new feature, state: **which pillar** · **which capability**
(ADR-007) · **which LFS section** it reads/writes · **which Quality-Gate
targets** it must not regress. If those four can't be named, the feature
isn't ready.
