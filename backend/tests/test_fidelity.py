"""M-R1 Document Fidelity Measurement Framework: metric shape
{current,target,pass,confidence,source}, reserved slots, static geometry
measurements, and — critically — GATED overall scoring (never averaged)."""

from app.pipeline.document import Document
from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.line import Line
from app.pipeline.elements.page import Page
from app.pipeline.elements.paragraph import Paragraph
from app.pipeline.elements.region import Region
from app.pipeline.elements.run import Run
from app.pipeline.elements.textbox import TextBlock, WordBox
from app.pipeline.quality.fidelity import CRITICAL_FAMILIES, Metric, compute_document_fidelity

BB = BoundingBox(0, 0, 100, 12)


def _line(baseline: float, lid: str) -> Line:
    return Line(id=lid, bbox=BB, baseline_y=baseline,
                runs=[Run(id=f"r-{lid}", bbox=BB, text="hello", font_id="f1", font_size=12.0)])


def _document(*, glyph_fraction: float = 0.0, confidence: float = 1.0,
              width_errors: list[float] | None = None,
              baseline_gaps: list[float] | None = None,
              line_height: float = 14.0) -> Document:
    fonts = [FontResource(id="f1", original_name="Arial", family="Arial")]
    # Geometrically consistent fixture: origin_y placed exactly where the CSS
    # half-leading model puts the baseline, so a "clean" document really is
    # clean (the baseline metric flags the difference otherwise — correctly).
    size, asc, desc, top = 12.0, 0.8, -0.2, 100.0
    origin_y = top + (line_height - (asc - desc) * size) / 2 + asc * size
    words = [WordBox(text=f"w{i}", x=0, width=20, baseline_y=origin_y, font_id="f1", width_error=e)
             for i, e in enumerate(width_errors or [])]
    block = TextBlock(id="b1", page=1, bbox=BoundingBox(50, top, 300, 12), text="hello world",
                      origin_y=origin_y, line_height=line_height, font_size=size,
                      ascender=asc, descender=desc, words=words)
    baselines = [100.0]
    for gap in (baseline_gaps or []):
        baselines.append(baselines[-1] + gap)
    lines = [_line(b, f"l{i}") for i, b in enumerate(baselines)]
    paragraph = Paragraph(id="p1", bbox=BB, line_height=line_height, lines=lines)
    page = Page(number=1, width=600, height=800, text_blocks=[block],
                regions=[Region(id="reg", bbox=BB, paragraphs=[paragraph])])
    doc = Document(project_id="p", pages=[page], fonts=fonts)
    doc.reconstruction_profile = {
        "chars_total": 10, "chars_lost": 0, "character_substitution_rate": 0.0,
        "glyph_fraction": glyph_fraction, "mean_reconstruction_confidence": confidence,
    }
    return doc


def test_metric_shape_matches_the_approved_contract() -> None:
    entry = Metric("word_drift", 0.42, 0.25, lower_is_better=True,
                   confidence=0.998, source="static_geometry").to_dict()
    assert entry == {
        "metric": "word_drift", "current": 0.42, "target": 0.25, "pass": False,
        "confidence": 0.998, "source": "static_geometry", "unit": "",
    }


def test_every_family_exists_with_reserved_slots() -> None:
    fidelity = compute_document_fidelity(_document())
    assert set(fidelity["families"]) == {
        "extraction", "typography", "layout", "semantic", "rendering", "performance",
    }
    semantic = fidelity["families"]["semantic"]
    assert semantic["gate_pass"] is None  # fully reserved → no data, no gate
    assert all(m["source"] == "reserved" and m["current"] is None for m in semantic["metrics"])


def test_overall_is_gated_never_averaged() -> None:
    """The review's exact scenario: Typography/Extraction perfect, Rendering
    terrible — an average would look fine; the gate must fail."""
    fidelity = compute_document_fidelity(_document(glyph_fraction=0.80, confidence=0.5))
    families = fidelity["families"]
    assert families["extraction"]["gate_pass"] is True
    assert families["rendering"]["gate_pass"] is False
    assert fidelity["overall"]["pass"] is False
    # And the trend score is weakest-link (min), not a mean.
    scores = [f["score"] for f in families.values() if f["score"] is not None]
    assert fidelity["overall"]["score"] == min(scores)


def test_clean_document_passes_all_critical_gates() -> None:
    fidelity = compute_document_fidelity(_document(baseline_gaps=[14.0, 14.0]))
    for name in CRITICAL_FAMILIES:
        assert fidelity["families"][name]["gate_pass"] in (True, None)
    assert fidelity["overall"]["pass"] is True


def test_line_height_deviation_measured_from_tree_baselines() -> None:
    # Paragraph line_height=14 but actual gaps are 18 → deviation 4px, FAIL.
    fidelity = compute_document_fidelity(_document(baseline_gaps=[18.0, 18.0]))
    typography = {m["metric"]: m for m in fidelity["families"]["typography"]["metrics"]}
    assert typography["line_height_deviation_px"]["current"] == 4.0
    assert typography["line_height_deviation_px"]["pass"] is False


def test_word_drift_uses_width_error_proxy_with_reduced_confidence() -> None:
    fidelity = compute_document_fidelity(_document(width_errors=[0.4, 0.4, 0.5]))
    drift = {m["metric"]: m for m in fidelity["families"]["typography"]["metrics"]}["word_drift_px"]
    assert drift["current"] == 0.4  # median
    assert drift["pass"] is False   # > 0.25 target
    assert drift["confidence"] < 1.0  # proxy, honestly flagged


def test_performance_family_populated_only_when_rvf_supplies_it() -> None:
    without = compute_document_fidelity(_document())
    assert without["families"]["performance"]["gate_pass"] is None
    with_perf = compute_document_fidelity(_document(), performance={"seconds_per_page": 1.5})
    perf = {m["metric"]: m for m in with_perf["families"]["performance"]["metrics"]}
    assert perf["seconds_per_page"]["current"] == 1.5
    assert perf["seconds_per_page"]["source"] == "rvf"
