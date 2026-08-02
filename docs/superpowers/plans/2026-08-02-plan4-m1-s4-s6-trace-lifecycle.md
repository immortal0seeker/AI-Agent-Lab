# Plan 4 M1 S4-S6 Trace Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a transaction-safe Trace lifecycle service, request-local Trace context, and reusable token/cost/latency metadata helpers without wiring Trace into Chat, RAG, or Agent runtime paths.

**Architecture:** `TraceService` is the only writer for lifecycle state and uses the caller-owned SQLAlchemy session with `flush()` but no transaction completion. `TraceContext` propagates a run UUID through `ContextVar` and wraps individual steps. Existing LLM usage calculation moves to `observability/token_cost.py`; `services/llm_usage.py` remains a compatibility facade.

**Tech Stack:** Python 3.11, SQLAlchemy 2.0, Pydantic 2, pytest 9, SQLite, ContextVars.

## Global Constraints

- Work only on `P4-M1-S4-S6`; do not implement M2 runtime hooks, Trace API/UI, Advanced RAG, reranking, evaluation, or Plan 5 behavior.
- Use the current `main` workspace; do not create a branch/worktree or stage, commit, push, pull, rebase, merge, or move tags.
- `TraceService` shares the caller's SQLAlchemy transaction and must never call `commit()` or `rollback()`.
- Tests use temporary SQLite, injected clocks, and mock usage only; never access `backend/ai_agent_lab.db`, a real `.env`, credentials, a paid Provider, or a network Tool.
- Automatic context-manager errors store only the exception class, never arbitrary exception text.
- Keep API routes untouched and preserve all existing Plan 1-3 imports and behavior.
- Codex self-review is the only review gate.

## File Structure

- Create `backend/app/observability/trace_service.py`: lifecycle state validation, run/step persistence, timing, and deterministic step ordering.
- Create `backend/app/observability/trace_context.py`: UUID context binding plus run activation and step context managers.
- Create `backend/app/observability/token_cost.py`: Provider latency timer, Decimal cost calculation, metrics record, and JSON-safe Trace metadata.
- Modify `backend/app/services/llm_usage.py`: compatibility re-exports only.
- Create `backend/tests/test_trace_service.py`: service lifecycle, ordering, transaction ownership, and negative-path tests.
- Create `backend/tests/test_trace_context.py`: ContextVar nesting/isolation and step context-manager tests.
- Modify `backend/tests/test_llm_usage.py`: verify the new canonical module, legacy facade, JSON-safe metadata, and step persistence.
- Modify `docs-plan/04-PLAN4/04-PLAN4-执行步骤表 (V1.0).md`: mark only S4-S6 complete with evidence.
- Modify `CHANGELOG.md`: record the Trace lifecycle foundation under Unreleased.
- Create `docs/reviews/2026-08-02-plan4-m1-s4-s6-review.md`: record RED/GREEN, regression, scope, and Codex review.
- Do not expand `backend/app/observability/__init__.py`; importing service classes there would create a package/model import cycle because `models/trace.py` imports `observability.trace_types`.

---

### Task 1: TraceService Lifecycle Writer

**Files:**
- Create: `backend/app/observability/trace_service.py`
- Create: `backend/tests/test_trace_service.py`

**Interfaces:**
- Consumes: `TraceRun`, `TraceStep`, `TraceRunCreate`, `TraceStepCreate`, `TraceStatus`, `TraceStepType`, `utc_now`, and a caller-owned `Session`.
- Produces: `TraceStateError`; `TraceService.create_run`, `add_step`, `finish_run`, `fail_run`, `finish_step`, and `fail_step`.

- [ ] **Step 1: Write failing creation, ordering, completion, and rollback tests**

Create a temporary SQLite fixture with `Base.metadata.create_all()` and an injected sequence clock. Add tests equivalent to:

