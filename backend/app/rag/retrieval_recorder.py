from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import JsonValue
from sqlalchemy.orm import Session

from app.models.retrieval import RagRetrievalCandidate, RagRetrievalRun
from app.models.trace import TraceRun, TraceStep
from app.observability.trace_service import TraceService
from app.observability.trace_types import TraceRunType, TraceStepType
from app.rag.retriever import RetrievalBatch
from app.rag.rag_prompt import RagPrompt
from app.schemas.rag import RagRetrievalRequest, RetrievalResult
from app.schemas.retrieval import (
    RagFinalAnswerStepInputMetadata,
    RagFinalAnswerStepOutputMetadata,
    RagPromptSourceMetadata,
    RagPromptStepInputMetadata,
    RagPromptStepOutputMetadata,
    RagRetrievalCandidateCreate,
    RagRetrievalRunCreate,
    RagRetrieveStepInputMetadata,
    RagRetrieveStepOutputMetadata,
)
from app.schemas.trace import TraceRunCreate


logger = logging.getLogger("app.rag_trace")

_CANDIDATE_PREVIEW_CHARACTERS = 500
_CHUNK_METADATA_KEYS = (
    "source_format",
    "start_char",
    "end_char",
    "heading_level",
)


@dataclass(frozen=True, slots=True)
class RAGRunSnapshot:
    run_type: TraceRunType
    input_text: str
    conversation_id: UUID | None
    provider: str | None
    model: str | None
    metadata_json: dict[str, object]
    started_at: datetime


@dataclass(slots=True)
class RAGTraceRun:
    record: TraceRun
    snapshot: RAGRunSnapshot


@dataclass(frozen=True, slots=True)
class RAGRetrievalSnapshot:
    run: RAGRunSnapshot
    input_metadata: RagRetrieveStepInputMetadata
    started_at: datetime


@dataclass(slots=True)
class RAGRetrievalTrace:
    run: RAGTraceRun
    step: TraceStep
    snapshot: RAGRetrievalSnapshot


@dataclass(slots=True)
class RAGRecordedRetrieval:
    trace: RAGRetrievalTrace
    record: RagRetrievalRun
    candidates: tuple[RagRetrievalCandidate, ...]
    results: tuple[RetrievalResult, ...]
    run_data: RagRetrievalRunCreate
    candidate_data: tuple[RagRetrievalCandidateCreate, ...]
    step_snapshot: RAGCompletedStepSnapshot


@dataclass(frozen=True, slots=True)
class RAGCompletedStepSnapshot:
    step_type: TraceStepType
    name: str
    input_json: dict[str, JsonValue]
    output_json: dict[str, JsonValue]
    started_at: datetime
    ended_at: datetime
    latency_ms: int


@dataclass(slots=True)
class RAGPromptTrace:
    retrieval: RAGRecordedRetrieval
    step: TraceStep
    prompt_version: str


@dataclass(slots=True)
class RAGRecordedPrompt:
    trace: RAGPromptTrace
    prompt: RagPrompt
    sources: tuple[RagPromptSourceMetadata, ...]
    step_snapshot: RAGCompletedStepSnapshot


@dataclass(slots=True)
class RAGFinalAnswerTrace:
    prompt: RAGRecordedPrompt
    step: TraceStep


