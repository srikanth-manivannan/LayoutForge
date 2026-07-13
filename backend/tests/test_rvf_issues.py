"""RVF issue classification + per-document artifacts (Phase 2.7b): every
validator violation and scorecard failure becomes a categorized, earliest-
stage-attributed backlog item, and each document emits an evidence bundle."""

import json
from pathlib import Path

from app.pipeline.document import Document
from app.pipeline.quality.accounting import _TARGETS
from tools.rvf import artifacts, issues
from tools.rvf.pipeline import RunArtifacts


def _art(ok=True, validation=None, quality=None, error=None) -> RunArtifacts:
    doc = Document(project_id="p")
    doc.idm_validation = validation or {}
    doc.quality = quality or {}
    return RunArtifacts(name="book.pdf", ok=ok, document=doc, error=error, project_dir=None)


def test_pipeline_failure_is_a_p0_issue() -> None:
    result = issues.classify(_art(ok=False, error="boom"))
    assert len(result) == 1
    assert result[0]["category"] == "Pipeline" and result[0]["severity"] == "P0"
    assert result[0]["release_blocking"] is True


def test_validator_violation_maps_to_category_stage_and_severity() -> None:
    validation = {"violations": [
        {"code": "word_fragment_mismatch", "severity": "error", "page": 3, "message": "x"},
        {"code": "character_loss", "severity": "error", "page": 1, "message": "y"},
    ]}
    result = issues.classify(_art(validation=validation))
    # P0 (character_loss / Unicode / extraction) is ranked first
    assert result[0]["code"] == "character_loss"
    assert result[0]["severity"] == "P0" and result[0]["stage"] == "extraction"
    frag = next(i for i in result if i["code"] == "word_fragment_mismatch")
    assert frag["category"] == "Typography" and frag["stage"] == "word_builder" and frag["severity"] == "P1"


def test_warning_is_not_release_blocking() -> None:
    validation = {"violations": [{"code": "baseline_inversion", "severity": "warning", "page": 2, "message": "z"}]}
    issue = issues.classify(_art(validation=validation))[0]
    assert issue["severity"] == "P3" and issue["release_blocking"] is False


def test_issue_ids_are_deterministic_and_carry_lifecycle() -> None:
    validation = {"violations": [{"code": "empty_run", "severity": "error", "page": 1, "message": "m"}]}
    a = issues.classify(_art(validation=validation))[0]
    b = issues.classify(_art(validation=validation))[0]
    assert a["id"] == b["id"]  # stable across runs
    assert a["status"] == "Open" and a["detected_by"] == "RVF"
    assert {"regression_test", "fixed_in", "verified_by"} <= a.keys()


def test_scorecard_failure_becomes_an_issue() -> None:
    quality = {"scorecard": {"font_resolution_pct": {"target": 99.9, "current": 80.0, "pass": False}}}
    result = issues.classify(_art(quality=quality))
    assert any(i["code"] == "scorecard:font_resolution_pct" and i["category"] == "Fonts" for i in result)


def test_every_scorecard_metric_has_an_explicit_classification() -> None:
    """Regression test for a real bug found via the golden corpus (2026-07-11):
    `mean_width_error_px` was added to the quality scorecard but not to
    `issues._SCORECARD_META`, so it silently fell through to the generic
    default (category='Quality', stage='unknown', severity='P1') instead of
    joining its Rendering/font_metrics/P2 siblings — wrongly promoting a
    known-open rendering-fidelity gap to release-blocking. Every scorecard
    target must be explicitly classified, so this can't recur silently."""
    missing = set(_TARGETS) - set(issues._SCORECARD_META)
    assert not missing, f"scorecard metrics with no issue classification: {missing}"


def test_width_error_classifies_with_its_rendering_fidelity_siblings() -> None:
    quality = {"scorecard": {"mean_width_error_px": {"target": 0.25, "current": 1.85, "pass": False}}}
    issue = issues.classify(_art(quality=quality))[0]
    assert issue["category"] == "Rendering" and issue["stage"] == "font_metrics" and issue["severity"] == "P2"


def test_clean_document_has_no_issues() -> None:
    quality = {"scorecard": {"character_fidelity_pct": {"target": 100.0, "current": 100.0, "pass": True}}}
    assert issues.classify(_art(validation={"violations": []}, quality=quality)) == []


def test_artifacts_bundle_is_written(tmp_path: Path) -> None:
    art = _art(validation={"violations": []}, quality={"overall_pass": True, "scorecard": {}})
    record = {
        "pages": 2, "fidelity": {"chars_total": 10, "chars_lost": 0}, "structure": {"runs": 5},
        "performance": {"total_seconds": 1.2, "stage_seconds": {}}, "quality": {"overall_pass": True},
    }
    doc_dir = artifacts.write_document_artifacts(art, record, issues.classify(art), tmp_path / "documents")
    for name in ("report.json", "validator.json", "quality.json", "performance.json", "reconstruction.json", "issues.json"):
        assert (doc_dir / name).exists()
    assert json.loads((doc_dir / "issues.json").read_text())["count"] == 0
