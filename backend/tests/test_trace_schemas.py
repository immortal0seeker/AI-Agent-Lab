from datetime import datetime
from decimal import Decimal
import importlib
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError


def load_trace_contracts() -> tuple[Any, Any]:
    try:
        trace_types = importlib.import_module("app.observability.trace_types")
        trace_schemas = importlib.import_module("app.schemas.trace")
    except ModuleNotFoundError:
        pytest.fail("Trace schemas are not implemented", pytrace=False)
    return trace_types, trace_schemas


def valid_run_read_data() -> dict[str, object]:
    return {
        "id": uuid4(),
        "run_type": "rag_query",
        "conversation_id": None,
        "agent_run_id": None,
        "user_message_id": None,
        "title": None,
        "input_text": "Why provider abstraction?",
        "output_text": None,
        "provider": None,
        "model": None,
        "status": "running",
        "total_input_tokens": None,
        "total_output_tokens": None,
        "total_tokens": None,
        "estimated_cost": None,
        "latency_ms": None,
        "error_message": None,
        "metadata_json": {},
        "started_at": datetime(2026, 8, 2, 12, 0, 0),
        "ended_at": None,
        "created_at": datetime(2026, 8, 2, 12, 0, 0),
    }


def test_trace_run_schema_serializes_enum_and_uuid_values() -> None:
    trace_types, trace_schemas = load_trace_contracts()
    conversation_id = uuid4()

    payload = trace_schemas.TraceRunCreate(
        run_type=trace_types.TraceRunType.RAG_QUERY,
        conversation_id=conversation_id,
        input_text="Why provider abstraction?",
        metadata_json={"strategy": "naive_vector"},
    )

    assert payload.model_dump(mode="json") == {
        "run_type": "rag_query",
        "conversation_id": str(conversation_id),
        "agent_run_id": None,
        "user_message_id": None,
        "title": None,
        "input_text": "Why provider abstraction?",
        "provider": None,
        "model": None,
        "status": "pending",
        "metadata_json": {"strategy": "naive_vector"},
    }


def test_trace_json_defaults_are_isolated() -> None:
    trace_types, trace_schemas = load_trace_contracts()
    first_run = trace_schemas.TraceRunCreate(
        run_type=trace_types.TraceRunType.CHAT,
        input_text="first",
    )
    second_run = trace_schemas.TraceRunCreate(
        run_type=trace_types.TraceRunType.CHAT,
        input_text="second",
    )
    first_step = trace_schemas.TraceStepCreate(
        trace_run_id=uuid4(),
        step_index=1,
        step_type=trace_types.TraceStepType.BUILD_CONTEXT,
        name="Build context",
    )
    second_step = trace_schemas.TraceStepCreate(
        trace_run_id=uuid4(),
        step_index=1,
        step_type=trace_types.TraceStepType.BUILD_CONTEXT,
        name="Build context",
    )

    first_run.metadata_json["source"] = "first"
    first_step.input_json["query"] = "first"

    assert second_run.metadata_json == {}
    assert second_step.input_json == {}
    assert first_run.metadata_json is not second_run.metadata_json
    assert first_step.input_json is not second_step.input_json


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"run_type": "unknown"}, "run_type"),
        ({"status": "unknown"}, "status"),
        ({"input_text": "   "}, "input_text"),
        ({"provider": "   "}, "provider"),
        ({"model": "   "}, "model"),
        ({"unexpected": True}, "unexpected"),
    ],
)
def test_trace_run_create_rejects_invalid_values(
    overrides: dict[str, object],
    match: str,
) -> None:
    _, trace_schemas = load_trace_contracts()
    values: dict[str, object] = {
        "run_type": "chat",
        "input_text": "hello",
    }
    values.update(overrides)

    with pytest.raises(ValidationError, match=match):
        trace_schemas.TraceRunCreate.model_validate(values)


