from fastapi.testclient import TestClient

from tests.conftest import make_rich_pdf_bytes
from tests.test_api_projects import upload


def upload_rich(client: TestClient, pages: int = 2) -> dict:
    pdf_bytes = make_rich_pdf_bytes(pages=pages)
    response = client.post(
        "/api/projects",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        data={"name": "Rich Report"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_summary_returns_404_for_unknown_project() -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/projects/does-not-exist/summary")
        assert response.status_code == 404


def test_summary_reports_statistics_manifest_health_and_progress() -> None:
    from app.main import app

    with TestClient(app) as client:
        body = upload_rich(client, pages=2)
        project_id = body["project_id"]

        response = client.get(f"/api/projects/{project_id}/summary")
        assert response.status_code == 200, response.text
        summary = response.json()

        assert summary["project"]["id"] == project_id
        assert summary["statistics"]["page_count"] == 2
        assert summary["statistics"]["html_file_count"] == 2
        assert summary["statistics"]["css_file_count"] >= 2
        assert summary["statistics"]["image_count"] >= 1
        assert summary["statistics"]["font_count"] >= 1
        assert summary["statistics"]["disk_size_bytes"] > 0

        assert summary["manifest"] is not None
        assert summary["manifest"]["page_count"] == 2
        assert len(summary["manifest"]["pages"]) == 2

        assert summary["health"]["storage_ok"] is True
        assert summary["health"]["idm_ok"] is True
        assert summary["health"]["all_pages_rendered"] is True

        assert summary["progress"] is not None
        assert summary["progress"]["status"] == "completed"
        assert summary["progress"]["progress"] == 100

        assert summary["warnings"] == []
        assert isinstance(summary["recent_logs"], list)


def test_summary_manifest_is_null_before_pipeline_runs() -> None:
    """A project with no completed job yet (idm.json not written) must not
    crash the summary endpoint — manifest is simply null and warnings/health
    reflect the incomplete state, honestly, rather than fabricating data."""
    from app.main import app
    from app.core.settings import get_settings
    from app.services.storage_service import StorageService
    from app.models.project import Project
    from app.database.session import SessionLocal

    with TestClient(app) as client:
        db = SessionLocal()
        try:
            project = Project(name="Pending", filename="pending.pdf", page_count=0)
            db.add(project)
            db.commit()
            db.refresh(project)
            project_id = project.id
        finally:
            db.close()

        storage = StorageService(get_settings())
        storage.ensure_project_dirs(project_id)

        response = client.get(f"/api/projects/{project_id}/summary")
        assert response.status_code == 200, response.text
        summary = response.json()
        assert summary["manifest"] is None
        assert summary["health"]["idm_ok"] is False
        assert summary["progress"] is None
