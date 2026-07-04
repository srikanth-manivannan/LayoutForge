from app.core.enums import AssetType
from app.pipeline.document import Document
from app.repositories.interfaces import IAssetRepository, IJobRepository, IPageRepository, IProjectRepository
from app.schemas.summary import (
    HealthRead,
    ManifestAssetRead,
    ManifestFontRead,
    ManifestPageRead,
    ManifestRead,
    ProgressRead,
    ProjectSummary,
    ProjectSummaryProjectRead,
    StatisticsRead,
)
from app.services.storage_service import StorageService

_RECENT_LOG_LINES = 5


class SummaryService:
    """Assembles the one consolidated, read-only view the frontend dashboard
    and workspace need (project + statistics + manifest + health + progress
    + warnings + a small recent-logs snippet). Everything here is derived
    on demand from already-persisted artifacts (idm.json, the DB, and a
    directory walk) — no pipeline stage is added and no generator output is
    changed."""

    def __init__(
        self,
        project_repository: IProjectRepository,
        job_repository: IJobRepository,
        page_repository: IPageRepository,
        asset_repository: IAssetRepository,
        storage_service: StorageService,
    ) -> None:
        self._projects = project_repository
        self._jobs = job_repository
        self._pages = page_repository
        self._assets = asset_repository
        self._storage = storage_service

    def get_summary(self, project_id: str) -> ProjectSummary | None:
        project = self._projects.get(project_id)
        if project is None:
            return None

        project_dir = self._storage.project_dir(project_id)
        idm = self._try_load_idm(project_id)

        statistics = self._build_statistics(project_id, idm)
        manifest = self._build_manifest(idm)
        health = self._build_health(project_id, idm)
        progress = self._build_progress(project_id)
        warnings = self._build_warnings(project_id, idm, health)
        recent_logs = self._tail_application_log()

        return ProjectSummary(
            project=ProjectSummaryProjectRead.model_validate(project, from_attributes=True),
            statistics=statistics,
            manifest=manifest,
            health=health,
            progress=progress,
            warnings=warnings,
            recent_logs=recent_logs,
        )

    def _try_load_idm(self, project_id: str) -> Document | None:
        try:
            return self._storage.load_idm(project_id)
        except (FileNotFoundError, ValueError):
            return None

    def _build_statistics(self, project_id: str, idm: Document | None) -> StatisticsRead:
        project_dir = self._storage.project_dir(project_id)
        pages_dir = project_dir / "pages"
        css_dir = project_dir / "resources" / "css"

        html_file_count = len(list(pages_dir.glob("*.html"))) if pages_dir.is_dir() else 0
        css_file_count = len(list(css_dir.glob("*.css"))) if css_dir.is_dir() else 0

        if idm is not None:
            page_count = len(idm.pages)
            text_block_count = sum(len(page.text_blocks) for page in idm.pages)
            image_count = sum(1 for asset in idm.assets if asset.type == AssetType.IMAGE.value)
            font_count = len(idm.fonts)
        else:
            db_pages = self._pages.list_by_project(project_id)
            db_assets = self._assets.list_by_project(project_id)
            page_count = len(db_pages)
            text_block_count = 0
            image_count = sum(1 for asset in db_assets if asset.type == AssetType.IMAGE)
            font_count = sum(1 for asset in db_assets if asset.type == AssetType.FONT)

        disk_size_bytes = sum(f.stat().st_size for f in project_dir.rglob("*") if f.is_file()) if project_dir.is_dir() else 0

        return StatisticsRead(
            page_count=page_count,
            html_file_count=html_file_count,
            css_file_count=css_file_count,
            image_count=image_count,
            font_count=font_count,
            text_block_count=text_block_count,
            disk_size_bytes=disk_size_bytes,
        )

    def _build_manifest(self, idm: Document | None) -> ManifestRead | None:
        if idm is None:
            return None
        return ManifestRead(
            title=idm.metadata.title,
            author=idm.metadata.author,
            page_count=idm.metadata.page_count,
            pages=[
                ManifestPageRead(
                    number=page.number,
                    width=page.width,
                    height=page.height,
                    rotation=page.rotation,
                    background_image=page.background_image,
                )
                for page in idm.pages
            ],
            fonts=[
                ManifestFontRead(id=font.id, family=font.family, weight=font.weight, style=font.style, embedded=font.embedded)
                for font in idm.fonts
            ],
            assets=[
                ManifestAssetRead(
                    id=asset.id,
                    type=asset.type,
                    filename=asset.filename,
                    path=asset.path,
                    referenced_pages=asset.referenced_pages,
                )
                for asset in idm.assets
            ],
        )

    def _build_health(self, project_id: str, idm: Document | None) -> HealthRead:
        project_dir = self._storage.project_dir(project_id)
        db_pages = self._pages.list_by_project(project_id)
        all_pages_rendered = bool(db_pages) and all(p.html_path and p.css_path for p in db_pages)
        return HealthRead(storage_ok=project_dir.is_dir(), idm_ok=idm is not None, all_pages_rendered=all_pages_rendered)

    def _build_progress(self, project_id: str) -> ProgressRead | None:
        jobs = self._jobs.list_by_project(project_id)
        if not jobs:
            return None
        latest = jobs[0]
        return ProgressRead(
            job_id=latest.id,
            status=latest.status,
            stage=latest.stage,
            progress=latest.progress,
            current_page=latest.current_page,
            total_pages=latest.total_pages,
            error_message=latest.error_message,
        )

    def _build_warnings(self, project_id: str, idm: Document | None, health: HealthRead) -> list[str]:
        warnings: list[str] = []
        project = self._projects.get(project_id)
        if project is None:
            return warnings

        if project.status.value == "ready" and idm is None:
            warnings.append("Project is marked ready but its Internal Document Model (idm.json) is missing.")

        if project.status.value == "ready" and not health.all_pages_rendered:
            warnings.append("Project is marked ready but one or more pages are missing generated HTML or CSS.")

        if idm is not None:
            fonts_dir = self._storage.fonts_dir(project_id)
            for font in idm.fonts:
                if font.filename and not (fonts_dir / font.filename).exists():
                    warnings.append(f"Font file missing on disk: {font.filename} (family: {font.family}).")

        return warnings

    def _tail_application_log(self) -> list[str]:
        log_path = self._storage.logs_dir / "application.log"
        if not log_path.is_file():
            return []
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return []
        return lines[-_RECENT_LOG_LINES:]
