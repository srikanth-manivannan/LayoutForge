"""Core v1 Certification (RVF; docs/DEVELOPMENT_MODEL.md): the release bar
before Phase 3 — 0 P0/P1, 0 failures, quality pass everywhere, parity."""

from tools.rvf.certification import certify


def _clean_aggregates(**overrides) -> dict:
    agg = {
        "total": 5, "failed": 0, "quality_passes": 5, "unicode_parity_failures": 0,
        "issues_by_severity": {"P2": 3, "P3": 1},
    }
    agg.update(overrides)
    return agg


def test_clean_corpus_certifies() -> None:
    result = certify(_clean_aggregates())
    assert result["certified"] is True
    assert all(c["pass"] for c in result["criteria"].values())


def test_p0_blocks_certification() -> None:
    result = certify(_clean_aggregates(issues_by_severity={"P0": 1}))
    assert result["certified"] is False
    assert result["criteria"]["no_p0_issues"]["pass"] is False


def test_p1_blocks_certification() -> None:
    assert certify(_clean_aggregates(issues_by_severity={"P1": 2}))["certified"] is False


def test_quality_failure_blocks_certification() -> None:
    result = certify(_clean_aggregates(quality_passes=4))
    assert result["certified"] is False
    assert result["criteria"]["quality_all_pass"]["pass"] is False


def test_empty_corpus_is_not_certified() -> None:
    assert certify(_clean_aggregates(total=0, quality_passes=0))["certified"] is False
