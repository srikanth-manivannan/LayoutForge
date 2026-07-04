from fastapi.testclient import TestClient

from tests.conftest import make_pdf_bytes


def upload(client: TestClient, pages: int = 2) -> dict:
    pdf_bytes = make_pdf_bytes(pages=pages)
    response = client.post(
        "/api/projects",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        data={"name": "Test Report"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_creates_project_and_completes_job() -> None:
    from app.main import app

    with TestClient(app) as client:
        body = upload(client)
        project_id, job_id = body["project_id"], body["job_id"]

        job_response = client.get(f"/api/jobs/{job_id}")
        assert job_response.status_code == 200
        job = job_response.json()
        assert job["status"] == "completed"
        assert job["progress"] == 100

        project_response = client.get(f"/api/projects/{project_id}")
        assert project_response.status_code == 200
        project = project_response.json()
        assert project["page_count"] == 2
        assert project["name"] == "Test Report"
        assert project["status"] == "ready"

        listing = client.get("/api/projects").json()
        assert any(p["id"] == project_id for p in listing)

        delete_response = client.delete(f"/api/projects/{project_id}")
        assert delete_response.status_code == 204
        assert client.get(f"/api/projects/{project_id}").status_code == 404


def test_upload_rejects_non_pdf_file() -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/projects",
            files={"file": ("report.txt", b"not a pdf", "text/plain")},
        )
        assert response.status_code == 400
