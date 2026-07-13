import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


_request_id: ContextVar[str] = ContextVar("request_id", default="-")
logger = logging.getLogger("app.request")


def get_request_id() -> str:
    return _request_id.get()


@contextmanager
def bind_request_id(request_id: str) -> Iterator[None]:
    token = _request_id.set(request_id)
    try:
        yield
    finally:
        _request_id.reset(token)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started_at = perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
            await send(message)

        with bind_request_id(request_id):
            try:
                await self._app(scope, receive, send_with_request_id)
            finally:
                logger.info(
                    "request_completed",
                    extra={
                        "method": scope["method"],
                        "path": scope["path"],
                        "status_code": status_code,
                        "duration_ms": max(
                            0,
                            round((perf_counter() - started_at) * 1000),
                        ),
                    },
                )
