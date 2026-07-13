"""Measured quality (Phase 2.7): per-stage Expected/Observed/Delta/Confidence
ledger + release scorecard, computed from the reconstructed tree."""

from app.pipeline.document import Document
from app.pipeline.elements.bbox import BoundingBox
from app.pipeline.elements.font import FontResource
from app.pipeline.elements.page import Page
from app.pipeline.elements.textbox import TextBlock, TextSpan
from app.pipeline.quality.accounting import compute_document_quality
from app.pipeline.typography.line_builder import build_line
from app.pipeline.typography.paragraph_builder import build_paragraphs
from app.pipeline.typography.region_builder import build_regions

BB = BoundingBox(50, 100, 300, 12)


def _document(texts: list[str]) -> Document:
    fonts = [FontResource(id="f1", original_name="Arial", family="Arial")]
    fonts_by_id = {f.id: f for f in fonts}
    blocks = [
        TextBlock(id=f"b{i}", page=1, bbox=BoundingBox(50, 100 + i * 14, 300, 12), text=t,
                  origin_y=110 + i * 14, line_height=14.0, font_size=12.0,
                  spans=[TextSpan(text=t, font_id="f1", font_size=12.0, color="#000")])
        for i, t in enumerate(texts)
    ]
    lines = [build_line(b, i, fonts_by_id) for i, b in enumerate(blocks)]
    page = Page(number=1, width=600, height=800, text_blocks=blocks, regions=build_regions(build_paragraphs(lines, fonts_by_id)))
    doc = Document(project_id="p", pages=[page], fonts=fonts)
    doc.reconstruction_profile = {"chars_total": sum(len(t.replace(" ", "")) for t in texts), "chars_lost": 0, "character_substitution_rate": 0.0}
    return doc


def test_conservation_stages_are_100_percent() -> None:
    quality = compute_document_quality(_document(["Hello world", "second line"]))
    by_stage = {s["stage"]: s for s in quality["stages"]}
    assert by_stage["run_builder"]["delta"] == 0
    assert by_stage["run_builder"]["confidence"] == 1.0
    assert by_stage["word_builder"]["confidence"] == 1.0  # lexical chars conserved
    assert by_stage["paragraph_builder"]["expected"] == by_stage["paragraph_builder"]["observed"]


def test_scorecard_passes_for_a_clean_document() -> None:
    quality = compute_document_quality(_document(["Hello world"]))
    scorecard = quality["scorecard"]
    assert scorecard["character_fidelity_pct"]["current"] == 100.0
    assert scorecard["validator_errors"]["current"] == 0
    assert quality["overall_pass"] is True


def test_scorecard_flags_character_loss() -> None:
    doc = _document(["Hello world"])
    doc.reconstruction_profile = {"chars_total": 10, "chars_lost": 1, "character_substitution_rate": 0.0}
    quality = compute_document_quality(doc)
    assert quality["scorecard"]["character_fidelity_pct"]["pass"] is False
    assert quality["overall_pass"] is False


def test_rendering_fidelity_fails_the_gate_despite_conserved_characters() -> None:
    # The real-document failure mode: characters conserve 100% but 74% of
    # words escalate to glyph mode with low confidence — the render is NOT
    # faithful, so the gate MUST fail (it used to report PASS).
    doc = _document(["Hello world"])
    doc.reconstruction_profile = {
        "chars_total": 10, "chars_lost": 0, "character_substitution_rate": 0.0,
        "glyph_fraction": 0.7372, "mean_reconstruction_confidence": 0.8613,
    }
    quality = compute_document_quality(doc)
    assert quality["scorecard"]["character_fidelity_pct"]["pass"] is True   # conservation is fine
    assert quality["scorecard"]["glyph_escalation_rate"]["pass"] is False   # rendering is not
    assert quality["scorecard"]["mean_reconstruction_confidence"]["pass"] is False
    assert quality["overall_pass"] is False


def test_expected_observed_delta_shape() -> None:
    quality = compute_document_quality(_document(["one two"]))
    for stage in quality["stages"]:
        assert {"stage", "metric", "expected", "observed", "delta", "confidence"} <= stage.keys()
        assert stage["delta"] == stage["observed"] - stage["expected"]