class RAGTraceRecorder:
    def __init__(
        self,
        session: Session,
        *,
        trace_service: TraceService | None = None,
    ) -> None:
        self._session = session
        self._traces = trace_service or TraceService(session)

    def start_query_run(
        self,
        request: RagRetrievalRequest,
    ) -> RAGTraceRun:
        return self._start_run(
            run_type=TraceRunType.RAG_QUERY,
            input_text=request.query,
            conversation_id=None,
            user_message_id=None,
            provider=None,
            model=None,
            metadata_json={"strategy": "naive_vector"},
        )

    def attach_run(self, record: TraceRun) -> RAGTraceRun:
        if record.started_at is None:
            raise RuntimeError("RAG Trace start timestamp was not initialized")
        snapshot = RAGRunSnapshot(
            run_type=TraceRunType(record.run_type),
            input_text=record.input_text,
            conversation_id=record.conversation_id,
            provider=record.provider,
            model=record.model,
            metadata_json=deepcopy(record.metadata_json),
            started_at=record.started_at,
        )
        return RAGTraceRun(record=record, snapshot=snapshot)

    def start_retrieval(
        self,
        trace_run: RAGTraceRun,
        request: RagRetrievalRequest,
    ) -> RAGRetrievalTrace:
        input_metadata = RagRetrieveStepInputMetadata(
            knowledge_base_id=request.knowledge_base_id,
            strategy="naive_vector",
            top_k=request.top_k,
            score_threshold=request.score_threshold,
        )
        return self._start_retrieval_from_metadata(
            trace_run,
            input_metadata,
        )

    def complete_retrieval(
        self,
        retrieval: RAGRetrievalTrace,
        *,
        batch: RetrievalBatch,
        latency_ms: int,
    ) -> RAGRecordedRetrieval:
        input_metadata = retrieval.snapshot.input_metadata
        candidate_count = len(batch.results)
        run_data = RagRetrievalRunCreate(
            trace_run_id=retrieval.run.record.id,
            knowledge_base_id=input_metadata.knowledge_base_id,
            strategy_name=input_metadata.strategy,
            original_query=retrieval.run.snapshot.input_text,
            top_k=input_metadata.top_k,
            candidate_count=candidate_count,
            selected_count=candidate_count,
            score_threshold=input_metadata.score_threshold,
            latency_ms=latency_ms,
            metadata_filter_json={
                "knowledge_base_id": str(input_metadata.knowledge_base_id),
                "embedding_provider": batch.embedding_provider,
                "embedding_model": batch.embedding_model,
            },
            strategy_config_json={},
        )
        record = RagRetrievalRun(**run_data.model_dump(mode="python"))
        self._session.add(record)
        self._session.flush()

        candidate_data = tuple(
            self._build_candidate_data(record, result, rank)
            for rank, result in enumerate(batch.results, start=1)
        )
        candidates = tuple(
            RagRetrievalCandidate(**data.model_dump(mode="python"))
            for data in candidate_data
        )
        self._session.add_all(candidates)
        self._session.flush()

        output_metadata = RagRetrieveStepOutputMetadata(
            retrieval_run_id=record.id,
            candidate_count=candidate_count,
            selected_count=candidate_count,
        )
        self._traces.finish_step(
            retrieval.step,
            output_json=output_metadata.model_dump(mode="json"),
        )
        step_snapshot = self._snapshot_completed_step(
            retrieval.step,
            step_type=TraceStepType.RAG_RETRIEVE,
        )
        return RAGRecordedRetrieval(
            trace=retrieval,
            record=record,
            candidates=candidates,
            results=batch.results,
            run_data=run_data,
            candidate_data=candidate_data,
            step_snapshot=step_snapshot,
        )

    def start_prompt(
        self,
        retrieval: RAGRecordedRetrieval,
        *,
        prompt_version: str,
    ) -> RAGPromptTrace:
        input_metadata = RagPromptStepInputMetadata(
            prompt_version=prompt_version,
            retrieval_run_id=retrieval.record.id,
            candidate_count=len(retrieval.candidates),
        )
        step = self._traces.add_step(
            retrieval.trace.run.record,
            step_type=TraceStepType.BUILD_PROMPT,
            name="Build RAG prompt",
            input_json=input_metadata.model_dump(mode="json"),
        )
        return RAGPromptTrace(
            retrieval=retrieval,
            step=step,
            prompt_version=prompt_version,
        )

    def complete_prompt(
        self,
        prompt_trace: RAGPromptTrace,
        *,
        prompt: RagPrompt,
    ) -> RAGRecordedPrompt:
        source_metadata = tuple(
            self._build_prompt_source(prompt_trace.retrieval, source)
            for source in prompt.sources
        )
        output_metadata = RagPromptStepOutputMetadata(
            prompt_version=prompt_trace.prompt_version,
            context_characters=prompt.context_characters,
            used_source_count=len(source_metadata),
            sources=source_metadata,
        )
        self._traces.finish_step(
            prompt_trace.step,
            output_json=output_metadata.model_dump(mode="json"),
        )
        return RAGRecordedPrompt(
            trace=prompt_trace,
            prompt=prompt,
            sources=source_metadata,
            step_snapshot=self._snapshot_completed_step(
                prompt_trace.step,
                step_type=TraceStepType.BUILD_PROMPT,
            ),
        )

    def replay_completed_before_llm(
        self,
        failed_run: TraceRun,
        prompt: RAGRecordedPrompt,
    ) -> None:
        retrieval = prompt.trace.retrieval
        run_payload = retrieval.run_data.model_dump(mode="python")
        run_payload["trace_run_id"] = failed_run.id
        replayed_retrieval = RagRetrievalRun(
            id=retrieval.record.id,
            **run_payload,
        )
        replayed_candidates = tuple(
            RagRetrievalCandidate(**data.model_dump(mode="python"))
            for data in retrieval.candidate_data
        )
        self._session.add(replayed_retrieval)
        self._session.add_all(replayed_candidates)
        self._session.flush()
        self._replay_completed_step(
            failed_run,
            retrieval.step_snapshot,
        )
        self._replay_completed_step(
            failed_run,
            prompt.step_snapshot,
        )

    def start_final_answer(
        self,
        prompt: RAGRecordedPrompt,
    ) -> RAGFinalAnswerTrace:
        input_metadata = RagFinalAnswerStepInputMetadata(
            prompt_version=prompt.trace.prompt_version,
            retrieval_run_id=prompt.trace.retrieval.record.id,
            used_source_count=len(prompt.sources),
        )
        step = self._traces.add_step(
            prompt.trace.retrieval.trace.run.record,
            step_type=TraceStepType.FINAL_ANSWER,
            name="Record final RAG answer",
            input_json=input_metadata.model_dump(mode="json"),
        )
        return RAGFinalAnswerTrace(prompt=prompt, step=step)

    def complete_final_answer(
        self,
        final_trace: RAGFinalAnswerTrace,
        *,
        rag_query_id: UUID,
        answer_message_id: UUID,
        llm_call_id: UUID,
        answer_text: str,
    ) -> RAGTraceRun:
        output_metadata = RagFinalAnswerStepOutputMetadata(
            rag_query_id=rag_query_id,
            answer_message_id=answer_message_id,
            llm_call_id=llm_call_id,
            source_count=len(final_trace.prompt.sources),
            answer_characters=len(answer_text),
        )
        self._traces.finish_step(
            final_trace.step,
            output_json=output_metadata.model_dump(mode="json"),
        )
        trace_run = final_trace.prompt.trace.retrieval.trace.run
        self._traces.finish_run(trace_run.record, output_text=answer_text)
        return trace_run

    def finish_query(self, trace_run: RAGTraceRun) -> RAGTraceRun:
        self._traces.finish_run(trace_run.record)
        return trace_run

    def persist_retrieval_failure(
        self,
        retrieval: RAGRetrievalTrace,
        *,
        error: BaseException,
    ) -> TraceRun | None:
        snapshot = retrieval.snapshot
        try:
            self._session.rollback()
            failed_run = self._start_run(
                run_type=snapshot.run.run_type,
                input_text=snapshot.run.input_text,
                conversation_id=snapshot.run.conversation_id,
                user_message_id=None,
                provider=snapshot.run.provider,
                model=snapshot.run.model,
                metadata_json=deepcopy(snapshot.run.metadata_json),
            )
            failed_run.record.started_at = snapshot.run.started_at
            failed_retrieval = self._start_retrieval_from_metadata(
                failed_run,
                snapshot.input_metadata,
            )
            failed_retrieval.step.started_at = snapshot.started_at
            safe_error = type(error).__name__
            self._traces.fail_step(
                failed_retrieval.step,
                error_message=safe_error,
            )
            self._traces.fail_run(
                failed_run.record,
                error_message=safe_error,
            )
            self._session.commit()
            return failed_run.record
        except Exception as trace_exc:
            # 审计写入失败不能覆盖原始检索异常，也不能记录异常正文。
            try:
                self._session.rollback()
            except Exception:
                pass
            logger.error(
                "rag_trace_persistence_failed",
                extra={"exception_type": type(trace_exc).__name__},
            )
            return None

    def _start_run(
        self,
        *,
        run_type: TraceRunType,
        input_text: str,
        conversation_id: UUID | None,
        user_message_id: UUID | None,
        provider: str | None,
        model: str | None,
        metadata_json: dict[str, object],
    ) -> RAGTraceRun:
        record = self._traces.create_run(
            TraceRunCreate(
                run_type=run_type,
                input_text=input_text,
                conversation_id=conversation_id,
                user_message_id=user_message_id,
                provider=provider,
                model=model,
                metadata_json=metadata_json,
            )
        )
        if record.started_at is None:
            raise RuntimeError("RAG Trace start timestamp was not initialized")
        return RAGTraceRun(
            record=record,
            snapshot=RAGRunSnapshot(
                run_type=run_type,
                input_text=input_text,
                conversation_id=conversation_id,
                provider=provider,
                model=model,
                metadata_json=deepcopy(metadata_json),
                started_at=record.started_at,
            ),
        )

    def _start_retrieval_from_metadata(
        self,
        trace_run: RAGTraceRun,
        input_metadata: RagRetrieveStepInputMetadata,
    ) -> RAGRetrievalTrace:
        step = self._traces.add_step(
            trace_run.record,
            step_type=TraceStepType.RAG_RETRIEVE,
            name="Retrieve knowledge base",
            input_json=input_metadata.model_dump(mode="json"),
        )
        if step.started_at is None:
            raise RuntimeError(
                "RAG retrieval Trace start timestamp was not initialized"
            )
        return RAGRetrievalTrace(
            run=trace_run,
            step=step,
            snapshot=RAGRetrievalSnapshot(
                run=trace_run.snapshot,
                input_metadata=input_metadata,
                started_at=step.started_at,
            ),
        )

    @staticmethod
    def _build_candidate_data(
        record: RagRetrievalRun,
        result: object,
        rank: int,
    ) -> RagRetrievalCandidateCreate:
        if not isinstance(result, RetrievalResult):
            raise TypeError("retrieval batch contains an invalid result")
        chunk_metadata = {
            key: deepcopy(result.metadata[key])
            for key in _CHUNK_METADATA_KEYS
            if key in result.metadata
        }
        return RagRetrievalCandidateCreate(
            retrieval_run_id=record.id,
            document_id=result.document_id,
            chunk_id=result.chunk_id,
            rank=rank,
            final_rank=rank,
            source="dense",
            dense_score=result.score,
            selected=True,
            content_preview=_truncate_preview(result.content),
            metadata_json={
                "filename": result.filename,
                "chunk_index": result.chunk_index,
                "heading": result.heading,
                "page_number": result.page_number,
                "embedding_provider": result.embedding_provider,
                "embedding_model": result.embedding_model,
                "chunk_metadata": chunk_metadata,
            },
        )

    @staticmethod
    def _build_prompt_source(
        retrieval: RAGRecordedRetrieval,
        source: object,
    ) -> RagPromptSourceMetadata:
        from app.schemas.rag import RagSource

        if not isinstance(source, RagSource):
            raise TypeError("RAG prompt contains an invalid source")
        offset = source.source_index - 1
        if offset < 0 or offset >= len(retrieval.candidates):
            raise ValueError("RAG prompt source index is outside candidates")
        candidate = retrieval.candidates[offset]
        result = retrieval.results[offset]
        if (
            source.document_id != candidate.document_id
            or source.chunk_id != candidate.chunk_id
        ):
            raise ValueError("RAG prompt source does not match its candidate")
        return RagPromptSourceMetadata(
            source_index=source.source_index,
            candidate_id=candidate.id,
            document_id=source.document_id,
            chunk_id=source.chunk_id,
            included_characters=len(source.content),
            truncated=len(source.content) < len(result.content),
        )

    @staticmethod
    def _snapshot_completed_step(
        step: TraceStep,
        *,
        step_type: TraceStepType,
    ) -> RAGCompletedStepSnapshot:
        if (
            step.started_at is None
            or step.ended_at is None
            or step.latency_ms is None
            or step.output_json is None
        ):
            raise RuntimeError("completed RAG Trace step is incomplete")
        return RAGCompletedStepSnapshot(
            step_type=step_type,
            name=step.name,
            input_json=deepcopy(step.input_json),
            output_json=deepcopy(step.output_json),
            started_at=step.started_at,
            ended_at=step.ended_at,
            latency_ms=step.latency_ms,
        )

    def _replay_completed_step(
        self,
        failed_run: TraceRun,
        snapshot: RAGCompletedStepSnapshot,
    ) -> None:
        step = self._traces.add_step(
            failed_run,
            step_type=snapshot.step_type,
            name=snapshot.name,
            input_json=deepcopy(snapshot.input_json),
        )
        step.started_at = snapshot.started_at
        self._traces.finish_step(
            step,
            output_json=deepcopy(snapshot.output_json),
        )
        step.ended_at = snapshot.ended_at
        step.latency_ms = snapshot.latency_ms
        self._session.flush()


def _truncate_preview(value: str) -> str:
    if len(value) <= _CANDIDATE_PREVIEW_CHARACTERS:
        return value
    return f"{value[: _CANDIDATE_PREVIEW_CHARACTERS - 1]}…"
