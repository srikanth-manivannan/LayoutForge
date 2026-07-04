import subprocess
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter

from app.core.settings import get_settings
from app.schemas.version import VersionInfo

router = APIRouter(tags=["version"])

# Captured once, at import time (effectively process start) rather than
# per-request, so /api/version reports when this backend instance came up
# — the detail that actually answers "is this the process I think it is?".
_BUILD_TIME = datetime.now(timezone.utc).isoformat()


@lru_cache
def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=2, check=True
        )
        return result.stdout.strip()
    except Exception:  # noqa: BLE001 - no git repo / git not installed is expected in some environments
        return None


@router.get("/version", response_model=VersionInfo)
def get_version() -> VersionInfo:
    settings = get_settings()
    return VersionInfo(
        version=settings.app_version,
        build=_BUILD_TIME,
        git_commit=_git_commit(),
        api_version=settings.api_version,
    )
