import asyncio

from fastapi.testclient import TestClient

from app.api.v1.health import health_check
from app.main import app


def test_health_check_returns_ok() -> None:
    response = asyncio.run(health_check())

    assert response == {
        "status": "ok",
        "service": "ai-agent-lab-backend",
    }


def test_health_endpoint_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ai-agent-lab-backend",
    }


def test_health_endpoint_includes_cors_header_for_configured_origin() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:5173"},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_health_endpoint_allows_configured_frontend_origin() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
