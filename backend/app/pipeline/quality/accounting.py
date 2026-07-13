"""Quality accounting (Phase 2.7).

Computes, from the final Document, a conservation ledger across the
reconstruction stages and a release scorecard. Each stage reports
Expected / Observed / Delta / Confidence, so a drop in confidence points at
the FIRST stage that lost information — not merely where a defect became
visible.
"""

from dataclasses import dataclass

from app.pipeline.document import Document

# Scorecard targets (the objective definition of "done" per conversion) —
# Rendering Accuracy v1 success criteria (docs/ROAD_TO_PHASE4.md). Conservation
# metrics (fidelity/lexical/font) prove the model is internally correct;
# RENDERING-FIDELITY metrics (glyph escalation, reconstruction confidence,
# width error) prove the layout can be reproduced WITHOUT heavy corrective
# styling. A model can be internally perfect yet render poorly — these catch
# that. Pixel-level rendering metrics (baseline/line-height/overlay error)
# require the visual layer (Playwright) and are added with it.
_TARGETS = {
    "character_fidelity_pct": 100.0,
    "unicode_fidelity_pct": 100.0,
    "lexical_conservation_pct": 100.0,
    "font_resolution_pct": 99.9,
    "glyph_escalation_rate": 0.10,           # rendering fidelity — lower is better
    "mean_reconstruction_confidence": 0.99,  # rendering fidelity
    "mean_width_error_px": 0.25,             # rendering fidelity — lower is better
    "validator_errors": 0,
}
# Metrics where a SMALLER current value is better (pass = current <= target).
_LOWER_IS_BETTER = {"validator_errors", "glyph_escalation_rate", "mean_width_error_px"}


@dataclass
class StageMeasurement:
    stage: str
    metric: str
    expected: int
    observed: int

    @property
    def delta(self) -> int:
        return self.observed - self.expected

    @property
    def confidence(self) -> float:
        if self.expected == 0:
            return 1.0
        return round(max(0.0, 1.0 - abs(self.delta) / self.expected), 6)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "metric": self.metric,
            "expected": self.expected,
            "observed": self.observed,
            "delta": self.delta,
            "confidence": self.confidence,
        }


def _iter_runs(document: Document):
    for page in document.pages:
        for region in page.regions:
            for paragraph in region.paragraphs:
                for line in paragraph.lines:
                    for run in line.runs:
                        yield run


def _iter_lines(document: Document):
    for page in document.pages:
        for region in page.regions:
            for paragraph in region.paragraphs:
                yield from paragraph.lines


def _iter_words(document: Document):
    for line in _iter_lines(document):
        yield from line.words


def compute_document_quality(document: Document) -> dict:
    extract_chars = sum(len(block.text) for page in document.pages for block in page.text_blocks)
    run_chars = sum(len(run.text) for run in _iter_runs(document))
    run_nonspace = sum(sum(0 if ch.isspace() else 1 for ch in run.text) for run in _iter_runs(document))
    word_chars = sum(len(word.text) for word in _iter_words(document))
    extract_lines = sum(len(page.text_blocks) for page in document.pages)
    tree_lines = sum(1 for _ in _iter_lines(document))

    runs_with_font = [run for run in _iter_runs(document) if run.font_id]
    font_ids = {font.id for font in document.fonts}
    fonts_resolved = sum(1 for run in runs_with_font if run.font_id in font_ids)

    stages = [
        StageMeasurement("run_builder", "characters", extract_chars, run_chars),
        StageMeasurement("word_builder", "lexical_characters", run_nonspace, word_chars),
        StageMeasurement("paragraph_builder", "lines", extract_lines, tree_lines),
        StageMeasurement("font_resolution", "runs_with_font", len(runs_with_font), fonts_resolved),
    ]
    by_stage = {m.stage: m for m in stages}

    profile = document.reconstruction_profile or {}
    chars_total = profile.get("chars_total", 0)
    chars_lost = profile.get("chars_lost", 0)
    substitution_rate = profile.get("character_substitution_rate", 0.0)
    validator_errors = (document.idm_validation or {}).get("errors", 0)

    current = {
        "character_fidelity_pct": round(100.0 * (1 - chars_lost / chars_total), 4) if chars_total else 100.0,
        "unicode_fidelity_pct": round(100.0 * (1 - substitution_rate), 4),
        "lexical_conservation_pct": round(100.0 * by_stage["word_builder"].confidence, 4),
        "font_resolution_pct": round(100.0 * by_stage["font_resolution"].confidence, 4),
        # Rendering fidelity: what fraction of words could NOT be reproduced by
        # simple browser layout (escalated to glyph), and how confident the
        # reconstruction is. High escalation ⇒ the layout leans on corrective
        # styling ⇒ the render is not faithful, even if characters conserve.
        "glyph_escalation_rate": round(profile.get("glyph_fraction", 0.0), 4),
        "mean_reconstruction_confidence": round(profile.get("mean_reconstruction_confidence", 1.0), 4),
        "mean_width_error_px": _mean_width_error(document),
        "validator_errors": validator_errors,
    }
    scorecard = {}
    for metric, target in _TARGETS.items():
        value = current[metric]
        passed = value <= target if metric in _LOWER_IS_BETTER else value >= target
        scorecard[metric] = {"target": target, "current": value, "pass": passed}

    return {
        "stages": [m.to_dict() for m in stages],
        "scorecard": scorecard,
        "rendering": {
            "glyph_escalation_rate": current["glyph_escalation_rate"],
            "mean_reconstruction_confidence": current["mean_reconstruction_confidence"],
            "mean_width_error_px": current["mean_width_error_px"],
        },
        "overall_pass": all(entry["pass"] for entry in scorecard.values()),
    }


def _mean_width_error(document: Document) -> float:
    """Average absolute per-word width error (px) between the PDF box and the
    font-metric estimate — the direct signal of font-metric/tracking accuracy.
    Sourced from the adaptive-reconstruction word boxes (the measurement is
    already computed there; consumed here, never recomputed)."""
    errors = [
        abs(word.width_error)
        for page in document.pages
        for block in page.text_blocks
        for word in block.words
    ]
    return round(sum(errors) / len(errors), 3) if errors else 0.0
