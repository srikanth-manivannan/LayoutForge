"""Run Builder (Phase 2): runs merge on visual identity, split on genuine
style change even mid-word, and never merge across subset/object identity
boundaries that are visually identical."""

from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.textbox import TextBlock, TextSpan
from app.pipeline.typography.run_builder import build_runs


def _font(fid: str, original: str, weight: str = "normal", style: str = "normal") -> FontResource:
    return FontResource(id=fid, original_name=original, family=original, weight=weight, style=style)


def _block(spans: list[TextSpan]) -> TextBlock:
    return TextBlock(
        id="b1",
        page=1,
        bbox=BoundingBox(x=0.0, y=0.0, width=200.0, height=12.0),
        text="".join(s.text for s in spans),
        spans=spans,
    )


def test_sibling_subsets_of_same_face_merge_into_one_run() -> None:
    """`ABCDEF+Arial` and `XYZQWE+Arial` are the same typeface in two subsets
    — visually identical, so one run (not a mid-word split of `Times`)."""
    fonts = {
        "a": _font("a", "ABCDEF+Arial"),
        "b": _font("b", "XYZQWE+Arial"),
    }
    spans = [
        TextSpan(text="Ti", font_id="a", font_size=12.0, color="#000000"),
        TextSpan(text="mes", font_id="b", font_size=12.0, color="#000000"),
    ]
    runs = build_runs(_block(spans), fonts)
    assert len(runs) == 1
    assert runs[0].text == "Times"


def test_italic_change_splits_even_mid_word() -> None:
    """Genuine style change is authorial intent and must survive — `Hel`
    regular + `lo` italic stays two runs though it splits a word."""
    fonts = {
        "reg": _font("reg", "Arial"),
        "ital": _font("ital", "Arial-Italic", style="italic"),
    }
    spans = [
        TextSpan(text="Hel", font_id="reg", font_size=12.0, color="#000000"),
        TextSpan(text="lo", font_id="ital", font_size=12.0, color="#000000"),
    ]
    runs = build_runs(_block(spans), fonts)
    assert [r.text for r in runs] == ["Hel", "lo"]
    assert runs[0].italic is False and runs[1].italic is True


def test_color_and_size_changes_split_runs() -> None:
    fonts = {"a": _font("a", "Arial")}
    spans = [
        TextSpan(text="red", font_id="a", font_size=12.0, color="#ff0000"),
        TextSpan(text="black", font_id="a", font_size=12.0, color="#000000"),
        TextSpan(text="big", font_id="a", font_size=18.0, color="#000000"),
    ]
    runs = build_runs(_block(spans), fonts)
    assert [r.text for r in runs] == ["red", "black", "big"]


def test_bold_detected_and_weight_set() -> None:
    fonts = {"b": _font("b", "Arial-Bold", weight="bold")}
    runs = build_runs(_block([TextSpan(text="Hi", font_id="b", font_size=12.0, color="#000")]), fonts)
    assert runs[0].weight == 700


def test_runs_carry_style_only_not_words() -> None:
    # Words are reconstructed on the Line by the Word Builder (Phase 2.6);
    # the Run Builder produces style runs and does not own words.
    fonts = {"reg": _font("reg", "Arial"), "bold": _font("bold", "Arial-Bold", weight="bold")}
    spans = [
        TextSpan(text="normal ", font_id="reg", font_size=12.0, color="#000"),
        TextSpan(text="BOLD", font_id="bold", font_size=12.0, color="#000"),
    ]
    runs = build_runs(_block(spans), fonts)
    assert [r.text for r in runs] == ["normal ", "BOLD"]
    assert not hasattr(runs[0], "words")