```python
def test_trace_service_creates_running_run_and_ordered_steps(db):
    session, clock = db
    service = TraceService(session, clock=clock)
    run = service.create_run(
        TraceRunCreate(run_type=TraceRunType.CHAT, input_text="hello")
    )
    first = service.add_step(
        run,
        step_type=TraceStepType.BUILD_CONTEXT,
        name="Build context",
        input_json={"message_count": 1},
    )
    second = service.add_step(
        run,
        step_type=TraceStepType.LLM_CALL,
        name="Call model",
    )

    assert run.status == TraceStatus.RUNNING.value
    assert run.started_at == datetime(2026, 8, 2, 12, 0, 0)
    assert [first.step_index, second.step_index] == [1, 2]
    assert first.input_json == {"message_count": 1}


def test_trace_service_finishes_run_and_step_with_non_negative_latency(db):
    session, clock = db
    service = TraceService(session, clock=clock)
    run = service.create_run(
        TraceRunCreate(run_type=TraceRunType.CHAT, input_text="hello")
    )
    step = service.add_step(
        run,
        step_type=TraceStepType.LLM_CALL,
        name="Call model",
    )
    finished_step = service.finish_step(step, output_json={"ok": True})
    finished_run = service.finish_run(run, output_text="answer")

    assert finished_step.status == TraceStatus.COMPLETED.value
    assert finished_step.output_json == {"ok": True}
    assert finished_step.error_message is None
    assert finished_step.latency_ms >= 0
    assert finished_run.status == TraceStatus.COMPLETED.value
    assert finished_run.output_text == "answer"
    assert finished_run.error_message is None
    assert finished_run.latency_ms >= 0


def test_trace_service_never_commits_and_caller_rollback_removes_trace(db):
    session, clock = db
    service = TraceService(session, clock=clock)
    run = service.create_run(
        TraceRunCreate(run_type=TraceRunType.CHAT, input_text="rollback")
    )
    run_id = run.id

    session.rollback()

    assert session.get(TraceRun, run_id) is None
```

- [ ] **Step 2: Run the new tests and verify RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_service.py -q
```

Expected: collection fails because `app.observability.trace_service` does not exist.

- [ ] **Step 3: Implement the minimal lifecycle writer**

Implement this complete lifecycle writer:

```python
from collections.abc import Callable
from datetime import datetime

from pydantic import JsonValue
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.common import utc_now
from app.models.trace import TraceRun, TraceStep
from app.observability.trace_types import TraceStatus, TraceStepType
from app.schemas.trace import TraceRunCreate, TraceStepCreate


class TraceStateError(RuntimeError):
    pass


