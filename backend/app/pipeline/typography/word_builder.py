"""Word Builder — Lexical Reconstruction (ADR-011, Phase 2.6).

Words are reconstructed from the normalized **run** stream, not copied from
PyMuPDF's `get_text("words")` (those are geometry hints only). A word is a
maximal run of non-whitespace characters across a line's runs; it is split
into ordered `WordFragment`s at run boundaries so a genuinely mixed-style word
(`theToad`, `H`+`₂`+`O`) is represented once, by reference, and never crosses a
run boundary as a single unit.

Guarantees:
- No character is lost or reordered — words index the run text, they don't copy
  or rewrite it; whitespace stays in the run text (runs are unchanged).
- `"".join(f.text for f in word.fragments) == word.text` for every word.
- Every fragment references a run present on the line.

Whitespace segmentation uses Python's Unicode-aware `str.isspace()`, so
NBSP / thin / hair / narrow-no-break / figure / ideographic spaces all
separate words correctly while remaining in the run text.
"""

import uuid

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.run import Run
from app.pipeline.elements.textbox import WordBox
from app.pipeline.elements.word import Word, WordFragment


def _fragments(token: list[tuple[str, Run]]) -> list[WordFragment]:
    """Group a token's (char, run) pairs into one fragment per contiguous run,
    preserving order."""
    fragments: list[WordFragment] = []
    for char, run in token:
        if fragments and fragments[-1].run_id == run.id:
            fragments[-1] = WordFragment(run.id, fragments[-1].text + char)
        else:
            fragments.append(WordFragment(run.id, char))
    return fragments


def _bbox_from_runs(token: list[tuple[str, Run]]) -> BoundingBox:
    runs = {id(r): r for _, r in token}.values()
    xs = [r.bbox.x for r in runs]
    rights = [r.bbox.x + r.bbox.width for r in runs]
    tops = [r.bbox.y for r in runs]
    bottoms = [r.bbox.y + r.bbox.height for r in runs]
    left, top = min(xs), min(tops)
    return BoundingBox(x=left, y=top, width=max(rights) - left, height=max(bottoms) - top)


def build_words(runs: list[Run], baseline_y: float, hints: list[WordBox] | None = None) -> list[Word]:
    """Reconstruct the line's lexical words from its runs. `hints` (PyMuPDF
    word boxes) refine geometry ONLY when they align 1:1 with the reconstructed
    words — they are never allowed to change word text or boundaries."""
    stream: list[tuple[str, Run]] = [(ch, run) for run in runs for ch in run.text]

    tokens: list[list[tuple[str, Run]]] = []
    current: list[tuple[str, Run]] = []
    for char, run in stream:
        if char.isspace():
            if current:
                tokens.append(current)
                current = []
        else:
            current.append((char, run))
    if current:
        tokens.append(current)

    # Geometry refinement: only when the hint set matches the reconstruction
    # exactly (same count and text), so a disagreeing hint can never corrupt
    # structure — it is simply ignored (extraction is not the word oracle).
    hint_by_index: dict[int, WordBox] = {}
    if hints:
        ordered = sorted(hints, key=lambda w: w.x)
        if len(ordered) == len(tokens) and all(
            "".join(c for c, _ in tok) == hint.text for tok, hint in zip(tokens, ordered)
        ):
            hint_by_index = dict(enumerate(ordered))

    words: list[Word] = []
    for index, token in enumerate(tokens):
        text = "".join(char for char, _ in token)
        hint = hint_by_index.get(index)
        if hint is not None:
            bbox = BoundingBox(x=hint.x, y=_bbox_from_runs(token).y, width=hint.width, height=_bbox_from_runs(token).height)
            baseline = hint.baseline_y
        else:
            bbox = _bbox_from_runs(token)
            baseline = baseline_y
        words.append(Word(id=str(uuid.uuid4()), text=text, bbox=bbox, baseline_y=baseline, fragments=_fragments(token)))
    return words
