import json
import shutil
from pathlib import Path

from app.core.config import Settings
from app.pipeline.document import Document


class StorageService:
    """Owns the on-disk layout of a project's workspace under storage/projects/{id}/."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def project_dir(self, project_id: str) -> Path:
        return self._settings.projects_dir / project_id

    def source_pdf_path(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "source.pdf"

    def images_dir(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "resources" / "images"

    def fonts_dir(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "resources" / "fonts"

    def idm_path(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "idm.json"

    @property
    def logs_dir(self) -> Path:
        return self._settings.logs_dir

    def ensure_project_dirs(self, project_id: str) -> None:
        base = self.project_dir(project_id)
        for sub in ("pages", "resources/images", "resources/fonts", "resources/css"):
            (base / sub).mkdir(parents=True, exist_ok=True)

    def store_source_pdf(self, project_id: str, temp_path: Path) -> Path:
        self.ensure_project_dirs(project_id)
        destination = self.source_pdf_path(project_id)
        shutil.move(str(temp_path), str(destination))
        return destination

    def save_idm(self, document: Document) -> Path:
        """Persists the full Internal Document Model to disk. Once this is
        written, any later stage or output plugin can reconstruct the
        Document via `load_idm` without ever reopening the source PDF."""
        self.ensure_project_dirs(document.project_id)
        path = self.idm_path(document.project_id)
        path.write_text(json.dumps(document.to_dict(), indent=2), encoding="utf-8")
        return path

    def load_idm(self, project_id: str) -> Document:
        data = json.loads(self.idm_path(project_id).read_text(encoding="utf-8"))
        return Document.from_dict(data)

    def delete_project(self, project_id: str) -> None:
        shutil.rmtree(self.project_dir(project_id), ignore_errors=True)
