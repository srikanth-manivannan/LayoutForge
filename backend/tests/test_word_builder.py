"""Word Builder — Lexical Reconstruction (Phase 2.6): words come from the run
stream, span runs via fragments, preserve whitespace, and never lose or
reorder a character."""

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.run import Run
from app.pipeline.elements.textbox import WordBox
from app.pipeline.typography.word_builder import build_words

BB = BoundingBox(0, 0, 50, 12)


def _run(text: str, rid: str) -> Run:
    return Run(id=rid, bbox=BB, text=text, font_id="f", font_size=12.0)


def test_simple_line_segments_into_words() -> None:
    words = build_words([_run("Hello world", "r")], baseline_y=10.0)
    assert [w.text for w in words] == ["Hello", "world"]
    assert all(len(w.fragments) == 1 and w.fragments[0].run_id == "r" for w in words)


def test_word_spanning_two_runs_becomes_fragments_not_a_split() -> None:
    # "New York Time"(run1) + "s Bestselling author"(run2): the word "Times"
    # spans the run boundary and is represented as ordered fragments.
    runs = [_run("New York Time", "r1"), _run("s Bestselling author", "r2")]
    words = build_words(runs, baseline_y=10.0)
    times = next(w for w in words if w.text == "Times")
    assert [(f.run_id, f.text) for f in times.fragments] == [("r1", "Time"), ("r2", "s")]


def test_mixed_size_word_is_one_word_multiple_fragments() -> None:
    # "Tot theToad": hair space separates "Tot"; "theToad" spans two runs.
    runs = [_run("Tot ", "r1"), _run("the", "r2"), _run("Toad ", "r3")]
    words = build_words(runs, baseline_y=10.0)
    assert [w.text for w in words] == ["Tot", "theToad"]
    assert [(f.run_id, f.text) for f in words[1].fragments] == [("r2", "the"), ("r3", "Toad")]


def test_fragments_reassemble_every_word() -> None:
    runs = [_run("New York Time", "r1"), _run("s Bestselling author", "r2")]
    for word in build_words(runs, baseline_y=10.0):
        assert "".join(f.text for f in word.fragments) == word.text


def test_no_character_lost_or_reordered() -> None:
    runs = [_run("Tot ", "r1"), _run("the", "r2"), _run("Toad ", "r3")]
    words = build_words(runs, baseline_y=10.0)
    # Every non-space character survives, in order, across the words.
    non_space_in = "".join(ch for r in runs for ch in r.text if not ch.isspace())
    non_space_out = "".join(w.text for w in words)
    assert non_space_in == non_space_out


def test_geometry_hint_used_only_when_aligned() -> None:
    runs = [_run("Hello world", "r")]
    hints = [
        WordBox(text="Hello", x=5.0, width=30.0, baseline_y=9.0, font_id="f"),
        WordBox(text="world", x=40.0, width=28.0, baseline_y=9.0, font_id="f"),
    ]
    words = build_words(runs, baseline_y=10.0, hints=hints)
    assert words[0].bbox.x == 5.0 and words[1].bbox.x == 40.0  # hint geometry adopted


def test_disaligned_hints_are_ignored() -> None:
    # PyMuPDF merged the token wrongly (one hint vs two reconstructed words):
    # the hint must not corrupt structure; geometry falls back to the runs.
    runs = [_run("Tot ", "r1"), _run("the", "r2"), _run("Toad", "r3")]
    hints = [WordBox(text="Tot theToad", x=5.0, width=90.0, baseline_y=9.0, font_id="f")]
    words = build_words(runs, baseline_y=10.0, hints=hints)
    assert [w.text for w in words] == ["Tot", "theToad"]  # reconstruction wins
