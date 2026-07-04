# USER_WORKFLOW — The Real Production Journey

Every design decision must serve this loop. This is what a production
operator does all day, on deadline, for dozens of titles per week.

```
Customer sends PDF
      ↓
Import PDF               (Dashboard / Import)
      ↓
Extract                  (automatic pipeline: fonts, images, text, backgrounds → IDM)
      ↓
Generate HTML            (automatic: per-page HTML + shared/per-page CSS)
      ↓
Proof                    (Viewer + Compare: reconstructed page vs. source page)
      ↓
Fix layout               (Phase 3 editing: nudge, resize, restyle, replace font)
      ↓
Validate                 (Validation panel: automated layout/asset/link checks)
      ↓
Accessibility            (Phase 5: reading order, alt text, tagging, a11y report)
      ↓
Export EPUB              (Phase 4: reflowable / fixed-layout, plus HTML/ZIP today)
      ↓
Deliver                  (download package / push to customer)
```

## The critical insight

The loop is not linear — **Proof → Fix → Validate is a cycle** an operator
runs many times per title. The workspace must make that inner loop nearly
free: switching between Viewer, Compare, and Validation is a tab click
inside one workspace, never a page navigation that loses context.

## Workflow states of a project

`Imported → Processing → Ready → In Proofing → In Correction → Validated →
Accessible → Exported → Delivered`

(Today the backend tracks `Imported/Processing/Ready/Failed`; the later
production states arrive with the phases that give them meaning.)

## Time budget (target for a trained operator)

| Step | Today (desktop tools) | LayoutForge target |
|---|---|---|
| Import + extract | manual, minutes–hours | < 2 min automated |
| Proof 27-page book | ~1–2 hours manual | < 15 min with Compare + Validation |
| Fix layout issues | round-trip to desktop app | in-browser, seconds per fix |
| Validate | manual eyeballing | automated, seconds |
| Export | manual assembly | one command |
