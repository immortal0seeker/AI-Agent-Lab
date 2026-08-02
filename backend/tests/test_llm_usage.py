from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import TraceStep
from app.observability.token_cost import (
    LLMCallMetrics as ObservabilityMetrics,
)
from app.observability.token_cost import (
    ProviderLatencyTimer as ObservabilityTimer,
)
from app.observability.token_cost import (
    build_llm_call_metrics as observability_build_metrics,
)
from app.observability.trace_service import TraceService
from app.observability.trace_types import TraceRunType, TraceStepType
from app.providers.llm.base import TokenUsage
from app.providers.llm.registry import ModelInfo
from app.schemas.trace import TraceRunCreate
from app.services.llm_usage import (
    LLMCallMetrics as LegacyMetrics,
)
from app.services.llm_usage import ProviderLatencyTimer, build_llm_call_metrics


def model_info(
    input_price: Decimal | None,
    output_price: Decimal | None,
) -> ModelInfo:
    return ModelInfo(
        provider="openai_compatible",
        model="example-model",
        display_name="Example Model",
        input_price_per_1m=input_price,
        output_price_per_1m=output_price,
    )


@pytest.fixture
def trace_db(tmp_path: Path) -> Iterator[tuple[Session, Engine]]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'trace-usage.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session, engine
    finally:
        session.close()
        engine.dispose()


def test_build_metrics_calculates_decimal_cost_and_tokens() -> None:
    metrics = build_llm_call_metrics(
        usage=TokenUsage(
            input_tokens=1_000,
            output_tokens=500,
            total_tokens=1_500,
        ),
        model_info=model_info(Decimal("0.50"), Decimal("1.50")),
        latency_ms=123,
    )

    assert metrics.input_tokens == 1_000
    assert metrics.output_tokens == 500
    assert metrics.total_tokens == 1_500
    assert metrics.estimated_cost == Decimal("0.00125000")
    assert metrics.latency_ms == 123


def test_build_metrics_keeps_tokens_null_without_usage() -> None:
    metrics = build_llm_call_metrics(
        usage=None,
        model_info=model_info(Decimal("0.50"), Decimal("1.50")),
        latency_ms=1,
    )

    assert metrics.input_tokens is None
    assert metrics.output_tokens is None
    assert metrics.total_tokens is None
    assert metrics.estimated_cost is None


def test_build_metrics_keeps_cost_null_when_either_price_is_unknown() -> None:
    usage = TokenUsage(input_tokens=1, output_tokens=1, total_tokens=2)

    missing_input_price = build_llm_call_metrics(
        usage=usage,
        model_info=model_info(None, Decimal("1.50")),
        latency_ms=1,
    )
    missing_output_price = build_llm_call_metrics(
        usage=usage,
        model_info=model_info(Decimal("0.50"), None),
        latency_ms=1,
    )

    assert missing_input_price.estimated_cost is None
    assert missing_output_price.estimated_cost is None


def test_build_metrics_treats_zero_price_as_known() -> None:
    metrics = build_llm_call_metrics(
        usage=TokenUsage(input_tokens=10, output_tokens=20, total_tokens=30),
        model_info=model_info(Decimal("0"), Decimal("0")),
        latency_ms=0,
    )

    assert metrics.estimated_cost == Decimal("0E-8")


def test_build_metrics_rounds_to_database_scale() -> None:
    metrics = build_llm_call_metrics(
        usage=TokenUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        model_info=model_info(Decimal("0.004"), Decimal("0.004")),
        latency_ms=0,
    )

    assert metrics.estimated_cost == Decimal("1E-8")


def test_build_metrics_clamps_negative_latency() -> None:
    metrics = build_llm_call_metrics(
        usage=None,
        model_info=model_info(None, None),
        latency_ms=-1,
    )

    assert metrics.latency_ms == 0


def test_latency_timer_accumulates_only_measured_sections() -> None:
    ticks = iter([10.0, 10.010, 20.0, 20.015])
    timer = ProviderLatencyTimer(clock=lambda: next(ticks))

    with timer.measure():
        pass
    with timer.measure():
        pass

    assert timer.latency_ms == 25


def test_legacy_usage_imports_are_canonical_observability_objects() -> None:
    assert LegacyMetrics is ObservabilityMetrics
    assert ProviderLatencyTimer is ObservabilityTimer
    assert build_llm_call_metrics is observability_build_metrics


def test_metrics_build_json_safe_trace_step_metadata() -> None:
    metrics = build_llm_call_metrics(
        usage=TokenUsage(
            input_tokens=1_000,
            output_tokens=500,
            total_tokens=1_500,
        ),
        model_info=model_info(Decimal("0.50"), Decimal("1.50")),
        latency_ms=123,
    )

    assert metrics.to_step_metadata() == {
        "usage": {
            "input_tokens": 1_000,
            "output_tokens": 500,
            "total_tokens": 1_500,
            "estimated_cost": "0.00125000",
        },
        "latency_ms": 123,
    }


def test_metrics_metadata_preserves_unknowns_and_returns_fresh_objects() -> None:
    metrics = build_llm_call_metrics(
        usage=None,
        model_info=model_info(None, None),
        latency_ms=-1,
    )

    first = metrics.to_step_metadata()
    second = metrics.to_step_metadata()

    assert first == {
        "usage": {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "estimated_cost": None,
        },
        "latency_ms": 0,
    }
    assert first is not second
    assert first["usage"] is not second["usage"]


def test_mock_llm_usage_metadata_persists_on_completed_trace_step(
    trace_db: tuple[Session, Engine],
) -> None:
    session, _ = trace_db
    ticks = iter(
        [
            datetime(2026, 8, 2, 12, 0, 0),
            datetime(2026, 8, 2, 12, 0, 1),
            datetime(2026, 8, 2, 12, 0, 1, 25000),
        ]
    )
    service = TraceService(session, clock=lambda: next(ticks))
    trace_run = service.create_run(
        TraceRunCreate(
            run_type=TraceRunType.CHAT,
            input_text="Mock LLM usage",
        )
    )
    trace_step = service.add_step(
        trace_run,
        step_type=TraceStepType.LLM_CALL,
        name="Mock LLM call",
    )
    metrics = build_llm_call_metrics(
        usage=TokenUsage(
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
        ),
        model_info=model_info(Decimal("1.00"), Decimal("2.00")),
        latency_ms=25,
    )

    service.finish_step(
        trace_step,
        output_json=metrics.to_step_metadata(),
    )
    trace_step_id = trace_step.id
    session.commit()
    session.expire_all()

    stored = session.get(TraceStep, trace_step_id)
    assert stored is not None
    assert stored.output_json == metrics.to_step_metadata()
    assert stored.output_json["usage"]["estimated_cost"] == "0.00002000"
