"""Reconstruction diagnostics (M1.6): every escalated word records WHY
(reason) and an internal confidence, and the document profile aggregates
them — so the engine is explainable, not a black box."""

from app.pipeline.elements.textbox import WordBox
from app.pipeline.typography.adaptive_reconstruction import (
    AdaptiveReconstructionEngine,
    ReconstructionDecision,
    classify_reason,
)
from app.pipeline.typography.font_metrics import FontMetrics

UPM = 1000


def metrics(advances: dict[str, int]) -> FontMetrics:
    cmap = {ord(c): c for c in advances}
    return FontMetrics(cmap=cmap, advances={c: (a, 0) for c, a in advances.items()}, units_per_em=UPM)


def word(text: str, width: float, font="f1", size=10.0) -> WordBox:
    return WordBox(text=text, x=0.0, width=width, baseline_y=0.0, font_id=font, font_size=size)


def test_classify_reason_ligature_kerning_width() -> None:
    assert classify_reason("office", -2.0) == "ligature"  # contains "ffi"/"fi"
    assert classify_reason("HTML", -3.0) == "kerning"      # narrower than advances
    assert classify_reason("wide", +3.0) == "width_error"  # wider than advances


def test_within_tolerance_stays_word_high_confidence() -> None:
    eng = AdaptiveReconstructionEngine({"f1": metrics({"A": 600, "B": 400})})
    w = word("AB", width=10.05)  # natural 10.0, error 0.05 < 0.3
    eng.reconstruct_word(w)
    assert w.mode == "word"
    assert w.reason == "none"
    assert w.reconstruction_confidence > 0.99


def test_kerned_word_escalates_with_reason_and_lower_confidence() -> None:
    eng = AdaptiveReconstructionEngine({"f1": metrics({"H": 700, "T": 600})})
    # natural 13.0; box 9.0 → error -4.0, narrower → kerning
    w = word("HT", width=9.0)
    eng.reconstruct_word(w)
    assert w.mode == "glyph"
    assert w.reason == "kerning"
    assert 0.4 <= w.reconstruction_confidence < 0.9  # interim approximation
    assert w.letter_spacing != 0.0


def test_decide_word_returns_frozen_contract_without_mutating() -> None:
    eng = AdaptiveReconstructionEngine({"f1": metrics({"H": 700, "T": 600})})
    w = word("HT", width=9.0)
    decision = eng.decide_word(w)
    # decide_word is PURE — the word is untouched until reconstruct_word.
    assert w.mode == "word" and w.reason == "none"
    # the frozen contract carries the full measurement for consumers.
    assert decision.mode == "glyph"
    assert decision.reason == "kerning"
    assert decision.expected_width == 13.0
    assert decision.actual_width == 9.0
    assert decision.width_error == -4.0
    # Issue 002A: tolerance is calibrated from the measured bbox-vs-advance
    # gap (~2px) + a small per-glyph term, not a flat 0.3px constant.
    assert decision.tolerance == 2.16
    import dataclasses

    assert dataclasses.is_dataclass(decision)
    try:
        decision.mode = "word"  # frozen — must raise
        raise AssertionError("decision should be immutable")
    except dataclasses.FrozenInstanceError:
        pass


def test_unmeasurable_font_flags_unknown() -> None:
    eng = AdaptiveReconstructionEngine({"f1": None})
    w = word("AB", width=9.0)
    eng.reconstruct_word(w)
    assert w.reason == "unknown"
    assert w.reconstruction_confidence == 0.7


def test_profile_aggregates_modes_reasons_and_confidence() -> None:
    eng = AdaptiveReconstructionEngine({"f1": metrics({"A": 600, "B": 400, "H": 700, "T": 600})})
    eng.reconstruct_word(word("AB", width=10.0))  # exact → word
    eng.reconstruct_word(word("HT", width=9.0))   # kerned → glyph
    profile = eng.profile.to_dict()
    assert profile["words"] == 2
    assert profile["by_mode"]["word"] == 1
    assert profile["by_mode"]["glyph"] == 1
    assert profile["by_reason"]["kerning"] == 1
    assert profile["glyph_fraction"] == 0.5
    assert 0.0 <= profile["mean_reconstruction_confidence"] <= 1.0
