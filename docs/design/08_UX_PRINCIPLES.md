# 08 — UX Principles

The product-level constitution lives in
[../product/PRODUCT_PRINCIPLES.md](../product/PRODUCT_PRINCIPLES.md)
(15 principles, ratified 2026-07-02, with **Production Accuracy First**
as the non-negotiable Principle 0). The ten below are the UX layer of
that constitution. Each has a test — if a design can't pass the test, it
violates the principle.

1. **The document is the hero.**
   *Test:* on a 1440×900 screen with default docks, the page canvas gets
   ≥ 55% of the width; with docks collapsed (Ctrl+B/Ctrl+J), ≥ 85%.

2. **The inner loop is sacred.** Proof → Fix → Validate must cost one
   keystroke per leg and never lose page/zoom/selection.
   *Test:* switch Viewer→Compare→Validation→Viewer; you are still on page
   12 at 150% with the same object selected.

3. **Never block, never lie.** No modal spinners; progress is real
   (stage-level), errors are specific and actionable, placeholders admit
   what's unbuilt, data is never fabricated.
   *Test:* kill the backend mid-session — every failure surface names the
   problem and a next step (the PreviewError pattern).

4. **Keyboard-first, mouse-complete.** Every command has a palette entry;
   the frequent ones have shortcuts; everything is also clickable.
   *Test:* run the whole demo script in SAMPLE_PROJECT.md without the mouse
   (except canvas clicks).

5. **One vocabulary.** Status names, icons, and colors for a concept are
   identical on every surface.
   *Test:* grep the UI for "Complete|Done|Finished" — only one appears.

6. **Scale is invisible.** A 2,000-page book feels like a 27-page book.
   *Test:* page-nav latency and memory are flat as page count grows
   (windowing, virtualization, incremental everything).

7. **State is where you left it.** Layout sizes, active tab, page, zoom,
   theme survive reload and navigation.
   *Test:* F5 in the workspace returns you to the same visual state.

8. **Selection is the universal pointer.** Click anything anywhere
   (canvas, finding row, tree, search hit) → the same SelectionChanged
   event → Properties, canvas highlight, and future editing all agree.
   *Test:* there is exactly one selection code path (viewer `Selection`).

9. **Progressive disclosure, professional depth.** Defaults are clean;
   depth (Advanced property group, log streams, debug panels) is one
   deliberate step away, never removed.
   *Test:* a new operator is productive in 10 minutes; Priya never feels
   capped.

10. **Extensible by design, not by exception.** New capabilities arrive as
    commands + panels + events + plugins.
    *Test:* describe the feature as {commands it registers, panel it
    mounts, events it consumes/emits}. If you can't, redesign it.
