import importlib
import logging
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import (
    KnowledgeBase,
    RagQuery,
    RagRetrievalCandidate,
    RagRetrievalRun,
    TraceRun,
    TraceStep,
)
from app.observability.trace_types import (
    TraceRunType,
    TraceStatus,
    TraceStepType,
)
from app.providers.embedding import EmbeddingProviderResponseError
from app.rag.retriever import RetrievalBatch
from app.rag.rag_prompt import RagPromptBuilder
from app.schemas.rag import RagRetrievalRequest, RetrievalResult


KNOWLEDGE_BASE_ID = UUID("00000000-0000-0000-0000-000000000001")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000002")
CHUNK_ID = UUID("00000000-0000-0000-0000-000000000003")


def load_recorder_module() -> ModuleType:
    try:
        return importlib.import_module("app.rag.retrieval_recorder")
    except ModuleNotFoundError:
        pytest.fail("RAGTraceRecorder is not implemented", pytrace=False)


@pytest.fixture
def trace_db(tmp_path: Path) -> Iterator[tuple[Session, Engine]]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'rag-trace.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session, engine
    finally:
        session.close()
        engine.dispose()


def make_request(*, top_k: int = 3) -> RagRetrievalRequest:
    return RagRetrievalRequest(
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        query="What is the architecture?",
        top_k=top_k,
        score_threshold=0.5,
    )


def make_result(
    *,
    content: str = "The workspace uses layered services.",
    metadata: dict[str, object] | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        document_id=DOCUMENT_ID,
        chunk_id=CHUNK_ID,
        embedding_provider="recording",
        embedding_model="synthetic-embedding",
        filename="guide.md",
        chunk_index=0,
        content=content,
        score=0.93,
        heading="Architecture",
        page_number=2,
        metadata=metadata
        or {
            "source_format": "md",
            "start_char": 0,
            "end_char": len(content),
            "heading_level": 1,
        },
    )


def make_batch(*results: RetrievalResult) -> RetrievalBatch:
    return RetrievalBatch(
        results=tuple(results),
        embedding_provider="recording",
        embedding_model="synthetic-embedding",
    )


