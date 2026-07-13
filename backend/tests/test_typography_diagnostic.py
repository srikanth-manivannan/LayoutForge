"""Typography measurement diagnostic (Rendering Accuracy v1): the classifier
that attributes actual↔nominal advance differences to their cause."""

from tools.rvf.typography_diagnostic import classify_advances


def _pairs(nominals, transform):
    return [(transform(n), n) for n in nominals]


def test_matching_advances_classify_as_ok() -> None:
    result = classify_advances(_pairs([8.0, 9.0, 10.0, 7.5], lambda n: n))
    assert result["cause"] == "ok"


def test_constant_additive_excess_is_tracking() -> None:
    # Every glyph gets +2.5px (the Tc signature).
    result = classify_advances(_pairs([8.0, 9.0, 10.0, 7.5, 6.0], lambda n: n + 2.5))
    assert result["cause"] == "tracking"
    assert abs(result["tracking_px"] - 2.5) < 0.01


def test_constant_ratio_is_scaling() -> None:
    # Every glyph scaled ×1.2 (the Tz signature).
    result = classify_advances(_pairs([8.0, 9.0, 10.0, 7.5, 6.0], lambda n: n * 1.2))
    assert result["cause"] == "scaling"
    assert abs(result["scale"] - 1.2) < 0.02


def test_too_few_glyphs_is_unmeasurable() -> None:
    assert classify_advances([(8.0, 8.0)])["cause"] == "unmeasurable"
