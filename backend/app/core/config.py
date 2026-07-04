from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[3] is the repository root, so storage/
# resolves consistently regardless of the process's working directory.
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Centralized application configuration, sourced from environment
    variables / .env. Every tunable that previously risked being scattered
    or hardcoded (limits, paths, quality knobs) lives here."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "LayoutForge"
    app_version: str = "0.1.0"
    # Bumped whenever a request/response shape changes incompatibly, so the
    # frontend can detect a stale backend instead of failing silently.
    api_version: int = 1
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"

    storage_root: Path = REPO_ROOT / "storage"
    database_url: str = f"sqlite:///{(REPO_ROOT / 'storage' / 'layoutforge.db').as_posix()}"

    max_upload_size_bytes: int = 2 * 1024 * 1024 * 1024  # 2 GB
    allowed_upload_extensions: list[str] = [".pdf"]

    # Background render resolution. 300 DPI is the default for print-quality
    # fidelity; lower values trade fidelity for faster processing/smaller files.
    preview_dpi: Literal[72, 150, 300, 600] = 300
    jpeg_quality: int = 85

    @property
    def projects_dir(self) -> Path:
        return self.storage_root / "projects"

    @property
    def cache_dir(self) -> Path:
        return self.storage_root / "cache"

    @property
    def temp_dir(self) -> Path:
        return self.storage_root / "temp"

    @property
    def logs_dir(self) -> Path:
        return self.storage_root / "logs"