def test_rag_trace_recorder_persists_bounded_ordered_retrieval_audit(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    module = load_recorder_module()
    recorder = module.RAGTraceRecorder(session)
    request = make_request()
    unsafe_content = "片" * 600
    batch = make_batch(
        make_result(
            content=unsafe_content,
            metadata={
                "source_format": "md",
                "start_char": 0,
                "end_char": 600,
                "heading_level": 1,
                "source_path": "C:/private/secret.txt",
                "unknown": {"secret": "synthetic-secret"},
            },
        )
    )

    run = recorder.start_query_run(request)
    retrieval = recorder.start_retrieval(run, request)
    recorded = recorder.complete_retrieval(
        retrieval,
        batch=batch,
        latency_ms=7,
    )
    completed = recorder.finish_query(run)
    session.commit()
    session.expire_all()

    stored_run = session.get(TraceRun, completed.record.id)
    stored_retrieval = session.get(RagRetrievalRun, recorded.record.id)
    stored_candidate = session.get(
        RagRetrievalCandidate,
        recorded.candidates[0].id,
    )

    assert stored_run is not None
    assert stored_run.run_type == TraceRunType.RAG_QUERY.value
    assert stored_run.status == TraceStatus.COMPLETED.value
    assert stored_run.input_text == request.query
    assert stored_run.metadata_json == {"strategy": "naive_vector"}
    assert [step.step_type for step in stored_run.steps] == [
        TraceStepType.RAG_RETRIEVE.value
    ]
    step = stored_run.steps[0]
    assert step.status == TraceStatus.COMPLETED.value
    assert step.input_json == {
        "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
        "strategy": "naive_vector",
        "top_k": 3,
        "score_threshold": 0.5,
    }
    assert step.output_json == {
        "retrieval_run_id": str(recorded.record.id),
        "candidate_count": 1,
        "selected_count": 1,
    }

    assert stored_retrieval is not None
    assert stored_retrieval.trace_run_id == stored_run.id
    assert stored_retrieval.knowledge_base_id == KNOWLEDGE_BASE_ID
    assert stored_retrieval.strategy_name == "naive_vector"
    assert stored_retrieval.original_query == request.query
    assert stored_retrieval.rewritten_query is None
    assert stored_retrieval.top_k == 3
    assert stored_retrieval.candidate_count == 1
    assert stored_retrieval.selected_count == 1
    assert stored_retrieval.score_threshold == 0.5
    assert stored_retrieval.latency_ms == 7
    assert stored_retrieval.metadata_filter_json == {
        "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
        "embedding_provider": "recording",
        "embedding_model": "synthetic-embedding",
    }
    assert stored_retrieval.strategy_config_json == {}

    assert stored_candidate is not None
    assert stored_candidate.rank == 1
    assert stored_candidate.final_rank == 1
    assert stored_candidate.source == "dense"
    assert stored_candidate.dense_score == 0.93
    assert stored_candidate.sparse_score is None
    assert stored_candidate.fused_score is None
    assert stored_candidate.rerank_score is None
    assert stored_candidate.selected is True
    assert len(stored_candidate.content_preview) == 500
    assert stored_candidate.content_preview.endswith("…")
    assert stored_candidate.metadata_json == {
        "filename": "guide.md",
        "chunk_index": 0,
        "heading": "Architecture",
        "page_number": 2,
        "embedding_provider": "recording",
        "embedding_model": "synthetic-embedding",
        "chunk_metadata": {
            "source_format": "md",
            "start_char": 0,
            "end_char": 600,
            "heading_level": 1,
        },
    }
    assert "private" not in repr(stored_candidate.metadata_json)
    assert "synthetic-secret" not in repr(stored_candidate.metadata_json)


def test_rag_trace_recorder_records_zero_hit_embedding_identity(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    recorder = load_recorder_module().RAGTraceRecorder(session)
    request = make_request(top_k=9)

    run = recorder.start_query_run(request)
    retrieval = recorder.start_retrieval(run, request)
    recorded = recorder.complete_retrieval(
        retrieval,
        batch=make_batch(),
        latency_ms=0,
    )
    recorder.finish_query(run)

    assert recorded.record.candidate_count == 0
    assert recorded.record.selected_count == 0
    assert recorded.candidates == ()
    assert recorded.record.metadata_filter_json == {
        "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
        "embedding_provider": "recording",
        "embedding_model": "synthetic-embedding",
    }


def test_rag_trace_recorder_records_prompt_sources_and_final_answer(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    recorder = load_recorder_module().RAGTraceRecorder(session)
    request = make_request()
    first = make_result(content="A" * 400)
    second = first.model_copy(
        update={
            "chunk_id": UUID(int=44),
            "document_id": UUID(int=45),
            "chunk_index": 1,
            "content": "B" * 40,
            "score": 0.82,
        }
    )
    run = recorder.start_query_run(request)
    retrieval_trace = recorder.start_retrieval(run, request)
    recorded_retrieval = recorder.complete_retrieval(
        retrieval_trace,
        batch=make_batch(first, second),
        latency_ms=3,
    )
    prompt_trace = recorder.start_prompt(
        recorded_retrieval,
        prompt_version="naive-rag-v1",
    )
    prompt = RagPromptBuilder(max_context_characters=128).build(
        query=request.query,
        retrieval_results=(first, second),
    )
    recorded_prompt = recorder.complete_prompt(prompt_trace, prompt=prompt)
    final_trace = recorder.start_final_answer(recorded_prompt)
    completed = recorder.complete_final_answer(
        final_trace,
        rag_query_id=UUID(int=50),
        answer_message_id=UUID(int=51),
        llm_call_id=UUID(int=52),
        answer_text="Grounded answer [1]",
    )

    assert completed.record.status == TraceStatus.COMPLETED.value
    assert completed.record.output_text == "Grounded answer [1]"
    assert [step.step_type for step in completed.record.steps] == [
        TraceStepType.RAG_RETRIEVE.value,
        TraceStepType.BUILD_PROMPT.value,
        TraceStepType.FINAL_ANSWER.value,
    ]
    prompt_step = completed.record.steps[1]
    assert prompt_step.input_json == {
        "prompt_version": "naive-rag-v1",
        "retrieval_run_id": str(recorded_retrieval.record.id),
        "candidate_count": 2,
    }
    assert prompt_step.output_json == {
        "prompt_version": "naive-rag-v1",
        "context_characters": prompt.context_characters,
        "used_source_count": 1,
        "sources": [
            {
                "source_index": 1,
                "candidate_id": str(recorded_retrieval.candidates[0].id),
                "document_id": str(DOCUMENT_ID),
                "chunk_id": str(CHUNK_ID),
                "included_characters": len(prompt.sources[0].content),
                "truncated": True,
            }
        ],
    }
    assert "A" * 40 not in repr(prompt_step.output_json)
    final_step = completed.record.steps[2]
    assert final_step.input_json == {
        "prompt_version": "naive-rag-v1",
        "retrieval_run_id": str(recorded_retrieval.record.id),
        "used_source_count": 1,
    }
    assert final_step.output_json == {
        "rag_query_id": str(UUID(int=50)),
        "answer_message_id": str(UUID(int=51)),
        "llm_call_id": str(UUID(int=52)),
        "source_count": 1,
        "answer_characters": len("Grounded answer [1]"),
    }
    assert "Grounded answer [1]" not in repr(final_step.output_json)


def test_rag_trace_recorder_success_never_commits(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    recorder = load_recorder_module().RAGTraceRecorder(session)
    request = make_request()

    run = recorder.start_query_run(request)
    retrieval = recorder.start_retrieval(run, request)
    recorder.complete_retrieval(
        retrieval,
        batch=make_batch(make_result()),
        latency_ms=1,
    )
    recorder.finish_query(run)
    session.rollback()

    assert session.scalar(select(func.count()).select_from(TraceRun)) == 0
    assert session.scalar(select(func.count()).select_from(TraceStep)) == 0
    assert session.scalar(
        select(func.count()).select_from(RagRetrievalRun)
    ) == 0


def test_rag_trace_recorder_persists_class_only_retrieval_failure(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    session.add(KnowledgeBase(id=KNOWLEDGE_BASE_ID, name="Project docs"))
    session.commit()
    recorder = load_recorder_module().RAGTraceRecorder(session)
    request = make_request()
    run = recorder.start_query_run(request)
    retrieval = recorder.start_retrieval(run, request)
    session.add(
        RagQuery(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            query=request.query,
            top_k=request.top_k,
            retrieved_chunks_json=[],
        )
    )
    session.flush()

    persisted = recorder.persist_retrieval_failure(
        retrieval,
        error=EmbeddingProviderResponseError(
            "private embedding diagnostic synthetic-secret"
        ),
    )

    assert persisted is not None
    assert session.scalar(select(func.count()).select_from(RagQuery)) == 0
    assert session.scalar(select(func.count()).select_from(TraceRun)) == 1
    assert session.scalar(select(func.count()).select_from(TraceStep)) == 1
    assert session.scalar(
        select(func.count()).select_from(RagRetrievalRun)
    ) == 0
    assert session.scalar(
        select(func.count()).select_from(RagRetrievalCandidate)
    ) == 0
    stored = session.scalar(select(TraceRun))
    assert stored is not None
    assert stored.status == TraceStatus.FAILED.value
    assert stored.error_message == "EmbeddingProviderResponseError"
    assert stored.user_message_id is None
    assert len(stored.steps) == 1
    assert stored.steps[0].status == TraceStatus.FAILED.value
    assert stored.steps[0].error_message == "EmbeddingProviderResponseError"
    assert stored.steps[0].output_json is None
    assert "private embedding diagnostic" not in repr(stored.__dict__)
    assert "synthetic-secret" not in repr(stored.steps[0].__dict__)


def test_rag_trace_recorder_never_masks_failure_when_rollback_fails(
    trace_db: tuple[Session, Engine],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session, _ = trace_db
    recorder = load_recorder_module().RAGTraceRecorder(session)
    request = make_request()
    run = recorder.start_query_run(request)
    retrieval = recorder.start_retrieval(run, request)

    def fail_rollback() -> None:
        raise RuntimeError("private rollback diagnostic")

    with monkeypatch.context() as patch_context:
        patch_context.setattr(session, "rollback", fail_rollback)
        with caplog.at_level(logging.ERROR, logger="app.rag_trace"):
            persisted = recorder.persist_retrieval_failure(
                retrieval,
                error=EmbeddingProviderResponseError(
                    "private embedding diagnostic"
                ),
            )

    session.rollback()
    assert persisted is None
    assert any(
        record.getMessage() == "rag_trace_persistence_failed"
        and record.exception_type == "RuntimeError"
        for record in caplog.records
    )
    assert "private rollback diagnostic" not in caplog.text
    assert "private embedding diagnostic" not in caplog.text
