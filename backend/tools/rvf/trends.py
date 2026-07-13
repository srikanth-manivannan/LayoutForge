"""Trend history (M-R1). One JSONL row per corpus run — the release-over-
release quality record ("escalation 73% → 24% → …") that turns a snapshot
benchmark into evidence of direction. Lives next to the baseline so it
persists across runs and report directories."""

import json
from datetime import datetime, timezone
from pathlib import Path

MAX_TREND_ROWS = 20  # shown on the dashboard; the file itself keeps all rows


def trend_row(env: dict, aggregates: dict) -> dict:
    families = {}
    fidelity = aggregates.get("fidelity", {})
    for family, stats in fidelity.get("families", {}).items():
        families[family] = stats.get("mean_score")
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": env.get("git_commit"),
        "documents": aggregates.get("total", 0),
        "ok": aggregates.get("ok", 0),
        "quality_passes": aggregates.get("quality_passes", 0),
        "fidelity_passes": fidelity.get("overall_passes"),
        "unicode_fidelity_pct": aggregates.get("unicode_fidelity_pct"),
        "chars_lost": aggregates.get("chars_lost"),
        "total_issues": aggregates.get("total_issues"),
        "span_reduction": aggregates.get("span_reduction"),
        "total_seconds": aggregates.get("total_seconds"),
        "family_scores": families,
        "certified": aggregates.get("certification", {}).get("certified"),
    }


def append_history(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def load_history(path: Path, limit: int = MAX_TREND_ROWS) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # a corrupt line never breaks trend reporting
    return rows[-limit:]
