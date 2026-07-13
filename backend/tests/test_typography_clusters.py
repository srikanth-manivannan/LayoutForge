"""M-R2.4 Typography Cluster Analysis (investigation-only): font/class
clusters, histograms, OpenType capability probing, worst/most-stable fonts."""

from pathlib import Path

from app.pipeline.document import Document
from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.page import Page
from app.pipeline.elements.textbox import TextBlock, WordBox
from tools.rvf.typography_clusters import (
    aggregate_typography,
    analyze_document_fonts,
    classify_font_class,
    histogram,
    probe_font_capabilities,
)
from tests.conftest import make_minimal_ttf_bytes

BB = BoundingBox(0, 0, 100, 12)


def test_font_class_heuristic() -> None:
    assert classify_font_class("ChauncyPro-Regular") == "handwriting"
    assert classify_font_class("KGDancingontheRooftop") == "handwriting"
    assert classify_font_class("Palatino-Roman") == "serif"
    assert classify_font_class("Avenir-Medium") == "sans"
    assert classify_font_class("Courier New") == "typewriter"
    assert classify_font_class("Zapfino Extra") == "unknown"


def test_histogram_buckets() -> None:
    result = histogram([0.05, 0.15, 0.15, 0.3, 0.7, 2.0])
    assert result == {"0-0.1": 1, "0.1-0.2": 2, "0.2-0.5": 1, "0.5-1.0": 1, ">1.0": 1}


def test_probe_capabilities_on_real_ttf(tmp_path: Path) -> None:
    path = tmp_path / "t.ttf"
    path.write_bytes(make_minimal_ttf_bytes())
    caps = probe_font_capabilities(path)
    assert caps["readable"] is True
    assert caps["has_gpos_kerning"] is False  # minimal font has no GPOS
    assert caps["has_gsub_ligatures"] is False
    assert caps["glyph_count"] == 2


def test_probe_unreadable_file_is_honest(tmp_path: Path) -> None:
    path = tmp_path / "bad.ttf"
    path.write_bytes(b"not a font")
    assert probe_font_capabilities(path) == {"readable": False}


def _document() -> Document:
    fonts = [
        FontResource(id="f1", original_name="ChauncyPro-Regular", family="ChauncyPro-Regular", subset=True),
        FontResource(id="f2", original_name="Palatino-Roman", family="Palatino-Roman"),
    ]
    words = (
        [WordBox(text=f"h{i}", x=0, width=10, baseline_y=10, font_id="f1",
                 width_error=0.3, mode="glyph", reason="width_error") for i in range(25)]
        + [WordBox(text=f"s{i}", x=0, width=10, baseline_y=10, font_id="f2",
                   width_error=0.001, mode="word", reason="none") for i in range(30)]
    )
    page = Page(number=1, width=600, height=800,
                text_blocks=[TextBlock(id="b1", page=1, bbox=BB, text="x", words=words)])
    return Document(project_id="p", pages=[page], fonts=fonts)


def test_aggregation_builds_font_and_class_clusters() -> None:
    rows = [analyze_document_fonts(_document(), None), analyze_document_fonts(_document(), None)]
    report = aggregate_typography(rows)

    by_family = {f["family"]: f for f in report["fonts"]}
    chauncy = by_family["ChauncyPro-Regular"]
    assert chauncy["documents"] == 2 and chauncy["words"] == 50
    assert chauncy["median_drift_px"] == 0.3
    assert chauncy["escalation_rate"] == 1.0
    assert chauncy["reason_pct"]["width_error"] == 100.0
    assert chauncy["subset_seen"] is True

    assert report["classes"]["handwriting"]["median_drift_px"] == 0.3
    assert report["classes"]["serif"]["median_drift_px"] < 0.01

    # worst/stable use the >=20-word evidence floor
    assert report["worst_fonts"][0] == "ChauncyPro-Regular"
    assert report["most_stable_fonts"][0] == "Palatino-Roman"
    assert sum(report["drift_histogram"].values()) == 110
