from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from time import perf_counter

from app.providers.llm.base import TokenUsage
from app.providers.llm.registry import ModelInfo


COST_QUANTUM = Decimal("0.00000001")
TOKENS_PER_MILLION = Decimal("1000000")


@dataclass(frozen=True)
class LLMCallMetrics:
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost: Decimal | None
    latency_ms: int


class ProviderLatencyTimer:
    def __init__(self, *, clock: Callable[[], float] = perf_counter) -> None:
        self._clock = clock
        self._elapsed_seconds = 0.0

    @contextmanager
    def measure(self) -> Iterator[None]:
        started_at = self._clock()
        try:
            yield
        finally:
            self._elapsed_seconds += max(0.0, self._clock() - started_at)

    @property
    def latency_ms(self) -> int:
        return max(0, round(self._elapsed_seconds * 1000))


def build_llm_call_metrics(
    *,
    usage: TokenUsage | None,
    model_info: ModelInfo,
    latency_ms: int,
) -> LLMCallMetrics:
    estimated_cost: Decimal | None = None
    if (
        usage is not None
        and model_info.input_price_per_1m is not None
        and model_info.output_price_per_1m is not None
    ):
        raw_cost = (
            Decimal(usage.input_tokens) * model_info.input_price_per_1m
            + Decimal(usage.output_tokens) * model_info.output_price_per_1m
        ) / TOKENS_PER_MILLION
        estimated_cost = raw_cost.quantize(
            COST_QUANTUM,
            rounding=ROUND_HALF_UP,
        )

    return LLMCallMetrics(
        input_tokens=usage.input_tokens if usage is not None else None,
        output_tokens=usage.output_tokens if usage is not None else None,
        total_tokens=usage.total_tokens if usage is not None else None,
        estimated_cost=estimated_cost,
        latency_ms=max(0, latency_ms),
    )
