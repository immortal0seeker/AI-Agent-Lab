import asyncio

from app.api.v1.health import health_check


def test_health_check_returns_ok() -> None:
    response = asyncio.run(health_check())

    assert response == {
        "status": "ok",
        "service": "ai-agent-lab-backend",
    }
