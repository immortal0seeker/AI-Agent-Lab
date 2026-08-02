from collections.abc import Iterator
from contextvars import copy_context
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import TraceRun, TraceStep
from app.observability.trace_context import (
    TraceContext,
    bind_trace_run_id,
    get_trace_run_id,
)
from app.observability.trace_service import TraceService
from app.observability.trace_types import (
    TraceRunType,
    TraceStatus,
    TraceStepType,
)
from app.schemas.trace import TraceRunCreate


class SequenceClock:
    def __init__(self, *values: datetime) -> None:
        self._values = iter(values)

    def __call__(self) -> datetime:
        return next(self._values)


@pytest.fixture
def trace_db(tmp_path: Path) -> Iterator[tuple[Session, Engine]]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'trace-context.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session, engine
    finally:
        session.close()
        engine.dispose()


def create_trace_context(
    session: Session,
) -> tuple[TraceContext, TraceRun]:
    clock = SequenceClock(
        datetime(2026, 8, 2, 12, 0, 0),
        datetime(2026, 8, 2, 12, 0, 1),
        datetime(2026, 8, 2, 12, 0, 1, 250000),
    )
    service = TraceService(session, clock=clock)
    trace_run = service.create_run(
        TraceRunCreate(
            run_type=TraceRunType.CHAT,
            input_text="Explain the workspace",
        )
    )
    return TraceContext(service, trace_run), trace_run


def test_trace_run_id_binding_is_nested_and_restored() -> None:
    outer = uuid4()
    inner = uuid4()

    assert get_trace_run_id() is None
    with bind_trace_run_id(outer):
        assert get_trace_run_id() == outer
        with bind_trace_run_id(inner):
            assert get_trace_run_id() == inner
        assert get_trace_run_id() == outer
    assert get_trace_run_id() is None


def test_trace_run_id_is_restored_after_exception() -> None:
    with pytest.raises(RuntimeError, match="boom"):
        with bind_trace_run_id(uuid4()):
            raise RuntimeError("boom")

    assert get_trace_run_id() is None


def test_trace_run_id_is_isolated_across_copied_contexts() -> None:
    first_id = uuid4()
    second_id = uuid4()
    with bind_trace_run_id(first_id):
        first_context = copy_context()

    assert get_trace_run_id() is None
    with bind_trace_run_id(second_id):
        assert get_trace_run_id() == second_id
        assert first_context.run(get_trace_run_id) == first_id

    assert get_trace_run_id() is None


def test_trace_context_activation_binds_run_and_restores_outer_id(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    trace_context, trace_run = create_trace_context(session)
    outer_id = uuid4()

    with bind_trace_run_id(outer_id):
        with trace_context.activate() as active:
            assert active is trace_context
            assert get_trace_run_id() == trace_run.id
        assert get_trace_run_id() == outer_id

    assert get_trace_run_id() is None


def test_trace_context_step_binds_id_and_completes_with_output(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    trace_context, trace_run = create_trace_context(session)

    with trace_context.step(
        TraceStepType.LLM_CALL,
        name="Call model",
        input_json={"model": "mock-model"},
    ) as trace_step:
        assert get_trace_run_id() == trace_run.id
        assert trace_step.status == TraceStatus.RUNNING.value
        trace_step.output_json = {"finish_reason": "stop"}

    assert get_trace_run_id() is None
    assert trace_step.status == TraceStatus.COMPLETED.value
    assert trace_step.input_json == {"model": "mock-model"}
    assert trace_step.output_json == {"finish_reason": "stop"}
    assert trace_step.error_message is None
    assert trace_step.latency_ms == 250


def test_trace_context_step_fails_safely_and_reraises_original_exception(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    trace_context, trace_run = create_trace_context(session)
    synthetic_secret = "SYNTHETIC_SECRET_DO_NOT_STORE"

    with pytest.raises(RuntimeError, match=synthetic_secret):
        with trace_context.step(
            TraceStepType.TOOL_CALL,
            name="Call tool",
        ) as trace_step:
            assert get_trace_run_id() == trace_run.id
            trace_step.output_json = {"partial": synthetic_secret}
            raise RuntimeError(synthetic_secret)

    assert get_trace_run_id() is None
    stored = session.scalar(select(TraceStep))
    assert stored is not None
    assert stored.status == TraceStatus.FAILED.value
    assert stored.output_json is None
    assert stored.error_message == "RuntimeError"
    assert synthetic_secret not in stored.error_message
    assert stored.latency_ms == 250
