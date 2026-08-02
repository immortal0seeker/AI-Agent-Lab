from collections.abc import Callable
from datetime import datetime

from pydantic import JsonValue
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.common import utc_now
from app.models.trace import TraceRun, TraceStep
from app.observability.trace_types import TraceStatus, TraceStepType
from app.schemas.trace import TraceRunCreate, TraceStepCreate


class TraceStateError(RuntimeError):
    """Trace 生命周期状态不允许当前操作。"""


class TraceService:
    def __init__(
        self,
        session: Session,
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._session = session
        self._clock = clock

    def create_run(self, data: TraceRunCreate) -> TraceRun:
        if data.status is not TraceStatus.PENDING:
            raise TraceStateError(
                "TraceRun creation requires pending status"
            )
        payload = data.model_dump(mode="python")
        payload["run_type"] = data.run_type.value
        payload["status"] = TraceStatus.RUNNING.value
        trace_run = TraceRun(
            **payload,
            started_at=self._clock(),
        )
        self._session.add(trace_run)
        self._session.flush()
        return trace_run

    def add_step(
        self,
        trace_run: TraceRun,
        *,
        step_type: TraceStepType,
        name: str,
        input_json: dict[str, JsonValue] | None = None,
    ) -> TraceStep:
        self._require_running("TraceRun", trace_run.status)
        next_index = (
            self._session.scalar(
                select(func.max(TraceStep.step_index)).where(
                    TraceStep.trace_run_id == trace_run.id
                )
            )
            or 0
        ) + 1
        data = TraceStepCreate(
            trace_run_id=trace_run.id,
            step_index=next_index,
            step_type=step_type,
            name=name,
            status=TraceStatus.RUNNING,
            input_json=input_json or {},
        )
        payload = data.model_dump(mode="python")
        payload["step_type"] = data.step_type.value
        payload["status"] = data.status.value
        trace_step = TraceStep(
            **payload,
            started_at=self._clock(),
        )
        self._session.add(trace_step)
        self._session.flush()
        return trace_step

    def finish_run(
        self,
        trace_run: TraceRun,
        *,
        output_text: str | None = None,
    ) -> TraceRun:
        self._require_running("TraceRun", trace_run.status)
        started_at = self._require_started(
            "TraceRun",
            trace_run.started_at,
        )
        ended_at = self._clock()
        trace_run.status = TraceStatus.COMPLETED.value
        trace_run.output_text = output_text
        trace_run.error_message = None
        trace_run.ended_at = ended_at
        trace_run.latency_ms = self._latency_ms(started_at, ended_at)
        self._session.flush()
        return trace_run

    def fail_run(
        self,
        trace_run: TraceRun,
        *,
        error_message: str,
    ) -> TraceRun:
        self._require_running("TraceRun", trace_run.status)
        safe_error = self._normalize_error(error_message)
        started_at = self._require_started(
            "TraceRun",
            trace_run.started_at,
        )
        ended_at = self._clock()
        trace_run.status = TraceStatus.FAILED.value
        trace_run.output_text = None
        trace_run.error_message = safe_error
        trace_run.ended_at = ended_at
        trace_run.latency_ms = self._latency_ms(started_at, ended_at)
        self._session.flush()
        return trace_run

    def finish_step(
        self,
        trace_step: TraceStep,
        *,
        output_json: dict[str, JsonValue] | None = None,
    ) -> TraceStep:
        self._require_running("TraceStep", trace_step.status)
        started_at = self._require_started(
            "TraceStep",
            trace_step.started_at,
        )
        ended_at = self._clock()
        trace_step.status = TraceStatus.COMPLETED.value
        trace_step.output_json = output_json
        trace_step.error_message = None
        trace_step.ended_at = ended_at
        trace_step.latency_ms = self._latency_ms(started_at, ended_at)
        self._session.flush()
        return trace_step

    def fail_step(
        self,
        trace_step: TraceStep,
        *,
        error_message: str,
    ) -> TraceStep:
        self._require_running("TraceStep", trace_step.status)
        safe_error = self._normalize_error(error_message)
        started_at = self._require_started(
            "TraceStep",
            trace_step.started_at,
        )
        ended_at = self._clock()
        trace_step.status = TraceStatus.FAILED.value
        trace_step.output_json = None
        trace_step.error_message = safe_error
        trace_step.ended_at = ended_at
        trace_step.latency_ms = self._latency_ms(started_at, ended_at)
        self._session.flush()
        return trace_step

    @staticmethod
    def _require_running(record_type: str, status: str) -> None:
        if status != TraceStatus.RUNNING.value:
            raise TraceStateError(
                f"{record_type} must be running; current status: {status}"
            )

    @staticmethod
    def _require_started(
        record_type: str,
        started_at: datetime | None,
    ) -> datetime:
        if started_at is None:
            raise TraceStateError(f"{record_type} is missing started_at")
        return started_at

    @staticmethod
    def _normalize_error(error_message: str) -> str:
        normalized = error_message.strip()
        if not normalized:
            raise ValueError("error_message must not be blank")
        return normalized

    @staticmethod
    def _latency_ms(started_at: datetime, ended_at: datetime) -> int:
        return max(
            0,
            round((ended_at - started_at).total_seconds() * 1000),
        )