class TraceService:
    def __init__(
        self,
        session: Session,
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._session = session
        self._clock = clock

    def create_run(self, data: TraceRunCreate) -> TraceRun:
        if data.status is not TraceStatus.PENDING:
            raise TraceStateError("TraceRun creation requires pending status")
        payload = data.model_dump(mode="python")
        payload["run_type"] = data.run_type.value
        payload["status"] = TraceStatus.RUNNING.value
        trace_run = TraceRun(
            **payload,
            started_at=self._clock(),
        )
        self._session.add(trace_run)
        self._session.flush()
        return trace_run

    def add_step(
        self,
        trace_run: TraceRun,
        *,
        step_type: TraceStepType,
        name: str,
        input_json: dict[str, JsonValue] | None = None,
    ) -> TraceStep:
        self._require_running("TraceRun", trace_run.status)
        next_index = (
            self._session.scalar(
                select(func.max(TraceStep.step_index)).where(
                    TraceStep.trace_run_id == trace_run.id
                )
            )
            or 0
        ) + 1
        data = TraceStepCreate(
            trace_run_id=trace_run.id,
            step_index=next_index,
            step_type=step_type,
            name=name,
            status=TraceStatus.RUNNING,
            input_json=input_json or {},
        )
        payload = data.model_dump(mode="python")
        payload["step_type"] = data.step_type.value
        payload["status"] = data.status.value
        trace_step = TraceStep(
            **payload,
            started_at=self._clock(),
        )
        self._session.add(trace_step)
        self._session.flush()
        return trace_step

    def finish_run(
        self,
        trace_run: TraceRun,
        *,
        output_text: str | None = None,
    ) -> TraceRun:
        self._require_running("TraceRun", trace_run.status)
        started_at = self._require_started("TraceRun", trace_run.started_at)
        ended_at = self._clock()
        trace_run.status = TraceStatus.COMPLETED.value
        trace_run.output_text = output_text
        trace_run.error_message = None
        trace_run.ended_at = ended_at
        trace_run.latency_ms = self._latency_ms(started_at, ended_at)
        self._session.flush()
        return trace_run

    def fail_run(
        self,
        trace_run: TraceRun,
        *,
        error_message: str,
    ) -> TraceRun:
        self._require_running("TraceRun", trace_run.status)
        safe_error = self._normalize_error(error_message)
        started_at = self._require_started("TraceRun", trace_run.started_at)
        ended_at = self._clock()
        trace_run.status = TraceStatus.FAILED.value
        trace_run.output_text = None
        trace_run.error_message = safe_error
        trace_run.ended_at = ended_at
        trace_run.latency_ms = self._latency_ms(started_at, ended_at)
        self._session.flush()
        return trace_run

    def finish_step(
        self,
        trace_step: TraceStep,
        *,
        output_json: dict[str, JsonValue] | None = None,
    ) -> TraceStep:
        self._require_running("TraceStep", trace_step.status)
        started_at = self._require_started("TraceStep", trace_step.started_at)
        ended_at = self._clock()
        trace_step.status = TraceStatus.COMPLETED.value
        trace_step.output_json = output_json
        trace_step.error_message = None
        trace_step.ended_at = ended_at
        trace_step.latency_ms = self._latency_ms(started_at, ended_at)
        self._session.flush()
        return trace_step

    def fail_step(
        self,
        trace_step: TraceStep,
        *,
        error_message: str,
    ) -> TraceStep:
        self._require_running("TraceStep", trace_step.status)
        safe_error = self._normalize_error(error_message)
        started_at = self._require_started("TraceStep", trace_step.started_at)
        ended_at = self._clock()
        trace_step.status = TraceStatus.FAILED.value
        trace_step.output_json = None
        trace_step.error_message = safe_error
        trace_step.ended_at = ended_at
        trace_step.latency_ms = self._latency_ms(started_at, ended_at)
        self._session.flush()
        return trace_step

    @staticmethod
    def _require_running(record_type: str, status: str) -> None:
        if status != TraceStatus.RUNNING.value:
            raise TraceStateError(
                f"{record_type} must be running; current status: {status}"
            )

    @staticmethod
    def _require_started(
        record_type: str,
        started_at: datetime | None,
    ) -> datetime:
        if started_at is None:
            raise TraceStateError(f"{record_type} is missing started_at")
        return started_at

    @staticmethod
    def _normalize_error(error_message: str) -> str:
        normalized = error_message.strip()
        if not normalized:
            raise ValueError("error_message must not be blank")
        return normalized

    @staticmethod
    def _latency_ms(started_at: datetime, ended_at: datetime) -> int:
        return max(
            0,
            round((ended_at - started_at).total_seconds() * 1000),
        )
```

Implementation rules:

- `create_run` accepts only `TraceStatus.PENDING`, writes `RUNNING`, sets `started_at`, adds, and flushes.
- `add_step` accepts only a running run, uses `select(func.max(TraceStep.step_index))` scoped by run ID, validates through `TraceStepCreate`, writes `RUNNING`, sets `started_at`, adds, and flushes.
- Terminal methods require `RUNNING` and non-null `started_at`, write one terminal state, `ended_at`, and latency, then flush.
- Completion clears `error_message`; failure strips/rejects blank safe errors and clears output.
- No method calls `commit()` or `rollback()` and no integrity exception is swallowed.

- [ ] **Step 4: Add failing negative-path tests**

Cover the exact contracts:

```python
@pytest.mark.parametrize("terminal", ["completed", "failed", "cancelled"])
def test_trace_service_rejects_step_addition_to_terminal_run(db, terminal):
    session, clock = db
    service = TraceService(session, clock=clock)
    run = service.create_run(
        TraceRunCreate(run_type=TraceRunType.CHAT, input_text="hello")
    )
    run.status = terminal
    with pytest.raises(TraceStateError, match="must be running"):
        service.add_step(
            run,
            step_type=TraceStepType.LLM_CALL,
            name="Call model",
        )


def test_trace_service_rejects_non_pending_create_status(db):
    session, clock = db
    service = TraceService(session, clock=clock)
    with pytest.raises(TraceStateError, match="requires pending"):
        service.create_run(
            TraceRunCreate(
                run_type=TraceRunType.CHAT,
                input_text="hello",
                status=TraceStatus.COMPLETED,
            )
        )


def test_trace_service_rejects_repeated_terminal_transition(db):
    session, clock = db
    service = TraceService(session, clock=clock)
    run = service.create_run(
        TraceRunCreate(run_type=TraceRunType.CHAT, input_text="hello")
    )
    service.finish_run(run, output_text="answer")
    with pytest.raises(TraceStateError, match="must be running"):
        service.fail_run(run, error_message="safe error")
    assert run.status == TraceStatus.COMPLETED.value


def test_trace_service_records_explicit_safe_failure_and_clears_output(db):
    session, clock = db
    service = TraceService(session, clock=clock)
    run = service.create_run(
        TraceRunCreate(run_type=TraceRunType.CHAT, input_text="hello")
    )
    run.output_text = "partial"
    service.fail_run(run, error_message="  Public provider failure  ")
    assert run.status == TraceStatus.FAILED.value
    assert run.output_text is None
    assert run.error_message == "Public provider failure"


def test_trace_service_rejects_blank_failure_message(db):
    session, clock = db
    service = TraceService(session, clock=clock)
    run = service.create_run(
        TraceRunCreate(run_type=TraceRunType.CHAT, input_text="hello")
    )
    with pytest.raises(ValueError, match="must not be blank"):
        service.fail_run(run, error_message="   ")
    assert run.status == TraceStatus.RUNNING.value


def test_trace_service_clamps_clock_regression_to_zero(db):
    session, _ = db
    ticks = iter(
        [
            datetime(2026, 8, 2, 12, 0, 1),
            datetime(2026, 8, 2, 12, 0, 0),
        ]
    )
    service = TraceService(session, clock=lambda: next(ticks))
    run = service.create_run(
        TraceRunCreate(run_type=TraceRunType.CHAT, input_text="hello")
    )
    service.finish_run(run)
    assert run.latency_ms == 0
```

Assert `TraceStateError` for invalid states, `ValueError` for blank error text, and no mutation of the previous terminal state.

- [ ] **Step 5: Run focused service tests and preserve the GREEN result**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_service.py tests/test_trace_models.py tests/test_trace_schemas.py -q
```

Expected: all tests pass with no new warning.

- [ ] **Step 6: Review checkpoint without Git mutation**

Run `git diff --check` and inspect `git diff -- backend/app/observability/trace_service.py backend/tests/test_trace_service.py`. Do not stage or commit; the user will create one final verified batch commit.

---

### Task 2: Request-Local TraceContext And Step Manager

**Files:**
- Create: `backend/app/observability/trace_context.py`
- Create: `backend/tests/test_trace_context.py`

**Interfaces:**
- Consumes: Task 1 `TraceService`, `TraceRun`, `TraceStep`, and `TraceStepType`.
- Produces: `get_trace_run_id() -> UUID | None`, `bind_trace_run_id(UUID) -> ContextManager[None]`, `TraceContext.activate()`, and `TraceContext.step`.

- [ ] **Step 1: Write failing ContextVar contract tests**

Add tests equivalent to:

```python
def test_trace_run_id_binding_is_nested_and_restored():
    outer = uuid4()
    inner = uuid4()
    assert get_trace_run_id() is None
    with bind_trace_run_id(outer):
        assert get_trace_run_id() == outer
        with bind_trace_run_id(inner):
            assert get_trace_run_id() == inner
        assert get_trace_run_id() == outer
    assert get_trace_run_id() is None


def test_trace_run_id_is_restored_after_exception():
    with pytest.raises(RuntimeError, match="boom"):
        with bind_trace_run_id(uuid4()):
            raise RuntimeError("boom")
    assert get_trace_run_id() is None
```

Add a `copy_context()` isolation test proving a bound ID in one copied context does not overwrite an independently bound ID or the original unbound context.

- [ ] **Step 2: Run Context tests and verify RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_context.py -q
```

Expected: collection fails because `app.observability.trace_context` does not exist.

- [ ] **Step 3: Implement binding and activation**

Use this dependency-free binding core:

```python
_trace_run_id: ContextVar[UUID | None] = ContextVar(
    "trace_run_id",
    default=None,
)


def get_trace_run_id() -> UUID | None:
    return _trace_run_id.get()


@contextmanager
def bind_trace_run_id(trace_run_id: UUID) -> Iterator[None]:
    token = _trace_run_id.set(trace_run_id)
    try:
        yield
    finally:
        _trace_run_id.reset(token)
```

`TraceContext.__init__(service, trace_run)` stores one service and run. `activate()` must wrap `bind_trace_run_id(self.trace_run.id)` and yield `self`.

- [ ] **Step 4: Write failing success/failure step-manager tests**

Cover:

```python
def test_trace_context_step_binds_id_and_completes_with_output(db):
    context, run = create_context(db)
    with context.step(
        TraceStepType.LLM_CALL,
        name="Call model",
        input_json={"model": "mock"},
    ) as step:
        assert get_trace_run_id() == run.id
        step.output_json = {"finish_reason": "stop"}
    assert step.status == TraceStatus.COMPLETED.value
    assert step.output_json == {"finish_reason": "stop"}
    assert get_trace_run_id() is None


def test_trace_context_step_fails_safely_and_reraises(db):
    context, _ = create_context(db)
    secret = "SYNTHETIC_SECRET_DO_NOT_STORE"
    with pytest.raises(RuntimeError, match=secret):
        with context.step(TraceStepType.TOOL_CALL, name="Call tool"):
            raise RuntimeError(secret)
    stored = db.session.scalar(select(TraceStep))
    assert stored.status == TraceStatus.FAILED.value
    assert stored.error_message == "RuntimeError"
    assert secret not in stored.error_message
```

- [ ] **Step 5: Implement the step context manager**

Implement:

```python
@contextmanager
def step(
    self,
    step_type: TraceStepType,
    *,
    name: str,
    input_json: dict[str, JsonValue] | None = None,
) -> Iterator[TraceStep]:
    with bind_trace_run_id(self.trace_run.id):
        trace_step = self.service.add_step(
            self.trace_run,
            step_type=step_type,
            name=name,
            input_json=input_json,
        )
        try:
            yield trace_step
        except Exception as exc:
            self.service.fail_step(
                trace_step,
                error_message=type(exc).__name__,
            )
            raise
        else:
            self.service.finish_step(
                trace_step,
                output_json=trace_step.output_json,
            )
```

Do not log or persist `str(exc)`. Do not finish/fail the enclosing run automatically; its product owner decides run outcome.

- [ ] **Step 6: Run focused context and service tests**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_context.py tests/test_trace_service.py -q
```

Expected: all tests pass, including nested restoration and safe exception persistence.

- [ ] **Step 7: Review checkpoint without Git mutation**

Run `git diff --check` and inspect only the Task 2 files plus Task 1 dependencies. Do not stage or commit.

---

### Task 3: Canonical Token/Cost/Latency Metadata

**Files:**
- Create: `backend/app/observability/token_cost.py`
- Modify: `backend/app/services/llm_usage.py`
- Modify: `backend/tests/test_llm_usage.py`

**Interfaces:**
- Consumes: `TokenUsage`, `ModelInfo`, `TraceService.finish_step`, and the existing Plan 1/3 LLM usage contracts.
- Produces: `LLMCallMetrics`, `ProviderLatencyTimer`, `build_llm_call_metrics`, and `LLMCallMetrics.to_step_metadata()` from the canonical observability module; legacy imports remain identical.

- [ ] **Step 1: Write failing canonical-module and metadata tests**

Retain every existing assertion and add:

```python
from app.observability.token_cost import (
    LLMCallMetrics as ObservabilityMetrics,
    ProviderLatencyTimer as ObservabilityTimer,
    build_llm_call_metrics as observability_build_metrics,
)
from app.services.llm_usage import LLMCallMetrics as LegacyMetrics


def test_legacy_usage_imports_are_canonical_observability_objects():
    assert LegacyMetrics is ObservabilityMetrics
    assert ProviderLatencyTimer is ObservabilityTimer
    assert build_llm_call_metrics is observability_build_metrics


def test_metrics_build_json_safe_trace_step_metadata():
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
```

Also assert unknown usage/pricing produces explicit `None` values and each call returns independent nested dictionaries.

- [ ] **Step 2: Run usage tests and verify RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_usage.py -q
```

Expected: import fails because `app.observability.token_cost` does not exist.

- [ ] **Step 3: Extract the implementation and preserve compatibility**

Move `COST_QUANTUM`, `TOKENS_PER_MILLION`, `LLMCallMetrics`, `ProviderLatencyTimer`, and `build_llm_call_metrics` unchanged into `observability/token_cost.py`, then add:

```python
@dataclass(frozen=True)
class LLMCallMetrics:
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost: Decimal | None
    latency_ms: int

    def to_step_metadata(self) -> dict[str, JsonValue]:
        return {
            "usage": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.total_tokens,
                "estimated_cost": (
                    format(self.estimated_cost, "f")
                    if self.estimated_cost is not None
                    else None
                ),
            },
            "latency_ms": self.latency_ms,
        }
