import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import register_exception_handlers
from app.core.request_context import RequestContextMiddleware


SENSITIVE_DETAIL = "private unexpected diagnostic"


def create_test_app() -> FastAPI:
    test_app = FastAPI()
    test_app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(test_app)

    @test_app.get("/ok")
    def ok() -> dict[str, str]:
        return {"status": "ok"}

    @test_app.get("/explode")
    def explode() -> None:
        raise RuntimeError(SENSITIVE_DETAIL)

    return test_app


def test_method_not_allowed_uses_unified_error() -> None:
    with TestClient(create_test_app()) as client:
        response = client.post("/ok")

    assert response.status_code == 405
    assert response.json() == {
        "error": {
            "code": "http_error",
            "message": "Method not allowed",
            "request_id": response.headers["x-request-id"],
        }
    }


def test_unexpected_error_is_safe_and_request_linked(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR, logger="app.error"):
        with TestClient(
            create_test_app(),
            raise_server_exceptions=False,
        ) as client:
            response = client.get("/explode")

    request_id = response.headers["x-request-id"]
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "The request could not be completed",
            "request_id": request_id,
        }
    }
    assert SENSITIVE_DETAIL not in response.text
    assert SENSITIVE_DETAIL not in caplog.text
    assert any(
        record.getMessage() == "request_failed"
        and record.error_code == "internal_error"
        and record.request_id == request_id
        for record in caplog.records
    )
