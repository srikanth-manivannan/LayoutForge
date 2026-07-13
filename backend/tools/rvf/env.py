"""Provenance capture (RVF). Every report records exactly what produced it —
six months from now this is what makes an old report interpretable."""

import platform
import subprocess
from datetime import datetime, timezone

from app.core.config import Settings
from tools.rvf import RVF_VERSION


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 - provenance is best-effort, never fatal
        return "unknown"


def capture_environment(settings: Settings | None = None) -> dict:
    settings = settings or Settings()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rvf_version": RVF_VERSION,
        "layoutforge_version": settings.app_version,
        "git_commit": _git_commit(),
        "lfs_version": "1.0",
        "rich_idm_version": "0.3",  # ADR-011 tree revision
        "writer_version": "0.1",
        "feature_flags": {
            "use_rich_tree": settings.use_rich_tree,
            "emit_debug_attributes": settings.emit_debug_attributes,
        },
        "os": platform.platform(),
        "python": platform.python_version(),
    }