```

Replace `services/llm_usage.py` with explicit compatibility imports and `__all__`:

```python
from app.observability.token_cost import (
    LLMCallMetrics,
    ProviderLatencyTimer,
    build_llm_call_metrics,
)

__all__ = [
    "LLMCallMetrics",
    "ProviderLatencyTimer",
    "build_llm_call_metrics",
]
```

Do not change ChatService, RagService, Provider adapters, or model pricing files.

- [ ] **Step 4: Add a failing TraceStep persistence acceptance test**

Use Task 1 service with temporary SQLite and a mock `TokenUsage`:

```python
def test_mock_llm_usage_metadata_persists_on_completed_trace_step(trace_db):
    metrics = build_llm_call_metrics(
        usage=TokenUsage(input_tokens=10, output_tokens=5, total_tokens=15),
        model_info=model_info(Decimal("1.00"), Decimal("2.00")),
        latency_ms=25,
    )
    service, run = create_trace_service_and_run(trace_db)
    step = service.add_step(
        run,
        step_type=TraceStepType.LLM_CALL,
        name="Mock LLM call",
    )
    service.finish_step(step, output_json=metrics.to_step_metadata())
    trace_db.commit()
    trace_db.expire_all()

    stored = trace_db.get(TraceStep, step.id)
    assert stored.output_json == metrics.to_step_metadata()
    assert stored.output_json["usage"]["estimated_cost"] == "0.00002000"
