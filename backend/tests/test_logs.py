from fastapi.testclient import TestClient


def test_logs_defaults_to_application_stream_and_returns_lines() -> None:
    from app.main import app

    with TestClient(app) as client:
        # Startup logging guarantees application.log has content by now.
        response = client.get("/api/logs")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["stream"] == "application"
        assert isinstance(body["lines"], list)
        assert isinstance(body["truncated"], bool)


def test_logs_accepts_each_known_stream() -> None:
    from app.main import app

    with TestClient(app) as client:
        for stream in ("application", "conversion", "performance"):
            response = client.get("/api/logs", params={"stream": stream})
            assert response.status_code == 200, response.text
            assert response.json()["stream"] == stream


def test_logs_rejects_unknown_stream() -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/logs", params={"stream": "../../etc/passwd"})
        assert response.status_code == 422


def test_logs_respects_tail_limit() -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/logs", params={"stream": "application", "tail": 3})
        assert response.status_code == 200, response.text
        assert len(response.json()["lines"]) <= 3
