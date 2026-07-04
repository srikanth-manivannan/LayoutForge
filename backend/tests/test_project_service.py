from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.enums import JobStatus, ProjectStatus
from app.events.dispatcher import EventDispatcher
from app.repositories.sqlite.job_repository import SQLiteJobRepository
from app.repositories.sqlite.project_repository import SQLiteProjectRepository
from app.services.project_service import ProjectService
from app.services.storage_service import StorageService
from app.utils.upload_validation import UploadValidationError
from tests.conftest import make_encrypted_pdf_bytes, make_pdf_bytes


def make_service(db_session, tmp_path: Path) -> ProjectService:
    settings = Settings(storage_root=tmp_path)
    storage = StorageService(settings)
    return ProjectService(
        SQLiteProjectRepository(db_session),
        SQLiteJobRepository(db_session),
        storage,
        settings,
        EventDispatcher(),
    )


def test_create_project_from_upload_happy_path(db_session, tmp_path: Path) -> None:
    service = make_service(db_session, tmp_path)
    temp_pdf = tmp_path / "incoming.pdf"
    temp_pdf.write_bytes(make_pdf_bytes(pages=3))

    project, job = service.create_project_from_upload(
        temp_path=temp_pdf, original_filename="My Report.pdf", size_bytes=temp_pdf.stat().st_size
    )

    assert project.page_count == 3
    assert project.status == ProjectStatus.CREATED
    assert job.project_id == project.id
    assert job.status == JobStatus.QUEUED
    assert not temp_pdf.exists()  # moved into the project's storage dir
    assert (tmp_path / "projects" / project.id / "source.pdf").exists()


def test_create_project_from_upload_rejects_wrong_extension(db_session, tmp_path: Path) -> None:
    service = make_service(db_session, tmp_path)
    temp_file = tmp_path / "incoming.docx"
    temp_file.write_bytes(b"irrelevant")

    with pytest.raises(UploadValidationError):
        service.create_project_from_upload(
            temp_path=temp_file, original_filename="report.docx", size_bytes=temp_file.stat().st_size
        )

    assert not (tmp_path / "projects").exists()


def test_create_project_from_upload_rejects_password_protected_pdf(db_session, tmp_path: Path) -> None:
    service = make_service(db_session, tmp_path)
    temp_pdf = tmp_path / "incoming.pdf"
    temp_pdf.write_bytes(make_encrypted_pdf_bytes())

    with pytest.raises(UploadValidationError):
        service.create_project_from_upload(
            temp_path=temp_pdf, original_filename="secret.pdf", size_bytes=temp_pdf.stat().st_size
        )

    assert not (tmp_path / "projects").exists()
