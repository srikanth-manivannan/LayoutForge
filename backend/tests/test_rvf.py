"""Rendering Validation Framework end-to-end: it drives real PDFs through the
real pipeline, produces a report, and its writer-diff/baseline logic works."""

from pathlib import Path

from tools.rvf.baseline import detect_regressions
from tools.rvf.runner import run_corpus
from tests.conftest import make_rich_pdf_bytes


def _corpus(tmp_path: Path, count: int = 2) -> Path:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for i in range(count):
        (corpus / f"doc_{i}.pdf").write_bytes(make_rich_pdf_bytes(pages=2))
    return corpus


def test_run_corpus_produces_report_and_metrics(tmp_path: Path) -> None:
    result = run_corpus(_corpus(tmp_path), tmp_path / "report")

    assert (tmp_path / "report" / "index.html").exists()
    assert (tmp_path / "report" / "summary.json").exists()
    assert (tmp_path / "report" / "metrics.csv").exists()

    agg = result.aggregates
    assert agg["total"] == 2 and agg["ok"] == 2 and agg["failed"] == 0
    assert agg["chars_total"] > 0
    assert agg["chars_lost"] == 0  # fidelity gate holds across the corpus
    # Phase R-1: the production path renders runs — uniform-style synthetic
    # pages need ZERO spans (the old word-pinned path emitted one per word;
    # the "semantic ≤ legacy" comparison is obsolete now both are run-based).
    assert agg["legacy_spans"] == 0
    assert result.regressions == []  # no baseline → nothing to regress against


def test_legacy_semantic_unicode_parity_holds(tmp_path: Path) -> None:
    result = run_corpus(_corpus(tmp_path, count=1), tmp_path / "report")
    assert result.aggregates["unicode_parity_failures"] == 0


def test_baseline_regression_detection() -> None:
    baseline = {"failed": 0, "unicode_fidelity_pct": 100.0, "unicode_parity_failures": 0,
                "chars_lost": 0, "total_seconds": 10.0}
    worse = {"failed": 1, "unicode_fidelity_pct": 99.5, "unicode_parity_failures": 2,
             "chars_lost": 3, "total_seconds": 20.0}
    regressions = detect_regressions(worse, baseline)
    assert len(regressions) == 5  # failures, fidelity, parity, lost, time
    assert detect_regressions(baseline, baseline) == []
