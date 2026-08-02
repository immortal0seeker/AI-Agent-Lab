from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import TraceRun, TraceStep
from app.observability.trace_service import TraceService, TraceStateError
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
    engine = create_db_engine(f"sqlite:///{tmp_path / 'trace-service.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session, engine
    finally:
        session.close()
        engine.dispose()


def create_running_run(
    session: Session,
    *ticks: datetime,
) -> tuple[TraceService, TraceRun]:
    service = TraceService(session, clock=SequenceClock(*ticks))
    trace_run = service.create_run(
        TraceRunCreate(
            run_type=TraceRunType.CHAT,
            input_text="Explain the workspace",
            metadata_json={"request_id": "req-1"},
        )
    )
    return service, trace_run


def test_trace_service_creates_running_run_and_ordered_steps(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    started_at = datetime(2026, 8, 2, 12, 0, 0)
    service, trace_run = create_running_run(
        session,
        started_at,
        datetime(2026, 8, 2, 12, 0, 1),
        datetime(2026, 8, 2, 12, 0, 2),
    )

    first = service.add_step(
        trace_run,
        step_type=TraceStepType.BUILD_CONTEXT,
        name="Build context",
        input_json={"message_count": 1},
    )
    second = service.add_step(
        trace_run,
        step_type=TraceStepType.LLM_CALL,
        name="Call model",
    )

    assert trace_run.status == TraceStatus.RUNNING.value
    assert trace_run.started_at == started_at
    assert trace_run.metadata_json == {"request_id": "req-1"}
    assert [first.step_index, second.step_index] == [1, 2]
    assert first.status == TraceStatus.RUNNING.value
    assert first.input_json == {"message_count": 1}
    assert second.input_json == {}
    assert session.scalars(
        select(TraceStep)
        .where(TraceStep.trace_run_id == trace_run.id)
        .order_by(TraceStep.step_index)
    ).all() == [first, second]


def test_trace_service_finishes_run_and_step(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    service, trace_run = create_running_run(
        session,
        datetime(2026, 8, 2, 12, 0, 0),
        datetime(2026, 8, 2, 12, 0, 1),
        datetime(2026, 8, 2, 12, 0, 1, 250000),
        datetime(2026, 8, 2, 12, 0, 2),
    )
    trace_step = service.add_step(
        trace_run,
        step_type=TraceStepType.LLM_CALL,
        name="Call model",
    )

    finished_step = service.finish_step(
        trace_step,
        output_json={"finish_reason": "stop"},
    )
    finished_run = service.finish_run(trace_run, output_text="Answer")

    assert finished_step is trace_step
    assert trace_step.status == TraceStatus.COMPLETED.value
    assert trace_step.output_json == {"finish_reason": "stop"}
    assert trace_step.error_message is None
    assert trace_step.latency_ms == 250
    assert finished_run is trace_run
    assert trace_run.status == TraceStatus.COMPLETED.value
    assert trace_run.output_text == "Answer"
    assert trace_run.error_message is None
    assert trace_run.latency_ms == 2000


def test_trace_service_never_commits_and_caller_rollback_removes_trace(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    _, trace_run = create_running_run(
        session,
        datetime(2026, 8, 2, 12, 0, 0),
    )
    trace_run_id = trace_run.id

    session.rollback()

    assert session.get(TraceRun, trace_run_id) is None


def test_trace_service_rejects_non_pending_create_status(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    service = TraceService(
        session,
        clock=lambda: datetime(2026, 8, 2, 12, 0, 0),
    )

    with pytest.raises(TraceStateError, match="requires pending"):
        service.create_run(
            TraceRunCreate(
                run_type=TraceRunType.CHAT,
                input_text="Invalid initial state",
                status=TraceStatus.COMPLETED,
            )
        )

    assert session.scalar(select(TraceRun)) is None


@pytest.mark.parametrize(
    "terminal_status",
    [
        TraceStatus.COMPLETED,
        TraceStatus.FAILED,
        TraceStatus.CANCELLED,
    ],
)
def test_trace_service_rejects_step_addition_to_terminal_run(
    trace_db: tuple[Session, Engine],
    terminal_status: TraceStatus,
) -> None:
    session, _ = trace_db
    service, trace_run = create_running_run(
        session,
        datetime(2026, 8, 2, 12, 0, 0),
    )
    trace_run.status = terminal_status.value

    with pytest.raises(TraceStateError, match="TraceRun must be running"):
        service.add_step(
            trace_run,
            step_type=TraceStepType.LLM_CALL,
            name="Call model",
        )

    assert trace_run.steps == []


def test_trace_service_rejects_repeated_terminal_transition_without_mutation(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    service, trace_run = create_running_run(
        session,
        datetime(2026, 8, 2, 12, 0, 0),
        datetime(2026, 8, 2, 12, 0, 1),
    )
    service.finish_run(trace_run, output_text="Answer")
    ended_at = trace_run.ended_at

    with pytest.raises(TraceStateError, match="TraceRun must be running"):
        service.fail_run(trace_run, error_message="Safe error")

    assert trace_run.status == TraceStatus.COMPLETED.value
    assert trace_run.output_text == "Answer"
    assert trace_run.error_message is None
    assert trace_run.ended_at == ended_at


def test_trace_service_records_explicit_failures_and_clears_partial_outputs(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    service, trace_run = create_running_run(
        session,
        datetime(2026, 8, 2, 12, 0, 0),
        datetime(2026, 8, 2, 12, 0, 1),
        datetime(2026, 8, 2, 12, 0, 1, 100000),
        datetime(2026, 8, 2, 12, 0, 2),
    )
    trace_step = service.add_step(
        trace_run,
        step_type=TraceStepType.TOOL_CALL,
        name="Call tool",
    )
    trace_step.output_json = {"partial": True}
    trace_run.output_text = "partial answer"

    service.fail_step(trace_step, error_message="  Safe tool failure  ")
    service.fail_run(trace_run, error_message="  Safe run failure  ")

    assert trace_step.status == TraceStatus.FAILED.value
    assert trace_step.output_json is None
    assert trace_step.error_message == "Safe tool failure"
    assert trace_step.latency_ms == 100
    assert trace_run.status == TraceStatus.FAILED.value
    assert trace_run.output_text is None
    assert trace_run.error_message == "Safe run failure"
    assert trace_run.latency_ms == 2000


def test_trace_service_rejects_blank_failure_without_mutation(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    service, trace_run = create_running_run(
        session,
        datetime(2026, 8, 2, 12, 0, 0),
    )

    with pytest.raises(ValueError, match="must not be blank"):
        service.fail_run(trace_run, error_message="   ")

    assert trace_run.status == TraceStatus.RUNNING.value
    assert trace_run.ended_at is None
    assert trace_run.error_message is None


def test_trace_service_rejects_missing_start_time_without_mutation(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    service, trace_run = create_running_run(
        session,
        datetime(2026, 8, 2, 12, 0, 0),
    )
    trace_run.started_at = None

    with pytest.raises(TraceStateError, match="missing started_at"):
        service.finish_run(trace_run)

    assert trace_run.status == TraceStatus.RUNNING.value
    assert trace_run.ended_at is None


def test_trace_service_clamps_clock_regression_to_zero(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    service, trace_run = create_running_run(
        session,
        datetime(2026, 8, 2, 12, 0, 1),
        datetime(2026, 8, 2, 12, 0, 0),
    )

    service.finish_run(trace_run)

    assert trace_run.latency_ms == 0