```

- [ ] **Step 5: Run focused S4-S6 and compatibility tests**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_service.py tests/test_trace_context.py tests/test_llm_usage.py tests/test_chat_service.py tests/test_rag_service.py -q
```

Expected: all tests pass and existing imports remain behaviorally identical.

- [ ] **Step 6: Review checkpoint without Git mutation**

Run `git diff --check`; inspect the canonical helper, compatibility facade, tests, and all import sites found by `Select-String -Path app/**/*.py,tests/**/*.py -Pattern 'services.llm_usage'`. Do not stage or commit.

---

### Task 4: Batch Documentation, Regression, And Codex Self-Review

**Files:**
- Modify: `docs-plan/04-PLAN4/04-PLAN4-执行步骤表 (V1.0).md`
- Modify: `CHANGELOG.md`
- Create: `docs/reviews/2026-08-02-plan4-m1-s4-s6-review.md`
- Verify: all Task 1-3 files and repository state.

**Interfaces:**
- Consumes: verified S4-S6 code/test evidence.
- Produces: accurate completion status, review classification, residual limitations, and a manual commit handoff.

- [ ] **Step 1: Update only current-batch documentation**

Change Batch 2 and rows S4-S6 from unfinished to completed with concise fresh evidence. Add an Unreleased CHANGELOG bullet describing Trace lifecycle/context/usage metadata. Create the review record with these sections:

