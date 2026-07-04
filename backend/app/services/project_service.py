from pathlib import Path

from app.core.config import Settings
from app.core.enums import JobStatus, ProjectStatus
from app.events.dispatcher import EventDispatcher
from app.events.events import ProjectCreated, ProjectDeleted, UploadCompleted
from app.models.job import Job
from app.models.project import Project
from app.repositories.interfaces import IJobRepository, IProjectRepository
from app.services.storage_service import StorageService
from app.utils.filenames import sanitize_filename
from app.utils.upload_validation import validate_extension, validate_mime, validate_pdf_structure


class ProjectService:
    def __init__(
        self,
        project_repository: IProjectRepository,
        job_repository: IJobRepository,
        storage_service: StorageService,
        settings: Settings,
        dispatcher: EventDispatcher,
    ) -> None:
        self._projects = project_repository
        self._jobs = job_repository
        self._storage = storage_service
        self._settings = settings
        self._dispatcher = dispatcher

    def create_project_from_upload(
        self, temp_path: Path, original_filename: str, size_bytes: int, display_name: str | None = None
    ) -> tuple[Project, Job]:
        """Validation order matters: an invalid PDF must never result in a
        project being created or any storage directory being written.
        extension -> MIME -> PDF structure -> create project -> store file
        -> create job -> return (caller schedules the background pipeline)."""
        sanitized_name = sanitize_filename(original_filename)
        validate_extension(sanitized_name, self._settings.allowed_upload_extensions)
        validate_mime(temp_path)

        document = validate_pdf_structure(temp_path)
        try:
            page_count = document.page_count
        finally:
            document.close()

        project = self._projects.create(
            Project(
                name=display_name or sanitized_name,
                filename=sanitized_name,
                page_count=page_count,
                status=ProjectStatus.CREATED,
            )
        )

        self._storage.store_source_pdf(project.id, temp_path)

        job = self._jobs.create(Job(project_id=project.id, status=JobStatus.QUEUED))

        self._dispatcher.publish(ProjectCreated(project_id=project.id, name=project.name))
        self._dispatcher.publish(
            UploadCompleted(project_id=project.id, filename=sanitized_name, size_bytes=size_bytes)
        )

        return project, job

    def list_projects(self) -> list[Project]:
        return self._projects.list()

    def get_project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def delete_project(self, project_id: str) -> bool:
        project = self._projects.get(project_id)
        if project is None:
            return False
        self._projects.delete(project_id)
        self._storage.delete_project(project_id)
        self._dispatcher.publish(ProjectDeleted(project_id=project_id))
        return True
