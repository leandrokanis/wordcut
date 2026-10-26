from fastapi.testclient import TestClient

from wordcut_api.app import create_app


def test_health_reports_ok() -> None:
    response = TestClient(create_app()).get("/api/health")

    assert (response.status_code, response.json()) == (200, {"status": "ok"})