```markdown
# Plan 4 M1 S4-S6 Review

## Scope
## Acceptance Matrix
## RED/GREEN Evidence
## Matching And Full Verification
## Codex Self-Review
## Finding Classification
## Deferred Boundaries
## Git Handoff
```

Record that runtime wiring is intentionally deferred to M2 and that concurrent writers to one TraceRun rely on the unique step-index constraint under the current single-user SQLite boundary.

- [ ] **Step 2: Run matching backend verification**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_service.py tests/test_trace_context.py tests/test_trace_models.py tests/test_trace_schemas.py tests/test_trace_migration.py tests/test_llm_usage.py tests/test_chat_service.py tests/test_rag_service.py -q
```

Expected: all selected tests pass; only the already-known Starlette/httpx deprecation warning is acceptable.

- [ ] **Step 3: Run complete backend and dependency verification**

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Expected: full suite passes; `pip check` reports `No broken requirements found.`

- [ ] **Step 4: Run risk-matched repository checks**

Run read-only checks that avoid the user database and secrets:

```powershell
git diff --check
git status --short
git diff --name-only
git diff --cached --name-only
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git rev-parse 'v0.3.1^{}'
```

Check Markdown local links for changed documents, scan tracked/diff text for private-key markers, real credential patterns, network Tool runtime, generated artifacts, and out-of-scope M2/Plan 5 implementation. Do not open `.env`, `backend/ai_agent_lab.db`, browser credentials, SSH material, or any untracked sensitive file.

No migration lifecycle, frontend typecheck/build, Docker/Qdrant, or browser replay is required because S4-S6 change no schema, API, UI, vector-store, or user-visible runtime behavior. Record this risk decision explicitly.

- [ ] **Step 5: Perform Codex final self-review**

Review every changed line for:

1. S4-S6-only scope and no M2 hooks;
2. no `commit()`/`rollback()` in Trace Service/Context;
3. strict and test-covered state transitions;
4. no arbitrary exception text in automatic Trace errors;
5. JSON-safe Decimal metadata and legacy import compatibility;
6. no secrets, real Provider/network calls, user database access, generated artifacts, or unrelated changes;
7. documentation matching actual fresh evidence.

Classify findings as must fix, fix later, recorded limitation, or not applicable. Fix and re-run matching tests for every must-fix before reporting completion.

- [ ] **Step 6: Prepare the manual Git handoff**

Do not stage or commit. Report the exact changed paths, verification counts, remaining limitations, clean staged set, and suggested commit message:

```text
feat(observability): add trace lifecycle and context
```

State whether the workspace is ready for the user to review and manually commit, and whether `P4-M1-S7` can begin after that commit.
