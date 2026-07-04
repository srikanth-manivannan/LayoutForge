# 01 — User Personas

Four personas, in priority order. The Workspace is designed for Priya; the
platform is bought because of Marcus; Phases 5 and 7 exist for Elena and
David.

---

## P1 · Priya — Production Operator (primary)

**Who:** 26, digital production artist at a mid-size educational publisher.
Converts 10–20 titles a week. Power user of Acrobat and a desktop
conversion tool she resents. Two monitors, keyboard-driven, on deadline.

**Goals**
- Get a title from "PDF received" to "delivered" as fast as possible
- Trust the output without eyeballing every page
- Fix the three pages that always break without leaving the tool

**Frustrations today**
- Manual side-by-side proofing (hours per title)
- Silent font substitution she discovers only when the customer complains
- Tool-hopping: converter → editor → validator → packager

**What she needs from LayoutForge**
- The Proof → Fix → Validate inner loop as tab switches, all keyboard-driven
- Compare overlay that makes a 2px drift instantly visible
- Validation that tells her *which* pages to look at, so she skips the rest

**Success metric:** proofs a 27-page book in < 15 minutes, confidently.

---

## P2 · Marcus — Production Manager (economic buyer)

**Who:** 45, runs a 6-person production team. Answers for deadlines,
quality escapes, and tooling costs. Doesn't operate daily, but opens the
Dashboard every morning.

**Goals**
- Throughput visibility: what's in flight, what's stuck, what shipped
- Fewer quality escapes reaching customers
- One browser tool instead of five desktop licenses per seat

**What he needs from LayoutForge**
- Dashboard that answers "are we on track?" in five seconds
- Validation/accessibility reports he can attach to a delivery
- (Phase 7) queues, assignments, and audit trail

**Success metric:** team throughput up, rework rate down, license spend down.

---

## P3 · Elena — Accessibility Specialist

**Who:** 33, WCAG/EPUB-a11y expert, remediates titles for education and
government clients. Today she works *after* production in separate tools,
where fixes are most expensive.

**Goals**
- Correct reading order, alt text, and semantic structure on every title
- Conformance reports (WCAG 2.1 AA / EPUB Accessibility 1.1) as deliverables

**What she needs from LayoutForge (Phase 5)**
- Reading-order overlay in the same Viewer Priya uses
- Alt-text workflow with (Phase 6) AI drafts she reviews, never auto-ships
- A11y validation integrated with the same Validation panel

**Success metric:** remediation happens inside production, not after it.

---

## P4 · David — Publishing Technology Lead (technical buyer)

**Who:** 39, owns publishing infrastructure at a large publisher. Evaluates
platforms for API, automation, security, and longevity.

**Goals**
- Automate conversion via API/watch folders (Phase 7)
- Extend the platform (custom exporters/validators via plugins)
- Self-host or control storage; audit everything

**What he needs from LayoutForge**
- Clean API surface (already: FastAPI, typed schemas)
- Plugin extension points that are real, not marketing
- Predictable performance on 1,000-page documents

**Success metric:** LayoutForge becomes infrastructure he builds on.

---

## Persona → design priorities

| Decision | Serves |
|---|---|
| One workspace, tabbed panels, keyboard-first | Priya |
| Dashboard as production overview, not vanity metrics | Marcus |
| A11y as pipeline stage sharing Viewer/Validation | Elena |
| Commands/events/plugins as public seams | David |
