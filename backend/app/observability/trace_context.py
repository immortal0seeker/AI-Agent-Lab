from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import UUID

from pydantic import JsonValue

from app.models.trace import TraceRun, TraceStep
from app.observability.trace_service import TraceService
from app.observability.trace_types import TraceStepType


_trace_run_id: ContextVar[UUID | None] = ContextVar(
    "trace_run_id",
    default=None,
)


def get_trace_run_id() -> UUID | None:
    return _trace_run_id.get()


@contextmanager
def bind_trace_run_id(trace_run_id: UUID) -> Iterator[None]:
    token = _trace_run_id.set(trace_run_id)
    try:
        yield
    finally:
        _trace_run_id.reset(token)


class TraceContext:
    def __init__(
        self,
        service: TraceService,
        trace_run: TraceRun,
    ) -> None:
        self._service = service
        self._trace_run = trace_run

    @contextmanager
    def activate(self) -> Iterator[TraceContext]:
        with bind_trace_run_id(self._trace_run.id):
            yield self

    @contextmanager
    def step(
        self,
        step_type: TraceStepType,
        *,
        name: str,
        input_json: dict[str, JsonValue] | None = None,
    ) -> Iterator[TraceStep]:
        with bind_trace_run_id(self._trace_run.id):
            trace_step = self._service.add_step(
                self._trace_run,
                step_type=step_type,
                name=name,
                input_json=input_json,
            )
            try:
                yield trace_step
            except Exception as exc:
                # 自动路径只记录异常类型，避免把敏感诊断写入 Trace。
                self._service.fail_step(
                    trace_step,
                    error_message=type(exc).__name__,
                )
                raise
            else:
                self._service.finish_step(
                    trace_step,
                    output_json=trace_step.output_json,
                )
