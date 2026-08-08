from collections.abc import Iterator
import importlib
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import Document, DocumentChunk, KnowledgeBase, TraceRun


def load_retrieval_models() -> tuple[Any, Any]:
    try:
        module = importlib.import_module("app.models.retrieval")
    except ModuleNotFoundError:
        pytest.fail("RAG retrieval audit models are not implemented", pytrace=False)
    return module.RagRetrievalRun, module.RagRetrievalCandidate


@pytest.fixture
def db(tmp_path: Path) -> Iterator[tuple[Session, Engine, Any, Any]]:
    retrieval_run, retrieval_candidate = load_retrieval_models()
    engine = create_db_engine(f"sqlite:///{tmp_path / 'retrieval-models.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session, engine, retrieval_run, retrieval_candidate
    finally:
        session.close()
        engine.dispose()


def make_retrieval_run(trace_run: TraceRun, retrieval_run: Any) -> Any:
    return retrieval_run(
        trace_run=trace_run,
        knowledge_base_id=UUID(int=1),
        strategy_name="naive_vector",
        original_query="What is the architecture?",
        top_k=3,
        candidate_count=2,
        selected_count=2,
        score_threshold=0.5,
        latency_ms=7,
        metadata_filter_json={"embedding_provider": "mock"},
        strategy_config_json={},
    )


def make_candidate(
    retrieval: Any,
    candidate: Any,
    *,
    rank: int,
    final_rank: int | None = None,
) -> Any:
    return candidate(
        retrieval_run=retrieval,
        document_id=uuid4(),
        chunk_id=uuid4(),
        rank=rank,
        final_rank=rank if final_rank is None else final_rank,
        source="dense",
        dense_score=0.9 - (rank / 100),
        selected=True,
        content_preview=f"candidate {rank}",
        metadata_json={"filename": f"guide-{rank}.md"},
    )


def test_retrieval_models_are_exported() -> None:
    retrieval_run, retrieval_candidate = load_retrieval_models()
    models = importlib.import_module("app.models")

    assert models.RagRetrievalRun is retrieval_run
    assert models.RagRetrievalCandidate is retrieval_candidate


def test_retrieval_models_persist_ordered_relationships_and_defaults(
    db: tuple[Session, Engine, Any, Any],
) -> None:
    session, _, retrieval_run, retrieval_candidate = db
    trace = TraceRun(run_type="rag_query", input_text="Question")
    first = make_retrieval_run(trace, retrieval_run)
    first.candidates.extend(
        [
            make_candidate(first, retrieval_candidate, rank=2),
            make_candidate(first, retrieval_candidate, rank=1),
        ]
    )
    second = retrieval_run(
        trace_run=trace,
        knowledge_base_id=UUID(int=2),
        strategy_name="naive_vector",
        original_query="Second retrieval",
        top_k=5,
        candidate_count=0,
        selected_count=0,
        latency_ms=0,
    )
    session.add(trace)
    session.commit()
    trace_id = trace.id
    first_id = first.id
    session.expire_all()

    loaded_trace = session.get(TraceRun, trace_id)
    loaded_first = session.get(retrieval_run, first_id)

    assert loaded_trace is not None
    assert [item.id for item in loaded_trace.retrieval_runs] == [
        first_id,
        second.id,
    ]
    assert loaded_first is not None
    assert isinstance(loaded_first.id, UUID)
    assert [item.rank for item in loaded_first.candidates] == [1, 2]
    assert loaded_first.metadata_filter_json == {"embedding_provider": "mock"}
    assert loaded_first.strategy_config_json == {}
    assert loaded_first.candidates[0].sparse_score is None
    assert loaded_first.candidates[0].fused_score is None
    assert loaded_first.candidates[0].rerank_score is None
    assert loaded_first.created_at.tzinfo is None


def test_retrieval_json_defaults_are_isolated(
    db: tuple[Session, Engine, Any, Any],
) -> None:
    session, _, retrieval_run, retrieval_candidate = db
    first_trace = TraceRun(run_type="rag_query", input_text="First")
    second_trace = TraceRun(run_type="rag_query", input_text="Second")
    first = retrieval_run(
        trace_run=first_trace,
        knowledge_base_id=UUID(int=1),
        strategy_name="naive_vector",
        original_query="First",
        top_k=1,
        candidate_count=1,
        selected_count=1,
        latency_ms=0,
    )
    second = retrieval_run(
        trace_run=second_trace,
        knowledge_base_id=UUID(int=2),
        strategy_name="naive_vector",
        original_query="Second",
        top_k=1,
        candidate_count=0,
        selected_count=0,
        latency_ms=0,
    )
    item = make_candidate(first, retrieval_candidate, rank=1)
    session.add_all([first_trace, second_trace, item])
    session.flush()

    first.metadata_filter_json["scope"] = "first"
    item.metadata_json["scope"] = "candidate"

    assert second.metadata_filter_json == {}
    assert second.strategy_config_json == {}
    assert first.metadata_filter_json is not second.metadata_filter_json


def test_deleting_trace_cascades_retrieval_audit(
    db: tuple[Session, Engine, Any, Any],
) -> None:
    session, _, retrieval_run, retrieval_candidate = db
    trace = TraceRun(run_type="rag_query", input_text="Question")
    retrieval = make_retrieval_run(trace, retrieval_run)
    item = make_candidate(retrieval, retrieval_candidate, rank=1)
    session.add_all([trace, item])
    session.commit()
    retrieval_id = retrieval.id
    candidate_id = item.id

    session.delete(trace)
    session.commit()

    assert session.get(retrieval_run, retrieval_id) is None
    assert session.get(retrieval_candidate, candidate_id) is None


def test_deleting_document_and_chunk_preserves_retrieval_audit(
    db: tuple[Session, Engine, Any, Any],
) -> None:
    session, _, retrieval_run, retrieval_candidate = db
    knowledge_base_id = UUID(int=101)
    document_id = UUID(int=102)
    chunk_id = UUID(int=103)
    knowledge_base = KnowledgeBase(
        id=knowledge_base_id,
        name="Source retention",
    )
    document = Document(
        id=document_id,
        knowledge_base_id=knowledge_base_id,
        filename="guide.md",
        original_filename="guide.md",
        file_type="md",
        file_path="documents/source/guide.md",
        file_size=12,
        file_hash="a" * 64,
    )
    chunk = DocumentChunk(
        id=chunk_id,
        document_id=document_id,
        knowledge_base_id=knowledge_base_id,
        chunk_index=0,
        content="source content",
        token_count=3,
        char_count=14,
    )
    trace = TraceRun(run_type="rag_query", input_text="Question")
    retrieval = make_retrieval_run(trace, retrieval_run)
    item = retrieval_candidate(
        retrieval_run=retrieval,
        document_id=document_id,
        chunk_id=chunk_id,
        rank=1,
        final_rank=1,
        source="dense",
        dense_score=0.9,
        selected=True,
        content_preview="source content",
    )
    session.add_all([knowledge_base, document, chunk, trace, item])
    session.commit()
    retrieval_id = retrieval.id
    candidate_id = item.id

    session.delete(document)
    session.commit()
    session.expire_all()

    assert session.get(Document, document_id) is None
    assert session.get(DocumentChunk, chunk_id) is None
    assert session.get(retrieval_run, retrieval_id) is not None
    preserved = session.get(retrieval_candidate, candidate_id)
    assert preserved is not None
    assert preserved.document_id == document_id
    assert preserved.chunk_id == chunk_id


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("strategy_name", "   "),
        ("original_query", "   "),
        ("top_k", 0),
        ("top_k", 101),
        ("candidate_count", -1),
        ("candidate_count", 101),
        ("selected_count", -1),
        ("selected_count", 101),
        ("latency_ms", -1),
    ],
)
def test_retrieval_run_rejects_invalid_persisted_values(
    db: tuple[Session, Engine, Any, Any],
    field: str,
    invalid: object,
) -> None:
    session, _, retrieval_run, _ = db
    trace = TraceRun(run_type="rag_query", input_text="Question")
    values: dict[str, object] = {
        "trace_run": trace,
        "knowledge_base_id": UUID(int=1),
        "strategy_name": "naive_vector",
        "original_query": "Question",
        "top_k": 5,
        "candidate_count": 1,
        "selected_count": 1,
        "latency_ms": 0,
    }
    values[field] = invalid
    session.add(retrieval_run(**values))

    with pytest.raises(IntegrityError):
        session.commit()


