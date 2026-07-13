"""Baselines + regression detection (RVF). A corpus run is only as useful as
its comparison to the last known-good run — this is how the compiler evolves
safely (like a compiler's golden output tests)."""

import json
from pathlib import Path


def save_baseline(aggregates: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(aggregates, indent=2), encoding="utf-8")


def load_baseline(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def detect_regressions(current: dict, baseline: dict | None, *, time_tolerance: float = 0.25) -> list[str]:
    """Compare current aggregates to the baseline. Returns human-readable
    regression lines (empty = no regressions)."""
    if not baseline:
        return []
    regressions: list[str] = []

    if current["failed"] > baseline["failed"]:
        regressions.append(f"failures ↑ {baseline['failed']} → {current['failed']}")
    if current["unicode_fidelity_pct"] < baseline["unicode_fidelity_pct"] - 1e-6:
        regressions.append(
            f"unicode fidelity ↓ {baseline['unicode_fidelity_pct']:.4f}% → {current['unicode_fidelity_pct']:.4f}%"
        )
    if current["unicode_parity_failures"] > baseline["unicode_parity_failures"]:
        regressions.append(
            f"legacy↔semantic parity failures ↑ "
            f"{baseline['unicode_parity_failures']} → {current['unicode_parity_failures']}"
        )
    if current["chars_lost"] > baseline["chars_lost"]:
        regressions.append(f"characters lost ↑ {baseline['chars_lost']} → {current['chars_lost']}")
    base_time = baseline.get("total_seconds", 0.0)
    if base_time and current["total_seconds"] > base_time * (1 + time_tolerance):
        regressions.append(
            f"total time ↑ {base_time:.1f}s → {current['total_seconds']:.1f}s (>{int(time_tolerance*100)}%)"
        )
    return regressions
