import asyncio
import logging

from sqlalchemy.orm import Session

from app.db.session_callbacks import (
    discard_async_rollback_callbacks,
    register_async_rollback_callback,
    register_async_session_finalizer,
    run_async_rollback_callbacks,
    run_async_session_finalizers,
)


def test_rollback_callbacks_run_once_in_reverse_registration_order() -> None:
    session = Session()
    events: list[str] = []

    async def first() -> None:
        events.append("first")

    async def second() -> None:
        events.append("second")

    register_async_rollback_callback(session, first)
    register_async_rollback_callback(session, second)

    asyncio.run(run_async_rollback_callbacks(session))
    asyncio.run(run_async_rollback_callbacks(session))

    assert events == ["second", "first"]


def test_discard_rollback_callbacks_prevents_cleanup_after_commit() -> None:
    session = Session()
    events: list[str] = []

    async def cleanup() -> None:
        events.append("cleanup")

    register_async_rollback_callback(session, cleanup)
    discard_async_rollback_callbacks(session)

    asyncio.run(run_async_rollback_callbacks(session))

    assert events == []


def test_session_finalizers_run_once_in_reverse_registration_order() -> None:
    session = Session()
    events: list[str] = []

    async def first() -> None:
        events.append("first")

    async def second() -> None:
        events.append("second")

    register_async_session_finalizer(session, first)
    register_async_session_finalizer(session, second)

    asyncio.run(run_async_session_finalizers(session))
    asyncio.run(run_async_session_finalizers(session))

    assert events == ["second", "first"]


def test_callback_failure_is_logged_and_does_not_skip_remaining_cleanup(
    caplog: object,
) -> None:
    session = Session()
    events: list[str] = []

    async def surviving_cleanup() -> None:
        events.append("survived")

    async def failing_cleanup() -> None:
        raise RuntimeError("private callback diagnostic")

    register_async_rollback_callback(session, surviving_cleanup)
    register_async_rollback_callback(session, failing_cleanup)

    with caplog.at_level(logging.ERROR, logger="app.db.session_callbacks"):
        asyncio.run(run_async_rollback_callbacks(session))

    assert events == ["survived"]
    assert "session_async_callback_failed" in caplog.text
    assert "private callback diagnostic" not in caplog.text