def test_retrieval_run_rejects_selected_count_above_candidate_count(
    db: tuple[Session, Engine, Any, Any],
) -> None:
    session, _, retrieval_run, _ = db
    trace = TraceRun(run_type="rag_query", input_text="Question")
    session.add(
        retrieval_run(
            trace_run=trace,
            knowledge_base_id=UUID(int=1),
            strategy_name="naive_vector",
            original_query="Question",
            top_k=5,
            candidate_count=1,
            selected_count=2,
            latency_ms=0,
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("rank", 0),
        ("final_rank", 0),
        ("source", "unknown"),
        ("content_preview", "   "),
        ("content_preview", "x" * 501),
    ],
)
def test_retrieval_candidate_rejects_invalid_persisted_values(
    db: tuple[Session, Engine, Any, Any],
    field: str,
    invalid: object,
) -> None:
    session, _, retrieval_run, retrieval_candidate = db
    trace = TraceRun(run_type="rag_query", input_text="Question")
    retrieval = make_retrieval_run(trace, retrieval_run)
    values: dict[str, object] = {
        "retrieval_run": retrieval,
        "document_id": uuid4(),
        "chunk_id": uuid4(),
        "rank": 1,
        "final_rank": 1,
        "source": "dense",
        "dense_score": 0.9,
        "selected": True,
        "content_preview": "candidate",
    }
    values[field] = invalid
    session.add(retrieval_candidate(**values))

    with pytest.raises(IntegrityError):
        session.commit()


@pytest.mark.parametrize("duplicate_field", ["rank", "final_rank"])
def test_retrieval_candidate_rank_is_unique_within_run(
    db: tuple[Session, Engine, Any, Any],
    duplicate_field: str,
) -> None:
    session, _, retrieval_run, retrieval_candidate = db
    trace = TraceRun(run_type="rag_query", input_text="Question")
    retrieval = make_retrieval_run(trace, retrieval_run)
    first = make_candidate(retrieval, retrieval_candidate, rank=1)
    second = make_candidate(retrieval, retrieval_candidate, rank=2)
    if duplicate_field == "rank":
        second.rank = first.rank
    else:
        second.final_rank = first.final_rank
    session.add_all([first, second])

    with pytest.raises(IntegrityError):
        session.commit()
