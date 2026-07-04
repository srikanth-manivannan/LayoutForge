from fastapi.testclient import TestClient

from tests.test_api_projects import upload


def test_list_pages_returns_geometry_and_paths_after_pipeline_completes() -> None:
    from app.main import app

    with TestClient(app) as client:
        body = upload(client, pages=2)
        project_id = body["project_id"]

        response = client.get(f"/api/projects/{project_id}/pages")
        assert response.status_code == 200
        pages = response.json()

        assert len(pages) == 2
        first = next(p for p in pages if p["page_number"] == 1)
        assert first["width"] > 0
        assert first["height"] > 0
        assert first["html_path"] == "pages/page_0001.html"
        assert first["css_path"] == "resources/css/page_0001.css"
        assert first["background_image"] == "resources/images/page_0001_bg.png"


def test_static_files_serve_generated_html_and_css() -> None:
    from app.main import app

    with TestClient(app) as client:
        body = upload(client, pages=1)
        project_id = body["project_id"]

        html_response = client.get(f"/static/projects/{project_id}/pages/page_0001.html")
        assert html_response.status_code == 200
        assert "lf-page" in html_response.text

        css_response = client.get(f"/static/projects/{project_id}/resources/css/common.css")
        assert css_response.status_code == 200
        assert ".lf-page" in css_response.text
