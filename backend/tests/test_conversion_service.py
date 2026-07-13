from pathlib import Path

from app.core.config import Settings
from app.core.enums import JobStatus, ProjectStatus
from app.events.dispatcher import EventDispatcher
from app.models.job import Job
from app.models.project import Project
from app.repositories.sqlite.asset_repository import SQLiteAssetRepository
from app.repositories.sqlite.job_repository import SQLiteJobRepository
from app.repositories.sqlite.page_repository import SQLitePageRepository
from app.repositories.sqlite.project_repository import SQLiteProjectRepository
from app.services.conversion_service import ConversionService
from app.services.project_service import ProjectService
from app.services.storage_service import StorageService
from tests.conftest import make_pdf_bytes, make_rich_pdf_bytes


def test_run_pipeline_marks_project_ready_on_success(db_session, tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, preview_dpi=72)
    storage = StorageService(settings)
    dispatcher = EventDispatcher()
    project_repo = SQLiteProjectRepository(db_session)
    job_repo = SQLiteJobRepository(db_session)
    page_repo = SQLitePageRepository(db_session)
    asset_repo = SQLiteAssetRepository(db_session)

    temp_pdf = tmp_path / "incoming.pdf"
    temp_pdf.write_bytes(make_pdf_bytes(pages=2))
    project, job = ProjectService(project_repo, job_repo, storage, settings, dispatcher).create_project_from_upload(
        temp_path=temp_pdf, original_filename="report.pdf", size_bytes=temp_pdf.stat().st_size
    )
    assert project.status == ProjectStatus.CREATED

    ConversionService(job_repo, project_repo, page_repo, asset_repo, storage, settings, dispatcher).run_pipeline(
        job.id
    )

    finished_job = job_repo.get(job.id)
    finished_project = project_repo.get(project.id)
    assert finished_job.status == JobStatus.COMPLETED
    assert finished_job.progress == 100
    assert finished_project.status == ProjectStatus.READY
    assert finished_project.page_count == 2
    assert len(page_repo.list_by_project(project.id)) == 2

    # The IDM must be reconstructible from disk alone — no PDF required.
    document = storage.load_idm(project.id)
    assert len(document.pages) == 2
    assert all(page.background_image for page in document.pages)

    db_pages = {p.page_number: p for p in page_repo.list_by_project(project.id)}
    assert db_pages[1].background_image == document.get_page(1).background_image


def test_run_pipeline_extracts_text_images_and_fonts_end_to_end(db_session, tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path, preview_dpi=72)
    storage = StorageService(settings)
    dispatcher = EventDispatcher()
    project_repo = SQLiteProjectRepository(db_session)
    job_repo = SQLiteJobRepository(db_session)
    page_repo = SQLitePageRepository(db_session)
    asset_repo = SQLiteAssetRepository(db_session)

    temp_pdf = tmp_path / "rich.pdf"
    temp_pdf.write_bytes(make_rich_pdf_bytes(pages=2, with_image=True))
    project, job = ProjectService(project_repo, job_repo, storage, settings, dispatcher).create_project_from_upload(
        temp_path=temp_pdf, original_filename="rich.pdf", size_bytes=temp_pdf.stat().st_size
    )

    ConversionService(job_repo, project_repo, page_repo, asset_repo, storage, settings, dispatcher).run_pipeline(
        job.id
    )

    assert job_repo.get(job.id).status == JobStatus.COMPLETED

    # Rebuild the Document purely from disk — proves the IDM is a complete
    # contract that doesn't require reopening the source PDF.
    document = storage.load_idm(project.id)
    assert len(document.pages) == 2
    for page in document.pages:
        assert page.background_image
        assert len(page.text_blocks) == 2
        assert len(page.images) == 1
        assert page.fonts_used
        assert all(block.font_id is not None for block in page.text_blocks)

    assets = asset_repo.list_by_project(project.id)
    image_assets = [a for a in assets if a.type.value == "image"]
    # Backgrounds are text-redacted (2026-07-13) — the fixture's two pages
    # differ only by heading text, so with text stripped the backgrounds are
    # pixel-identical and correctly dedup to 1, plus 1 deduplicated image.
    assert len(image_assets) == 2

    db_pages = {p.page_number: p for p in page_repo.list_by_project(project.id)}
    assert db_pages[1].css_path == "resources/css/page_0001.css"
    css_dir = storage.project_dir(project.id) / "resources" / "css"
    assert (css_dir / "common.css").exists()
    assert (css_dir / "page_0001.css").exists()

    assert db_pages[1].html_path == "pages/page_0001.html"
    html = (storage.project_dir(project.id) / "pages" / "page_0001.html").read_text(encoding="utf-8")
    assert "lf-layer-text" in html
    assert "lf-layer-images" in html

    # M1.7: the conversion report is written with the reconstruction profile
    # and per-stage timing/memory telemetry.
    import json

    report_path = storage.project_dir(project.id) / "report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["report_version"] == 1
    assert report["pages"] == 2
    assert report["reconstruction_profile"]["words"] >= 0
    assert report["performance"]["stages"]  # per-stage timing + memory recorded
    assert report["performance"]["peak_memory_mb"] >= 0.0


def test_run_pipeline_marks_project_failed_when_source_missing(db_session, tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path)
    storage = StorageService(settings)
    dispatcher = EventDispatcher()
    project_repo = SQLiteProjectRepository(db_session)
    job_repo = SQLiteJobRepository(db_session)
    page_repo = SQLitePageRepository(db_session)
    asset_repo = SQLiteAssetRepository(db_session)

    project = project_repo.create(Project(name="Broken", filename="broken.pdf", page_count=0))
    job = job_repo.create(Job(project_id=project.id))
    # source.pdf was never stored, so the pipeline's ValidateStage must fail.

    ConversionService(job_repo, project_repo, page_repo, asset_repo, storage, settings, dispatcher).run_pipeline(
        job.id
    )

    finished_job = job_repo.get(job.id)
    finished_project = project_repo.get(project.id)
    assert finished_job.status == JobStatus.FAILED
    assert finished_job.error_message
    assert finished_project.status == ProjectStatus.FAILED
