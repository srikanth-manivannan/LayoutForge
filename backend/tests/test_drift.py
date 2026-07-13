"""M-R2a drift diagnostics: per-page / per-font / per-reason statistics with
mean/median/p95/max, worst offenders, and reason contribution percentages."""

from app.pipeline.document import Document
from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.page import Page
from app.pipeline.elements.textbox import TextBlock, WordBox
from tools.rvf.drift import aggregate_drift, drift_report

BB = BoundingBox(0, 0, 100, 12)


def _word(text: str, error: float, font_id: str = "f1", reason: str = "none") -> WordBox:
    return WordBox(text=text, x=0, width=20, baseline_y=10, font_id=font_id,
                   width_error=error, reason=reason)


def _document() -> Document:
    fonts = [
        FontResource(id="f1", original_name="ChauncyPro", family="ChauncyPro"),
        FontResource(id="f2", original_name="Palatino", family="Palatino"),
    ]
    page1 = Page(number=1, width=600, height=800, text_blocks=[
        TextBlock(id="b1", page=1, bbox=BB, text="x", words=[
            _word("kitchen", -4.0, "f1", "tracking"),
            _word("stinking", -5.0, "f1", "tracking"),
            _word("clean", 0.1, "f2", "none"),
        ]),
    ])
    page2 = Page(number=2, width=600, height=800, text_blocks=[
        TextBlock(id="b2", page=2, bbox=BB, text="y", words=[
            _word("office", -2.0, "f2", "ligature"),
            _word("tidy", 0.2, "f2", "none"),
        ]),
    ])
    return Document(project_id="p", pages=[page1, page2], fonts=fonts)


def test_per_page_stats_have_the_approved_shape() -> None:
    report = drift_report(_document())
    page1 = report["by_page"]["1"]
    assert {"count", "mean", "median", "p95", "max"} <= page1.keys()
    assert page1["count"] == 3
    assert page1["max"] == 5.0


def test_per_font_stats_isolate_the_broken_font() -> None:
    report = drift_report(_document())
    assert report["by_font"]["ChauncyPro"]["mean"] == 4.5   # the bad face
    assert report["by_font"]["Palatino"]["mean"] < 1.0      # fine


def test_per_reason_contribution_sums_to_100() -> None:
    report = drift_report(_document())
    contributions = [s["contribution_pct"] for s in report["by_reason"].values()]
    assert abs(sum(contributions) - 100.0) < 0.5
    # tracking carries most of the drift in this fixture
    assert report["by_reason"]["tracking"]["contribution_pct"] > 70


def test_worst_words_are_sorted_by_drift() -> None:
    worst = drift_report(_document())["worst_words"]
    assert worst[0]["text"] == "stinking" and worst[0]["drift_px"] == 5.0
    assert worst[1]["text"] == "kitchen"
    drifts = [w["drift_px"] for w in worst]
    assert drifts == sorted(drifts, reverse=True)


def test_aggregate_drift_rolls_up_fonts_across_documents() -> None:
    reports = [drift_report(_document()), drift_report(_document())]
    agg = aggregate_drift(reports)
    assert agg["by_font"]["ChauncyPro"]["count"] == 4  # 2 words × 2 docs
    assert "tracking" in agg["by_reason"]
    assert "contribution_pct" in agg["by_reason"]["tracking"]
