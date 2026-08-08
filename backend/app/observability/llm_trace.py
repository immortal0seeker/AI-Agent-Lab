import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.trace import TraceRun, TraceStep
from app.observability.token_cost import LLMCallMetrics
from app.observability.trace_service import TraceService
from app.observability.trace_types import TraceRunType, TraceStepType
from app.schemas.trace import (
    LLMStepInputMetadata,
    LLMStepOutputMetadata,
    LLMStepUsageMetadata,
    TraceRunCreate,
)


logger = logging.getLogger("app.llm_trace")


@dataclass(frozen=True, slots=True)
class LLMTraceSnapshot:
    run_type: TraceRunType
    input_text: str
    provider: str
    requested_model: str
    prompt_version: str
    stream: bool
    message_count: int
    run_started_at: datetime
    step_started_at: datetime


@dataclass(slots=True)
class LLMTraceRun:
    record: TraceRun
    run_type: TraceRunType
    input_text: str
    provider: str
    requested_model: str
    prompt_version: str
    stream: bool


@dataclass(slots=True)
class LLMTraceCall:
    run: LLMTraceRun
    step: TraceStep
    snapshot: LLMTraceSnapshot


class LLMTraceRecorder:
    def __init__(
        self,
        session: Session,
        *,
        trace_service: TraceService | None = None,
    ) -> None:
        self._session = session
        self._traces = trace_service or TraceService(session)

    def start_run(
        self,
        *,
        run_type: TraceRunType,
        input_text: str,
        provider: str,
        requested_model: str,
        prompt_version: str,
        stream: bool,
        conversation_id: UUID | None,
        user_message_id: UUID | None,
    ) -> LLMTraceRun:
        record = self._traces.create_run(
            TraceRunCreate(
                run_type=run_type,
                conversation_id=conversation_id,
                user_message_id=user_message_id,
                input_text=input_text,
                provider=provider,
                model=requested_model,
                metadata_json={
                    "prompt_version": prompt_version,
                    "stream": stream,
                },
            )
        )
        return LLMTraceRun(
            record=record,
            run_type=run_type,
            input_text=input_text,
            provider=provider,
            requested_model=requested_model,
            prompt_version=prompt_version,
            stream=stream,
        )

    def start_call(
        self,
        trace_run: LLMTraceRun,
        *,
        message_count: int,
    ) -> LLMTraceCall:
        input_metadata = LLMStepInputMetadata(
            provider=trace_run.provider,
            requested_model=trace_run.requested_model,
            prompt_version=trace_run.prompt_version,
            stream=trace_run.stream,
            message_count=message_count,
        )
        step = self._traces.add_step(
            trace_run.record,
            step_type=TraceStepType.LLM_CALL,
            name="Call LLM",
            input_json=input_metadata.model_dump(mode="json"),
        )
        if trace_run.record.started_at is None or step.started_at is None:
            raise RuntimeError("LLM Trace start timestamps were not initialized")
        return LLMTraceCall(
            run=trace_run,
            step=step,
            snapshot=LLMTraceSnapshot(
                run_type=trace_run.run_type,
                input_text=trace_run.input_text,
                provider=trace_run.provider,
                requested_model=trace_run.requested_model,
                prompt_version=trace_run.prompt_version,
                stream=trace_run.stream,
                message_count=message_count,
                run_started_at=trace_run.record.started_at,
                step_started_at=step.started_at,
            ),
        )

    def complete_call(
        self,
        trace_call: LLMTraceCall,
        *,
        response_model: str,
        metrics: LLMCallMetrics,
        output_text: str,
    ) -> TraceRun:
        usage = LLMStepUsageMetadata(
            input_tokens=metrics.input_tokens,
            output_tokens=metrics.output_tokens,
            total_tokens=metrics.total_tokens,
            estimated_cost=(
                format(metrics.estimated_cost, "f")
                if metrics.estimated_cost is not None
                else None
            ),
        )
        output_metadata = LLMStepOutputMetadata(
            provider=trace_call.run.provider,
            model=response_model,
            prompt_version=trace_call.run.prompt_version,
            usage=usage,
            latency_ms=metrics.latency_ms,
        )
        self._traces.finish_step(
            trace_call.step,
            output_json=output_metadata.model_dump(mode="json"),
        )
        record = trace_call.run.record
        record.model = response_model
        record.total_input_tokens = metrics.input_tokens
        record.total_output_tokens = metrics.output_tokens
        record.total_tokens = metrics.total_tokens
        record.estimated_cost = metrics.estimated_cost
        self._traces.finish_run(record, output_text=output_text)
        return record

    def persist_failure(
        self,
        trace_call: LLMTraceCall,
        *,
        error: BaseException,
        conversation_id: UUID | None,
    ) -> TraceRun | None:
        snapshot = trace_call.snapshot
        try:
            self._session.rollback()
            failed_run = self.start_run(
                run_type=snapshot.run_type,
                input_text=snapshot.input_text,
                provider=snapshot.provider,
                requested_model=snapshot.requested_model,
                prompt_version=snapshot.prompt_version,
                stream=snapshot.stream,
                conversation_id=conversation_id,
                user_message_id=None,
            )
            failed_call = self.start_call(
                failed_run,
                message_count=snapshot.message_count,
            )
            failed_run.record.started_at = snapshot.run_started_at
            failed_call.step.started_at = snapshot.step_started_at
            safe_error = type(error).__name__
            self._traces.fail_step(
                failed_call.step,
                error_message=safe_error,
            )
            self._traces.fail_run(
                failed_run.record,
                error_message=safe_error,
            )
            self._session.commit()
            return failed_run.record
        except Exception as trace_exc:
            # Trace 是审计旁路，写入失败不能覆盖原始 Provider 异常。
            try:
                self._session.rollback()
            except Exception:
                pass
            logger.error(
                "llm_trace_persistence_failed",
                extra={"exception_type": type(trace_exc).__name__},
            )
            return None
