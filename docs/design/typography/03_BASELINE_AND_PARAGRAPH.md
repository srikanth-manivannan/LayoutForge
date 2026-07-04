# 03 — Baseline & Paragraph Reconstruction (Deliverables 2 & 3)

## Baseline Reconstruction Engine (Deliverable 2)

Stop describing a line as `{top, left}`. Describe it as the typographer
does:

```
baseline_y     — the y the glyphs sit on (PyMuPDF span origin.y; exact)
ascent         — font ascent × size (from Font Metrics Engine)
descent        — font descent × size
leading        — baseline-to-baseline distance to the next line
line_index     — position within the paragraph
```

**Why baseline, not top:** the earlier page-26 bug was baseline mismatch
(font metrics vs computed line-height disagreed). Anchoring on the measured
baseline and deriving the box from real ascent/descent removes an entire
class of vertical drift. The shipped baseline fix (bare-CFF metrics from
MuPDF) is the seed of this engine.

### Baseline grid

Within a paragraph, lines are near-equidistant. The engine computes the
**modal baseline delta** (leading) and snaps lines to a grid, so:

- a single dropped/rotated line can't skew the whole paragraph,
- reflowable output (EPUB) gets a real `line-height`, not per-line hacks,
- validation can flag any line off its grid (baseline-drift check, 08).

### Rendering (fixed-layout)

Paragraph container positioned by its first baseline; each line placed by
`baseline_y − ascent` (top of its box); words/glyphs pinned within. This
generalizes the current rotated-text baseline-origin fix to all text.

## Paragraph Reconstruction Algorithm (Deliverable 3)

Goal: recover paragraphs from positioned lines so output is
`<p><span>…</span></p>`, not one absolutely-placed `<p>` per line.

### Signals (all measured, none hardcoded thresholds baked in — derived
per document from its own statistics)

1. **Vertical rhythm** — consecutive lines within ~1 leading, same region.
2. **X-alignment** — shared left edge (body), or shared justification.
3. **First-line indent** — a line starting one em-ish right of the block
   left signals a *new* paragraph (or hanging indent — detect sign).
4. **Font continuity** — same dominant run style across lines.
5. **Short last line** — a line ending well short of the right margin ends
   a paragraph.
6. **Vertical gap** — a gap > modal leading × factor separates paragraphs.
7. **Drop cap / heading** — outsized first run → its own block with a
   heading/`role`.

### Algorithm

```
per region (reading order):
  compute doc-relative stats: modal leading, body left x, right margin,
    body font size (mode of run sizes)
  seed paragraph with line[0]
  for each subsequent line:
    if same region and vertical_delta ≈ leading and not new_indent(line)
       and font_continuous(line):
        append to current paragraph
    else:
        close paragraph; classify (heading/body/list-item via role rules);
        start new paragraph
  post: detect alignment (left/right/center/justified) from line edge
        variance; set first_line_indent, space_before/after from gaps
```

### Output altitude (the safety rule)

- **Reflowable (EPUB/XHTML):** emit `<p>` + `<span>` runs; let the browser
  wrap. Positions dropped; baseline grid → `line-height`; indents/spacing
  → CSS. This is where paragraph reconstruction pays off structurally.
- **Fixed-layout (proofing):** keep per-line placement but *inside* the
  paragraph container, with words/glyphs pinned (M1 today, M2 glyphs).
  Paragraph grouping still improves selection, accessibility, and export.

### Confidence & fallback

Each paragraph carries a `confidence`. Below threshold (dense math,
tabular text, unusual layout) the block falls back to line-level fixed
placement — never a *wrong* paragraph. Confidence is a reconstruction
signal, not fabricated UI data (consistent with the no-fake-confidence
Properties rule; it drives fallback, and may surface in Validation).
