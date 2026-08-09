from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import RagRetrievalCandidate, RagRetrievalRun, TraceRun, TraceStep
from app.services.trace_query_service import TraceQueryService, TraceRunNotFoundError


TRACE_ID = UUID(int=10)
RETRIEVAL_A = UUID(int=20)
RETRIEVAL_B = UUID(int=30)
CREATED_AT = datetime(2026, 8, 9, 12, 0, 0)


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'trace-query.db'}")
    Base.metadata.create_all(engine)
    db_session = Session(engine)
    try:
        yield db_session
    finally:
        db_session.close()
        engine.dispose()


def test_trace_query_service_returns_empty_list(session: Session) -> None:
    assert TraceQueryService(session).list_trace_runs(limit=50) == []


def test_trace_query_service_lists_deterministically_with_unicode_preview(
    session: Session,
) -> None:
    lower_id = TraceRun(
        id=UUID(int=1),
        run_type="chat",
        input_text="older by id",
        status="completed",
        created_at=CREATED_AT,
    )
    higher_id = TraceRun(
        id=UUID(int=2),
        run_type="rag_chat",
        input_text="界" * 161,
        status="failed",
        error_message="Safe failure",
        created_at=CREATED_AT,
    )
    session.add_all([lower_id, higher_id])
    session.commit()

    items = TraceQueryService(session).list_trace_runs(limit=1)

    assert [item.record.id for item in items] == [higher_id.id]
    assert items[0].input_preview == ("界" * 159) + "…"
    assert len(items[0].input_preview) == 160


def test_trace_query_service_returns_deterministic_nested_detail(
    session: Session,
) -> None:
    trace = TraceRun(
        id=TRACE_ID,
        run_type="rag_query",
        input_text="Where is the design?",
        status="completed",
        created_at=CREATED_AT,
    )
    trace.steps.extend(
        [
            TraceStep(
                id=UUID(int=42),
                step_index=2,
                step_type="build_prompt",
                name="Build prompt",
                status="completed",
                created_at=CREATED_AT,
            ),
            TraceStep(
                id=UUID(int=41),
                step_index=1,
                step_type="rag_retrieve",
                name="Retrieve",
                status="completed",
                created_at=CREATED_AT,
            ),
        ]
    )
    retrieval_b = RagRetrievalRun(
        id=RETRIEVAL_B,
        knowledge_base_id=UUID(int=101),
        strategy_name="naive_vector",
        original_query="Second retrieval",
        top_k=2,
        candidate_count=0,
        selected_count=0,
        latency_ms=1,
        created_at=CREATED_AT,
    )
    retrieval_a = RagRetrievalRun(
        id=RETRIEVAL_A,
        knowledge_base_id=UUID(int=100),
        strategy_name="naive_vector",
        original_query="First retrieval",
        top_k=2,
        candidate_count=2,
        selected_count=2,
        latency_ms=2,
        created_at=CREATED_AT,
    )
    retrieval_a.candidates.extend(
        [
            RagRetrievalCandidate(
                id=UUID(int=52),
                document_id=UUID(int=62),
                chunk_id=UUID(int=72),
                rank=2,
                final_rank=2,
                source="dense",
                dense_score=0.8,
                selected=True,
                content_preview="Second candidate",
                created_at=CREATED_AT,
            ),
            RagRetrievalCandidate(
                id=UUID(int=51),
                document_id=UUID(int=61),
                chunk_id=UUID(int=71),
                rank=1,
                final_rank=1,
                source="dense",
                dense_score=0.9,
                selected=True,
                content_preview="First candidate",
                created_at=CREATED_AT,
            ),
        ]
    )
    trace.retrieval_runs.extend([retrieval_b, retrieval_a])
    session.add(trace)
    session.commit()
    session.expire_all()

    statements: list[str] = []

    def record_statement(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        statements.append(statement)

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", record_statement)
    try:
        detail = TraceQueryService(session).get_trace_detail(TRACE_ID)
    finally:
        event.remove(engine, "before_cursor_execute", record_statement)

    assert [step.step_index for step in detail.steps] == [1, 2]
    assert [item.record.id for item in detail.retrievals] == [
        RETRIEVAL_A,
        RETRIEVAL_B,
    ]
    assert [row.rank for row in detail.retrievals[0].candidates] == [1, 2]
    assert detail.retrievals[1].candidates == ()
    assert len(statements) == 4


def test_trace_query_service_raises_safe_not_found(session: Session) -> None:
    missing_id = uuid4()

    with pytest.raises(TraceRunNotFoundError) as error:
        TraceQueryService(session).get_trace_detail(missing_id)

    assert error.value.trace_run_id == missing_id
    assert str(error.value) == "Trace run not found"
