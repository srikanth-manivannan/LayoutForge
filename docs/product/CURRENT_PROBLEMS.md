# CURRENT_PROBLEMS — Pain Points LayoutForge Exists to Kill

The problems production teams live with today, using desktop conversion
tools (Able2Extract, APZ Editor, ad-hoc scripts):

1. **Manual proofing takes hours.** Operators compare source and output page
   by page, by eye, with two windows side by side.
2. **Text alignment issues.** Converted output drifts from the source —
   baseline, kerning, line-height mismatches — and there is no systematic way
   to find them.
3. **Missing fonts.** Embedded PDF font subsets fail silently in browsers;
   output renders in fallback fonts with wrong metrics. (LayoutForge already
   solves the hardest case: fontTools re-sanitization in `ExtractFontsStage`.)
4. **No browser solution.** Everything competitive is desktop-only,
   Windows-only, single-machine, license-locked.
5. **Desktop software only** → no collaboration, no central storage, no
   remote work, IT-managed installs.
6. **Poor validation.** No automated checks; QA is human attention.
7. **No accessibility support.** A11y remediation happens in a separate tool
   (or not at all), long after conversion, when fixes are most expensive.
8. **Complex workflows.** Each title bounces across 3–5 tools: converter,
   editor, validator, EPUB packager, a11y checker.
9. **Difficult collaboration.** Files emailed around; no shared project
   state; no audit trail of what was fixed and by whom.

## Design consequences

- Compare (source vs. output) must be a first-class panel, not a debug view.
- Validation must be automated, incremental, and always one click away.
- Everything lives in one browser workspace — no tool-hopping.
- Project state is server-side from day one (already true: `storage/projects/{id}`).
- Accessibility is a pipeline stage, not an afterthought bolted on at export.