@pytest.mark.parametrize("correlation_field", ["agent_run_id", "user_message_id"])
def test_trace_run_correlation_requires_conversation(
    correlation_field: str,
) -> None:
    _, trace_schemas = load_trace_contracts()

    with pytest.raises(ValidationError, match="conversation_id"):
        trace_schemas.TraceRunCreate.model_validate(
            {
                "run_type": "agent",
                "input_text": "hello",
                correlation_field: uuid4(),
            }
        )


@pytest.mark.parametrize(
    "field",
    [
        "total_input_tokens",
        "total_output_tokens",
        "total_tokens",
        "latency_ms",
    ],
)
@pytest.mark.parametrize("invalid", [-1, True, 1.5])
def test_trace_run_read_rejects_invalid_integer_metrics(
    field: str,
    invalid: object,
) -> None:
    _, trace_schemas = load_trace_contracts()
    values = valid_run_read_data()
    values[field] = invalid

    with pytest.raises(ValidationError, match=field):
        trace_schemas.TraceRunRead.model_validate(values)


def test_trace_run_read_preserves_exact_non_negative_cost() -> None:
    _, trace_schemas = load_trace_contracts()
    values = valid_run_read_data()
    values["estimated_cost"] = Decimal("0.00000001")

    payload = trace_schemas.TraceRunRead.model_validate(values)

    assert payload.estimated_cost == Decimal("0.00000001")


def test_trace_run_read_rejects_negative_cost() -> None:
    _, trace_schemas = load_trace_contracts()
    values = valid_run_read_data()
    values["estimated_cost"] = Decimal("-0.00000001")

    with pytest.raises(ValidationError, match="estimated_cost"):
        trace_schemas.TraceRunRead.model_validate(values)


def test_trace_step_schema_serializes_contract() -> None:
    trace_types, trace_schemas = load_trace_contracts()
    trace_run_id = uuid4()

    payload = trace_schemas.TraceStepCreate(
        trace_run_id=trace_run_id,
        step_index=1,
        step_type=trace_types.TraceStepType.RAG_RETRIEVE,
        name="Retrieve sources",
        input_json={"top_k": 5},
    )

    assert payload.model_dump(mode="json") == {
        "trace_run_id": str(trace_run_id),
        "step_index": 1,
        "step_type": "rag_retrieve",
        "name": "Retrieve sources",
        "status": "pending",
        "input_json": {"top_k": 5},
    }


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"step_index": 0}, "step_index"),
        ({"step_index": True}, "step_index"),
        ({"step_type": "unknown"}, "step_type"),
        ({"status": "unknown"}, "status"),
        ({"name": "   "}, "name"),
        ({"unexpected": True}, "unexpected"),
    ],
)
def test_trace_step_create_rejects_invalid_values(
    overrides: dict[str, object],
    match: str,
) -> None:
    _, trace_schemas = load_trace_contracts()
    values: dict[str, object] = {
        "trace_run_id": uuid4(),
        "step_index": 1,
        "step_type": "llm_call",
        "name": "Call model",
    }
    values.update(overrides)

    with pytest.raises(ValidationError, match=match):
        trace_schemas.TraceStepCreate.model_validate(values)


def test_trace_read_schemas_accept_orm_attributes() -> None:
    trace_types, trace_schemas = load_trace_contracts()
    run_values = valid_run_read_data()
    run = trace_schemas.TraceRunRead.model_validate(SimpleNamespace(**run_values))
    step = trace_schemas.TraceStepRead.model_validate(
        SimpleNamespace(
            id=uuid4(),
            trace_run_id=run.id,
            step_index=1,
            step_type="rag_retrieve",
            name="Retrieve sources",
            status="completed",
            input_json={"top_k": 5},
            output_json={"result_count": 2},
            error_message=None,
            latency_ms=12,
            started_at=datetime(2026, 8, 2, 12, 0, 0),
            ended_at=datetime(2026, 8, 2, 12, 0, 0),
            created_at=datetime(2026, 8, 2, 12, 0, 0),
        )
    )

    assert run.status is trace_types.TraceStatus.RUNNING
    assert step.step_type is trace_types.TraceStepType.RAG_RETRIEVE
    assert step.status is trace_types.TraceStatus.COMPLETED
