import logging
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import Conversation, Message, TraceRun, TraceStep
from app.observability.llm_trace import LLMTraceRecorder
from app.observability.prompt_version import (
    CHAT_HISTORY_PROMPT_VERSION,
    NAIVE_RAG_PROMPT_VERSION,
)
from app.observability.token_cost import LLMCallMetrics
from app.observability.trace_service import TraceService
from app.observability.trace_types import (
    TraceRunType,
    TraceStatus,
    TraceStepType,
)
from app.providers.llm.base import ProviderRequestError
from app.schemas.trace import (
    LLMStepInputMetadata,
    LLMStepOutputMetadata,
    LLMStepUsageMetadata,
)


@pytest.fixture
def trace_db(tmp_path: Path) -> Iterator[tuple[Session, Engine]]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'llm-trace.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session, engine
    finally:
        session.close()
        engine.dispose()


def test_prompt_versions_are_stable() -> None:
    assert CHAT_HISTORY_PROMPT_VERSION == "chat-history-v1"
    assert NAIVE_RAG_PROMPT_VERSION == "naive-rag-v1"


def test_llm_step_metadata_serializes_exact_json_contract() -> None:
    input_metadata = LLMStepInputMetadata(
        provider="openai_compatible",
        requested_model="example-model",
        prompt_version=CHAT_HISTORY_PROMPT_VERSION,
        stream=False,
        message_count=1,
    )
    output_metadata = LLMStepOutputMetadata(
        provider="openai_compatible",
        model="resolved-model",
        prompt_version=CHAT_HISTORY_PROMPT_VERSION,
        usage=LLMStepUsageMetadata(
            input_tokens=5,
            output_tokens=3,
            total_tokens=8,
            estimated_cost="0.00000700",
        ),
        latency_ms=12,
    )

    assert input_metadata.model_dump(mode="json") == {
        "provider": "openai_compatible",
        "requested_model": "example-model",
        "prompt_version": "chat-history-v1",
        "stream": False,
        "message_count": 1,
    }
    assert output_metadata.model_dump(mode="json") == {
        "provider": "openai_compatible",
        "model": "resolved-model",
        "prompt_version": "chat-history-v1",
        "usage": {
            "input_tokens": 5,
            "output_tokens": 3,
            "total_tokens": 8,
            "estimated_cost": "0.00000700",
        },
        "latency_ms": 12,
    }


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (
            LLMStepInputMetadata,
            {
                "provider": "p",
                "requested_model": "m",
                "prompt_version": "v",
                "stream": False,
                "message_count": 0,
            },
        ),
        (
            LLMStepUsageMetadata,
            {
                "input_tokens": -1,
                "output_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": None,
            },
        ),
        (
            LLMStepUsageMetadata,
            {
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
                "estimated_cost": "0.1",
            },
        ),
        (
            LLMStepOutputMetadata,
            {
                "provider": "p",
                "model": "m",
                "prompt_version": "v",
                "usage": {
                    "input_tokens": None,
                    "output_tokens": None,
                    "total_tokens": None,
                    "estimated_cost": None,
                },
                "latency_ms": -1,
            },
        ),
    ],
)
def test_llm_step_metadata_rejects_invalid_values(
    schema: type[
        LLMStepInputMetadata | LLMStepUsageMetadata | LLMStepOutputMetadata
    ],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(payload)


def test_llm_step_metadata_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        LLMStepInputMetadata(
            provider="p",
            requested_model="m",
            prompt_version="v",
            stream=False,
            message_count=1,
            raw_prompt="must not be accepted",
        )


def test_llm_trace_recorder_completes_run_and_step_with_safe_metadata(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    conversation = Conversation(title="Trace conversation")
    session.add(conversation)
    session.flush()
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content="Hello",
    )
    session.add(user_message)
    session.flush()
    recorder = LLMTraceRecorder(session)

    trace_run = recorder.start_run(
        run_type=TraceRunType.CHAT,
        input_text="Hello",
        provider="openai_compatible",
        requested_model="example-model",
        prompt_version=CHAT_HISTORY_PROMPT_VERSION,
        stream=False,
        conversation_id=conversation.id,
        user_message_id=user_message.id,
    )
    trace_call = recorder.start_call(trace_run, message_count=1)
    completed = recorder.complete_call(
        trace_call,
        response_model="resolved-model",
        metrics=LLMCallMetrics(
            input_tokens=5,
            output_tokens=3,
            total_tokens=8,
            estimated_cost=Decimal("0.00000700"),
            latency_ms=12,
        ),
        output_text="Answer",
    )
    run_id = completed.id
    session.commit()
    session.expire_all()

    stored = session.get(TraceRun, run_id)
    assert stored is not None
    assert stored.status == TraceStatus.COMPLETED.value
    assert stored.run_type == TraceRunType.CHAT.value
    assert stored.conversation_id == conversation.id
    assert stored.user_message_id == user_message.id
    assert stored.provider == "openai_compatible"
    assert stored.model == "resolved-model"
    assert stored.total_input_tokens == 5
    assert stored.total_output_tokens == 3
    assert stored.total_tokens == 8
    assert stored.estimated_cost == Decimal("0.00000700")
    assert stored.output_text == "Answer"
    assert stored.metadata_json == {
        "prompt_version": "chat-history-v1",
        "stream": False,
    }
    assert len(stored.steps) == 1
    step = stored.steps[0]
    assert step.status == TraceStatus.COMPLETED.value
    assert step.step_type == TraceStepType.LLM_CALL.value
    assert step.input_json == {
        "provider": "openai_compatible",
        "requested_model": "example-model",
        "prompt_version": "chat-history-v1",
        "stream": False,
        "message_count": 1,
    }
    assert step.output_json == {
        "provider": "openai_compatible",
        "model": "resolved-model",
        "prompt_version": "chat-history-v1",
        "usage": {
            "input_tokens": 5,
            "output_tokens": 3,
            "total_tokens": 8,
            "estimated_cost": "0.00000700",
        },
        "latency_ms": 12,
    }


def test_llm_trace_recorder_can_complete_call_without_finishing_run(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    recorder = LLMTraceRecorder(session)
    trace_run = recorder.start_run(
        run_type=TraceRunType.RAG_CHAT,
        input_text="Question",
        provider="openai_compatible",
        requested_model="example-model",
        prompt_version=NAIVE_RAG_PROMPT_VERSION,
        stream=False,
        conversation_id=None,
        user_message_id=None,
    )
    trace_call = recorder.start_call(trace_run, message_count=2)

    completed = recorder.complete_call(
        trace_call,
        response_model="resolved-model",
        metrics=LLMCallMetrics(
            input_tokens=5,
            output_tokens=3,
            total_tokens=8,
            estimated_cost=Decimal("0.00000700"),
            latency_ms=12,
        ),
        output_text="Answer",
        finish_run=False,
    )

    assert completed.status == TraceStatus.RUNNING.value
    assert completed.model == "resolved-model"
    assert completed.total_tokens == 8
    assert completed.estimated_cost == Decimal("0.00000700")
    assert completed.output_text is None
    assert completed.ended_at is None
    assert trace_call.step.status == TraceStatus.COMPLETED.value
    assert trace_call.step.output_json is not None
    assert trace_call.step.output_json["usage"]["total_tokens"] == 8


def test_llm_trace_recorder_persists_class_only_failure_after_rollback(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    conversation = Conversation(title="Provisional conversation")
    session.add(conversation)
    session.flush()
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content="Sensitive prompt",
    )
    session.add(user_message)
    session.flush()
    recorder = LLMTraceRecorder(session)
    trace_run = recorder.start_run(
        run_type=TraceRunType.CHAT,
        input_text="Sensitive prompt",
        provider="openai_compatible",
        requested_model="example-model",
        prompt_version=CHAT_HISTORY_PROMPT_VERSION,
        stream=False,
        conversation_id=conversation.id,
        user_message_id=user_message.id,
    )
    trace_call = recorder.start_call(trace_run, message_count=1)

    persisted = recorder.persist_failure(
        trace_call,
        error=ProviderRequestError("synthetic secret diagnostic"),
        conversation_id=None,
    )

    assert persisted is not None
    assert session.scalar(select(func.count()).select_from(Conversation)) == 0
    assert session.scalar(select(func.count()).select_from(Message)) == 0
    assert session.scalar(select(func.count()).select_from(TraceRun)) == 1
    assert session.scalar(select(func.count()).select_from(TraceStep)) == 1
    stored = session.scalar(select(TraceRun))
    assert stored is not None
    assert stored.status == TraceStatus.FAILED.value
    assert stored.conversation_id is None
    assert stored.user_message_id is None
    assert stored.error_message == "ProviderRequestError"
    assert len(stored.steps) == 1
    step = stored.steps[0]
    assert step.status == TraceStatus.FAILED.value
    assert step.error_message == "ProviderRequestError"
    assert step.output_json is None
    serialized_trace = repr(
        {
            "run_error": stored.error_message,
            "run_metadata": stored.metadata_json,
            "step_error": step.error_message,
            "step_input": step.input_json,
            "step_output": step.output_json,
        }
    )
    assert "synthetic secret diagnostic" not in serialized_trace


def test_llm_trace_failure_runs_safe_replay_before_failed_call(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    recorder = LLMTraceRecorder(session)
    trace_run = recorder.start_run(
        run_type=TraceRunType.RAG_CHAT,
        input_text="Question",
        provider="openai_compatible",
        requested_model="example-model",
        prompt_version=NAIVE_RAG_PROMPT_VERSION,
        stream=False,
        conversation_id=None,
        user_message_id=None,
    )
    trace_call = recorder.start_call(trace_run, message_count=2)
    replayed_run_ids = []

    def replay_before_call(failed_run: object) -> None:
        replayed_run_ids.append(failed_run.record.id)
        trace_service = TraceService(session)
        step = trace_service.add_step(
            failed_run.record,
            step_type=TraceStepType.RAG_RETRIEVE,
            name="Replay retrieval",
            input_json={"strategy": "naive_vector"},
        )
        trace_service.finish_step(step, output_json={"candidate_count": 1})

    persisted = recorder.persist_failure(
        trace_call,
        error=ProviderRequestError("private provider diagnostic"),
        conversation_id=None,
        before_failed_call=replay_before_call,
    )

    assert persisted is not None
    assert replayed_run_ids == [persisted.id]
    stored = session.get(TraceRun, persisted.id)
    assert stored is not None
    assert [step.step_type for step in stored.steps] == [
        TraceStepType.RAG_RETRIEVE.value,
        TraceStepType.LLM_CALL.value,
    ]
    assert [step.status for step in stored.steps] == [
        TraceStatus.COMPLETED.value,
        TraceStatus.FAILED.value,
    ]
    assert stored.error_message == "ProviderRequestError"
    assert "private provider diagnostic" not in repr(stored.__dict__)


def test_llm_trace_recorder_never_masks_provider_error_when_rollback_fails(
    trace_db: tuple[Session, Engine],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session, _ = trace_db
    conversation = Conversation(title="Provisional conversation")
    session.add(conversation)
    session.flush()
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content="Hello",
    )
    session.add(user_message)
    session.flush()
    recorder = LLMTraceRecorder(session)
    trace_run = recorder.start_run(
        run_type=TraceRunType.CHAT,
        input_text="Hello",
        provider="openai_compatible",
        requested_model="example-model",
        prompt_version=CHAT_HISTORY_PROMPT_VERSION,
        stream=False,
        conversation_id=conversation.id,
        user_message_id=user_message.id,
    )
    trace_call = recorder.start_call(trace_run, message_count=1)

    def fail_rollback() -> None:
        raise RuntimeError("private rollback diagnostic")

    with monkeypatch.context() as patch_context:
        patch_context.setattr(session, "rollback", fail_rollback)
        with caplog.at_level(logging.ERROR, logger="app.llm_trace"):
            result = recorder.persist_failure(
                trace_call,
                error=ProviderRequestError("private provider diagnostic"),
                conversation_id=None,
            )

    session.rollback()
    assert result is None
    assert any(
        record.getMessage() == "llm_trace_persistence_failed"
        and record.exception_type == "RuntimeError"
        for record in caplog.records
    )
    assert "private rollback diagnostic" not in caplog.text
    assert "private provider diagnostic" not in caplog.text
