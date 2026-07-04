import os

from fastapi import APIRouter

from app.core.settings import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    storage_ok = settings.storage_root.is_dir() and os.access(settings.storage_root, os.W_OK)
    return HealthResponse(status="ok", app_env=settings.app_env, storage_ok=storage_ok)
