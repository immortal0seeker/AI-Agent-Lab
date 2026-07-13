from decimal import Decimal

from app.providers.llm.base import TokenUsage
from app.providers.llm.registry import ModelInfo
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
