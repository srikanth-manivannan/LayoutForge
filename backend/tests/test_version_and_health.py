from fastapi.testclient import TestClient


def test_health_reports_storage_ok() -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["storage_ok"] is True


def test_version_endpoint_reports_api_version() -> None:
    from app.core.settings import get_settings
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/version")
        assert response.status_code == 200
        body = response.json()
        assert body["version"] == get_settings().app_version
        assert body["api_version"] == get_settings().api_version
        assert body["build"]  # ISO timestamp, non-empty
        assert "git_commit" in body


def test_static_mount_serves_marker_file() -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/static/projects/.static_ok")
        assert response.status_code == 200
        assert response.text == "ok"


def test_version_and_static_marker_contract_returns_200() -> None:
    """The frontend's environment check depends on exactly these two
    endpoints returning 200 — this has regressed in practice (a stale
    backend process serving an old build), so it gets its own explicit,
    fails-loudly test rather than relying on the more general checks above."""
    from app.main import app

    with TestClient(app) as client:
        version_response = client.get("/api/version")
        assert version_response.status_code == 200, (
            f"GET /api/version returned {version_response.status_code}, expected 200"
        )

        static_response = client.get("/static/projects/.static_ok")
        assert static_response.status_code == 200, (
            f"GET /static/projects/.static_ok returned {static_response.status_code}, expected 200"
        )


def test_all_expected_routes_are_registered() -> None:
    from app.main import app

    paths = {route.path for route in app.routes if hasattr(route, "path")}
    for expected in (
        "/api/health",
        "/api/version",
        "/api/projects",
        "/api/projects/{project_id}",
        "/api/jobs/{job_id}",
        "/api/projects/{project_id}/pages",
    ):
        assert expected in paths, f"Expected route {expected} not registered"
