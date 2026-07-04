"""Adaptive precision (M1.5): a word stays cheap WORD level when its
measured width error is within tolerance, and only escalates to GLYPH (the
expensive per-glyph reconstruction M2 will handle) when it doesn't — so a
large document flags the ~5% that need it, not 100%."""

from app.pipeline.elements.textbox import WordBox
from app.pipeline.stages.normalize_idm import FontMetrics, apply_adaptive_precision

UPM = 1000
ADV = {"A": 600, "B": 400}


def make_metrics() -> FontMetrics:
    return FontMetrics(cmap={ord("A"): "A", ord("B"): "B"}, advances={"A": (600, 0), "B": (400, 0)}, units_per_em=UPM)


def make_word(text: str, width: float, size: float = 10.0) -> WordBox:
    return WordBox(text=text, x=0.0, width=width, baseline_y=0.0, font_id="f1", font_size=size)


def test_word_within_tolerance_stays_word_no_correction() -> None:
    # natural("AB") = (600+400)/1000*10 = 10.0; box 10.1 → 0.1px error < 0.3px
    word = make_word("AB", width=10.1)
    apply_adaptive_precision(word, {"f1": make_metrics()})
    assert word.mode == "word"
    assert word.letter_spacing == 0.0
    assert abs(word.width_error) <= 0.3


def test_word_beyond_tolerance_escalates_to_glyph() -> None:
    # box 8.0 → 2.0px error > 0.3px → GLYPH, interim letter-spacing applied
    word = make_word("AB", width=8.0)
    apply_adaptive_precision(word, {"f1": make_metrics()})
    assert word.mode == "glyph"
    assert word.letter_spacing == -1.0  # -2.0 / 2 chars
    assert word.width_error == -2.0


def test_implausible_correction_flags_glyph_without_distorting() -> None:
    # box 40.0 → +30px over 2 chars = 15/char = 150% of size → don't distort,
    # but still flag GLYPH for proper reconstruction.
    word = make_word("AB", width=40.0)
    apply_adaptive_precision(word, {"f1": make_metrics()})
    assert word.mode == "glyph"
    assert word.letter_spacing == 0.0


def test_unmeasurable_word_stays_word() -> None:
    word = make_word("AB", width=8.0)
    apply_adaptive_precision(word, {"f1": None})
    assert word.mode == "word"
    assert word.letter_spacing == 0.0
