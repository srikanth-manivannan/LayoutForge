# LayoutForge Studio — Product Vision

## Vision

LayoutForge Studio is an enterprise-grade **Digital Publishing Production
Platform** delivered in the browser.

It replaces traditional desktop publishing production tools (Able2Extract,
APZ Editor, and similar conversion utilities) with a complete browser-based
production workspace: import complex PDFs, convert them into
production-ready publishing formats with pixel-level layout fidelity, then
proof, fix, validate, make accessible, and export — all in one place.

**It is not a converter. It is a publishing workspace.** Conversion is the
first step of a production line, not the product.

## Definition (canonical, 2026-07-04)

> LayoutForge Studio is a **document reconstruction platform** that
> transforms fixed-layout documents into production-ready structured
> publishing assets while preserving visual fidelity.

Everything built supports that sentence. It is not a PDF→HTML converter, not
an EPUB editor, not "publishing software" — it is a reconstruction platform
whose output happens to be any of those. See
[PRODUCT_PILLARS.md](PRODUCT_PILLARS.md) for the seven pillars every feature
maps to, and [../CORE_v1.0.md](../CORE_v1.0.md) for the frozen platform.

## One-sentence positioning

> The future Adobe InDesign for digital publishing *production* — where the
> source is a finished PDF and the deliverable is a validated, accessible,
> pixel-accurate digital publication.

## Target users

- Publishing companies (books, magazines, education, government)
- Digital publishing / EPUB production teams
- Accessibility specialists (WCAG / EPUB Accessibility remediation)
- Educational publishers (textbooks, workbooks, fixed-layout)
- Magazine publishers (image-heavy, complex layout)
- Government document teams (compliance, archival, Section 508)

## Primary goals

1. **Pixel-perfect conversion** — the reconstructed page is indistinguishable
   from the source PDF.
2. **Fast production workflow** — a trained operator processes a book in
   minutes, not hours.
3. **Proofing** — side-by-side and overlay comparison against the source is a
   first-class tool, not an afterthought.
4. **Validation** — automated checks replace manual page-by-page inspection.
5. **Editing** — fix layout problems in the browser (Phase 3).
6. **Accessibility** — reading order, alt text, semantic tagging, WCAG/EPUB
   a11y conformance (Phase 5).
7. **Export** — HTML today; EPUB (reflowable + fixed-layout) and other
   publishing formats next (Phase 4).
8. **Automation** — batch processing, watch folders, API-driven pipelines
   (Phase 7).

## Markets (one engine, four buyers)

The same reconstruction engine serves distinct markets *because it
reconstructs documents rather than converting formats*:

1. **Publishing houses** — books, magazines, educational content.
2. **Accessibility remediation teams** — reading order, tagging, WCAG/EPUB-a11y.
3. **Government & legal** — long-form, structured, compliance-bound documents.
4. **Academic publishers** — tables, MathML, multilingual/RTL.

## Not Able2Extract anymore

The original reference point was a PDF-extraction tool (Able2Extract, APZ
Editor). The architecture has outgrown that category. LayoutForge is a
reconstruction engine that can power HTML generation, EPUB production,
XML/PML publishing, accessibility workflows, visual editing, and
AI-assisted document understanding — a broader and more defensible position
than "PDF extraction."

## Long-term goal

Become **the** production platform for digital publishing — the tool a
publishing production floor keeps open all day.

## What already exists

Phase 1 (conversion engine: PDF → IDM → pixel-accurate HTML/CSS) and Phase
2A (production workspace shell: command system, event bus, Document Manager,
dockable panels, IDE-style explorer) are built and verified. See
[../ARCHITECTURE.md](../ARCHITECTURE.md) and the top-level README. All
product design must build on those seams, not around them.
