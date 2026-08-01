import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.orm import Session

from app.core.logging import safe_stack_locations

logger = logging.getLogger(__name__)

AsyncSessionCallback = Callable[[], Awaitable[None]]

_ASYNC_ROLLBACK_CALLBACKS = "async_rollback_callbacks"
_ASYNC_SESSION_FINALIZERS = "async_session_finalizers"


def register_async_rollback_callback(
    session: Session,
    callback: AsyncSessionCallback,
) -> None:
    _register_callback(session, _ASYNC_ROLLBACK_CALLBACKS, callback)


def register_async_session_finalizer(
    session: Session,
    callback: AsyncSessionCallback,
) -> None:
    _register_callback(session, _ASYNC_SESSION_FINALIZERS, callback)


def discard_async_rollback_callbacks(session: Session) -> None:
    session.info.pop(_ASYNC_ROLLBACK_CALLBACKS, None)


async def run_async_rollback_callbacks(session: Session) -> None:
    await _run_callbacks(session, _ASYNC_ROLLBACK_CALLBACKS)


async def run_async_session_finalizers(session: Session) -> None:
    await _run_callbacks(session, _ASYNC_SESSION_FINALIZERS)


def _register_callback(
    session: Session,
    key: str,
    callback: AsyncSessionCallback,
) -> None:
    if not callable(callback):
        raise TypeError("session callback must be callable")
    callbacks = session.info.setdefault(key, [])
    callbacks.append(callback)


async def _run_callbacks(session: Session, key: str) -> None:
    callbacks = session.info.pop(key, [])
    for callback in reversed(callbacks):
        try:
            await callback()
        except Exception as exc:
            logger.error(
                "session_async_callback_failed",
                extra={
                    "callback_group": key,
                    "exception_type": exc.__class__.__name__,
                    "stack_locations": safe_stack_locations(exc),
                },
            )
