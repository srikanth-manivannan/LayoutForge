"""M-R1 trend history: one JSONL row per run, resilient loading, and the
dashboard-facing shape."""

from pathlib import Path

from tools.rvf.trends import append_history, load_history, trend_row


def _aggregates() -> dict:
    return {
        "total": 3, "ok": 3, "quality_passes": 2, "unicode_fidelity_pct": 100.0,
        "chars_lost": 0, "total_issues": 4, "span_reduction": 120, "total_seconds": 42.5,
        "fidelity": {"overall_passes": 1, "families": {
            "typography": {"mean_score": 0.82}, "rendering": {"mean_score": 0.41},
        }},
        "certification": {"certified": False},
    }


def test_trend_row_captures_run_essentials() -> None:
    row = trend_row({"git_commit": "abc1234"}, _aggregates())
    assert row["git_commit"] == "abc1234"
    assert row["documents"] == 3 and row["quality_passes"] == 2
    assert row["family_scores"] == {"typography": 0.82, "rendering": 0.41}
    assert row["certified"] is False
    assert "timestamp" in row


def test_history_appends_and_loads_in_order(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    for commit in ("a", "b", "c"):
        append_history(path, trend_row({"git_commit": commit}, _aggregates()))
    rows = load_history(path)
    assert [r["git_commit"] for r in rows] == ["a", "b", "c"]


def test_corrupt_line_never_breaks_trends(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    append_history(path, trend_row({"git_commit": "a"}, _aggregates()))
    with path.open("a", encoding="utf-8") as fh:
        fh.write("{not json\n")
    append_history(path, trend_row({"git_commit": "b"}, _aggregates()))
    rows = load_history(path)
    assert [r["git_commit"] for r in rows] == ["a", "b"]


def test_load_history_respects_limit(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    for i in range(30):
        append_history(path, trend_row({"git_commit": str(i)}, _aggregates()))
    assert len(load_history(path)) == 20  # MAX_TREND_ROWS default
    assert load_history(path)[-1]["git_commit"] == "29"
