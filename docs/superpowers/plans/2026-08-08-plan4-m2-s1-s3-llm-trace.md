# Plan 4 M2 S1～S3 LLM Trace Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist safe, standardized LLM Trace Runs/Steps for non-streaming Chat, streaming Chat, and Naive RAG Chat success and Provider-failure paths.

**Architecture:** A service-level `LLMTraceRecorder` maps product LLM calls to the generic flush-only M1 `TraceService`. Successful Trace and business rows share the existing transaction; a Provider failure rolls back provisional business state, then the recorder explicitly persists a standalone failed audit transaction before the product service re-raises the original safe-mapped exception.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2, Pydantic 2, SQLite, pytest 9, Mock LLM Providers, Markdown, PowerShell, Git read-only verification.

## Global Constraints

- Work only on `P4-M2-S1～S3`.
- Cover non-streaming Chat, streaming Chat, and only the LLM call inside Naive RAG Chat.
- Do not wire Simple Agent, Tool calls, retrieval candidates/Steps, Trace API/UI, cancellation persistence, Advanced RAG, reranking, evaluation, or later-Plan runtime.
- Do not add or modify an Alembic migration or database column/table.
- Preserve existing HTTP, SSE, Chat, RAG, Conversation, Message, `LLMCall`, and `RagQuery` response/rollback behavior.
- `TraceService` remains flush-only. Provider adapters remain independent of SQLAlchemy and Trace.
- Persist only exception class names for Provider failures; never persist/log raw exception text, Provider bodies, credentials, full Chat history, or RAG context.
- Use TDD: every production behavior must have an observed, correctly failing test first.
- Tests use Mock Providers and explicit temporary SQLite/storage only. Never read `backend/ai_agent_lab.db`, real `.env`, credentials, or call paid/network Providers/Tools.
- Use the current `main` workspace. Do not create a branch/worktree or stage, commit, push, pull, rebase, merge, or move tags.
- Preserve the user-owned untracked `PROJECT_LEARNING_CHECKLIST.md` without reading or modifying it.
- Necessary code comments are Chinese and explain only non-obvious security/transaction boundaries.
- Codex self-review is the only review gate.

---

## File Structure

- Create `backend/app/observability/prompt_version.py`: stable prompt-shape identifiers.
- Create `backend/app/observability/llm_trace.py`: product LLM-to-Trace coordinator and failure-audit transaction boundary.
- Modify `backend/app/observability/__init__.py`: export stable prompt identifiers and recorder types actually needed by services.
- Modify `backend/app/schemas/trace.py`: strict LLM Step input/usage/output metadata schemas.
- Create `backend/tests/test_llm_trace.py`: prompt/schema/recorder unit and temporary-SQLite transaction tests.
- Modify `backend/app/services/chat_service.py`: non-streaming and streaming hooks.
- Modify `backend/tests/test_chat_service.py`: service persistence, metadata, failure, streaming, and compatibility tests.
- Modify `backend/tests/test_chat_api.py`: committed API success/failure Trace assertions and redaction checks.
- Modify `backend/app/services/rag_service.py`: RAG Chat Run plus final LLM-call Step hook only.
- Modify `backend/tests/test_rag_service.py`: RAG LLM Trace success/failure tests.
- Modify `backend/tests/test_rag_api.py`: committed RAG API Trace assertions.
- Modify `docs/30-trace-observability.md`, `docs/01-architecture.md`, `README.md`, `README_CN.md`, `CHANGELOG.md`, and `docs-plan/04-PLAN4/04-PLAN4-执行步骤表 (V1.0).md`: current implementation truth.
- Create `docs/reviews/2026-08-08-plan4-m2-s1-s3-review.md`: RED/GREEN, verification, findings, and next-step gate.

---

### Task 1: Stable Prompt Versions And Strict LLM Metadata

**Files:**
- Create: `backend/app/observability/prompt_version.py`
- Modify: `backend/app/schemas/trace.py`
- Create: `backend/tests/test_llm_trace.py`

**Interfaces:**
- Produces: `CHAT_HISTORY_PROMPT_VERSION = "chat-history-v1"`.
- Produces: `NAIVE_RAG_PROMPT_VERSION = "naive-rag-v1"`.
- Produces: `LLMStepInputMetadata`, `LLMStepUsageMetadata`, and `LLMStepOutputMetadata`.
- Consumed by: Task 2 `LLMTraceRecorder` and Task 3 Chat/RAG hooks.

- [ ] **Step 1: Write the prompt-version and schema RED tests**

Create `backend/tests/test_llm_trace.py` with these first tests:

```python
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.observability.prompt_version import (
    CHAT_HISTORY_PROMPT_VERSION,
    NAIVE_RAG_PROMPT_VERSION,
)
from app.schemas.trace import (
    LLMStepInputMetadata,
    LLMStepOutputMetadata,
    LLMStepUsageMetadata,
)


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
        (LLMStepInputMetadata, {
            "provider": "p", "requested_model": "m",
            "prompt_version": "v", "stream": False,
            "message_count": 0,
        }),
        (LLMStepUsageMetadata, {
            "input_tokens": -1, "output_tokens": 0,
            "total_tokens": 0, "estimated_cost": None,
        }),
        (LLMStepUsageMetadata, {
            "input_tokens": None, "output_tokens": None,
            "total_tokens": None, "estimated_cost": "0.1",
        }),
        (LLMStepOutputMetadata, {
            "provider": "p", "model": "m", "prompt_version": "v",
            "usage": {
                "input_tokens": None, "output_tokens": None,
                "total_tokens": None, "estimated_cost": None,
            },
            "latency_ms": -1,
        }),
    ],
)
def test_llm_step_metadata_rejects_invalid_values(
    schema: type[LLMStepInputMetadata | LLMStepUsageMetadata | LLMStepOutputMetadata],
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
```

- [ ] **Step 2: Run RED and confirm the missing-contract failure**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_trace.py -q
```

Expected: collection fails because `prompt_version.py` and the LLM metadata
schemas do not exist. A syntax/import-path error unrelated to those missing
contracts is not an acceptable RED.

- [ ] **Step 3: Implement stable versions and strict schemas**

Create `backend/app/observability/prompt_version.py`:

```python
CHAT_HISTORY_PROMPT_VERSION = "chat-history-v1"
NAIVE_RAG_PROMPT_VERSION = "naive-rag-v1"
```

Add to `backend/app/schemas/trace.py`:

```python
from pydantic import StrictBool

TracePromptVersion = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
TraceCostString = Annotated[
    str,
    StringConstraints(pattern=r"^(?:0|[1-9]\d*)\.\d{8}$"),
]


class LLMStepInputMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: TraceProviderIdentifier
    requested_model: TraceModelIdentifier
    prompt_version: TracePromptVersion
    stream: StrictBool
    message_count: StrictInt = Field(ge=1)


class LLMStepUsageMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    input_tokens: StrictInt | None = Field(default=None, ge=0)
    output_tokens: StrictInt | None = Field(default=None, ge=0)
    total_tokens: StrictInt | None = Field(default=None, ge=0)
    estimated_cost: TraceCostString | None = None


class LLMStepOutputMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: TraceProviderIdentifier
    model: TraceModelIdentifier
    prompt_version: TracePromptVersion
    usage: LLMStepUsageMetadata
    latency_ms: StrictInt = Field(ge=0)
```

- [ ] **Step 4: Run GREEN and focused schema compatibility**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_trace.py tests/test_trace_schemas.py tests/test_llm_usage.py -q
```

Expected: all selected tests pass; old `LLMCallMetrics.to_step_metadata()`
shape remains unchanged.

- [ ] **Step 5: Review checkpoint**

Confirm there is no raw-prompt/response/error field, unknown fields are
rejected, exact cost scale is enforced, and no ORM/migration file changed.
Do not stage or commit.

---

### Task 2: LLMTraceRecorder And Non-Streaming Chat Hook

**Files:**
- Create: `backend/app/observability/llm_trace.py`
- Modify: `backend/app/observability/__init__.py`
- Modify: `backend/tests/test_llm_trace.py`
- Modify: `backend/tests/test_chat_service.py`
- Modify: `backend/tests/test_chat_api.py`
- Modify: `backend/app/services/chat_service.py`

**Interfaces:**
- Consumes: Task 1 prompt constants and metadata schemas; existing
  `TraceService`, `TraceRunType`, `TraceStepType`, and `LLMCallMetrics`.
- Produces: `LLMTraceRecorder.start_run()`, `start_call()`,
  `complete_call()`, and `persist_failure()`.
- Produces: immutable failure snapshot inside `LLMTraceCall` so rollback never
  requires access to expired ORM state.

- [ ] **Step 1: Add Recorder lifecycle RED tests**

Extend `backend/tests/test_llm_trace.py` with a temporary SQLite fixture and
tests that express this API:

```python
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
recorder.complete_call(
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
```

Assert the Run is completed with all totals, the Step is completed with exact
Task 1 input/output JSON, and the successful correlations are present.

Add a failure test:

```python
trace_call = recorder.start_call(trace_run, message_count=1)
recorder.persist_failure(
    trace_call,
    error=ProviderRequestError("synthetic secret diagnostic"),
    conversation_id=None,
)
```

Assert provisional Conversation/Message rows were rolled back, exactly one
failed Run/Step was committed, both errors equal `ProviderRequestError`, Step
output is null, and `synthetic secret diagnostic` is absent from all persisted
Trace fields/JSON.

- [ ] **Step 2: Add non-streaming Chat Service/API RED tests**

Modify the existing success tests to query `TraceRun`/`TraceStep` and assert:

```python
assert trace_run.run_type == TraceRunType.CHAT.value
assert trace_run.status == TraceStatus.COMPLETED.value
assert trace_run.conversation_id == result.conversation.id
assert trace_run.user_message_id == result.user_message.id
assert trace_run.provider == "openai_compatible"
assert trace_run.model == "resolved-model"
assert trace_run.total_tokens == 6
assert trace_run.estimated_cost == Decimal("0.00000500")
assert len(trace_run.steps) == 1
assert trace_run.steps[0].step_type == TraceStepType.LLM_CALL.value
assert trace_run.steps[0].input_json["prompt_version"] == "chat-history-v1"
assert trace_run.steps[0].output_json["usage"]["estimated_cost"] == (
    "0.00000500"
)
```

Modify Provider-failure Service/API tests to retain their existing zero
Conversation/Message/`LLMCall` assertions and additionally assert exactly one
failed uncorrelated Chat Run/Step with class-name-only error. Add an existing-
Conversation failure assertion proving the valid Conversation correlation is
retained while the rolled-back user Message is not referenced.

- [ ] **Step 3: Run RED and confirm missing Recorder/hooks**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_trace.py tests/test_chat_service.py tests/test_chat_api.py -q
```

Expected: Recorder imports/Trace assertions fail because the coordinator and
Chat hook are not implemented. Existing non-Trace behavior must still pass.

- [ ] **Step 4: Implement the minimal Recorder**

Create `backend/app/observability/llm_trace.py` around these concrete types and
methods:

```python
@dataclass(frozen=True, slots=True)
class LLMTraceSnapshot:
    run_type: TraceRunType
    input_text: str
    provider: str
    requested_model: str
    prompt_version: str
    stream: bool
    message_count: int
    run_started_at: datetime
    step_started_at: datetime


@dataclass(slots=True)
class LLMTraceRun:
    record: TraceRun
    run_type: TraceRunType
    input_text: str
    provider: str
    requested_model: str
    prompt_version: str
    stream: bool


@dataclass(slots=True)
class LLMTraceCall:
    run: LLMTraceRun
    step: TraceStep
    snapshot: LLMTraceSnapshot


class LLMTraceRecorder:
    def __init__(
        self,
        session: Session,
        *,
        trace_service: TraceService | None = None,
    ) -> None:
        self._session = session
        self._traces = trace_service or TraceService(session)

    def start_run(
        self,
        *,
        run_type: TraceRunType,
        input_text: str,
        provider: str,
        requested_model: str,
        prompt_version: str,
        stream: bool,
        conversation_id: UUID | None,
        user_message_id: UUID | None,
    ) -> LLMTraceRun:
        record = self._traces.create_run(
            TraceRunCreate(
                run_type=run_type,
                conversation_id=conversation_id,
                user_message_id=user_message_id,
                input_text=input_text,
                provider=provider,
                model=requested_model,
                metadata_json={
                    "prompt_version": prompt_version,
                    "stream": stream,
                },
            )
        )
        return LLMTraceRun(
            record=record,
            run_type=run_type,
            input_text=input_text,
            provider=provider,
            requested_model=requested_model,
            prompt_version=prompt_version,
            stream=stream,
        )

    def start_call(
        self,
        trace_run: LLMTraceRun,
        *,
        message_count: int,
    ) -> LLMTraceCall:
        input_metadata = LLMStepInputMetadata(
            provider=trace_run.provider,
            requested_model=trace_run.requested_model,
            prompt_version=trace_run.prompt_version,
            stream=trace_run.stream,
            message_count=message_count,
        )
        step = self._traces.add_step(
            trace_run.record,
            step_type=TraceStepType.LLM_CALL,
            name="Call LLM",
            input_json=input_metadata.model_dump(mode="json"),
        )
        assert trace_run.record.started_at is not None
        assert step.started_at is not None
        return LLMTraceCall(
            run=trace_run,
            step=step,
            snapshot=LLMTraceSnapshot(
                run_type=trace_run.run_type,
                input_text=trace_run.input_text,
                provider=trace_run.provider,
                requested_model=trace_run.requested_model,
                prompt_version=trace_run.prompt_version,
                stream=trace_run.stream,
                message_count=message_count,
                run_started_at=trace_run.record.started_at,
                step_started_at=step.started_at,
            ),
        )
```

`complete_call()` must construct `LLMStepUsageMetadata` and
`LLMStepOutputMetadata`, finish the Step, copy metrics/provider/resolved model
to the Run, then finish the Run:

```python
def complete_call(
    self,
    trace_call: LLMTraceCall,
    *,
    response_model: str,
    metrics: LLMCallMetrics,
    output_text: str,
) -> TraceRun:
    usage = LLMStepUsageMetadata(
        input_tokens=metrics.input_tokens,
        output_tokens=metrics.output_tokens,
        total_tokens=metrics.total_tokens,
        estimated_cost=(
            format(metrics.estimated_cost, "f")
            if metrics.estimated_cost is not None
            else None
        ),
    )
    output = LLMStepOutputMetadata(
        provider=trace_call.run.provider,
        model=response_model,
        prompt_version=trace_call.run.prompt_version,
        usage=usage,
        latency_ms=metrics.latency_ms,
    )
    self._traces.finish_step(
        trace_call.step,
        output_json=output.model_dump(mode="json"),
    )
    record = trace_call.run.record
    record.model = response_model
    record.total_input_tokens = metrics.input_tokens
    record.total_output_tokens = metrics.output_tokens
    record.total_tokens = metrics.total_tokens
    record.estimated_cost = metrics.estimated_cost
    self._traces.finish_run(record, output_text=output_text)
    return record
```

`persist_failure()` must:

```python
snapshot = trace_call.snapshot
self._session.rollback()
try:
    failed_run = self.start_run(
        run_type=snapshot.run_type,
        input_text=snapshot.input_text,
        provider=snapshot.provider,
        requested_model=snapshot.requested_model,
        prompt_version=snapshot.prompt_version,
        stream=snapshot.stream,
        conversation_id=conversation_id,
        user_message_id=None,
    )
    failed_call = self.start_call(
        failed_run,
        message_count=snapshot.message_count,
    )
    failed_run.record.started_at = snapshot.run_started_at
    failed_call.step.started_at = snapshot.step_started_at
    safe_error = type(error).__name__
    self._traces.fail_step(failed_call.step, error_message=safe_error)
    self._traces.fail_run(failed_run.record, error_message=safe_error)
    self._session.commit()
    return failed_run.record
except Exception as trace_exc:
    self._session.rollback()
    logger.error(
        "llm_trace_persistence_failed",
        extra={"exception_type": type(trace_exc).__name__},
    )
    return None
```

This catch must never log `str(trace_exc)`. It exists so Trace persistence
cannot mask the original Provider error re-raised by the product service.

- [ ] **Step 5: Wire non-streaming Chat minimally**

In `ChatService.__init__`, create one recorder from the existing Session. In
`complete()` after the user Message and Provider request exist:

```python
trace_run = self._llm_traces.start_run(
    run_type=TraceRunType.CHAT,
    input_text=request.content,
    provider=request.provider,
    requested_model=request.model,
    prompt_version=CHAT_HISTORY_PROMPT_VERSION,
    stream=False,
    conversation_id=conversation.id,
    user_message_id=user_message.id,
)
trace_call = self._llm_traces.start_call(
    trace_run,
    message_count=len(provider_request.messages),
)
```

On `LLMProviderError`, log using the existing safe helper, call
`persist_failure(trace_call, error=exc, conversation_id=request.conversation_id)`,
then re-raise. On success, after the operational `LLMCall` and successful-turn
state exist, call:

```python
self._llm_traces.complete_call(
    trace_call,
    response_model=response.model,
    metrics=metrics,
    output_text=response.content,
)
```

Do not add a route dependency or API response field.

- [ ] **Step 6: Run GREEN and compatibility group**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_trace.py tests/test_trace_service.py tests/test_trace_context.py tests/test_llm_usage.py tests/test_chat_service.py tests/test_chat_api.py -q
```

Expected: all selected tests pass; success and Provider-failure Trace rows are
verified without changing existing API bodies.

- [ ] **Step 7: Review checkpoint**

Inspect transaction calls: only the explicit failed-audit path commits in the
new recorder; successful non-streaming Chat still relies on request commit;
`TraceService` remains commit/rollback-free. Confirm error strings and raw
prompts are absent from Step JSON/log extras. Do not stage or commit.

---

### Task 3: Streaming Chat And RAG Chat Hooks

**Files:**
- Modify: `backend/tests/test_chat_service.py`
- Modify: `backend/tests/test_chat_api.py`
- Modify: `backend/tests/test_rag_service.py`
- Modify: `backend/tests/test_rag_api.py`
- Modify: `backend/app/services/chat_service.py`
- Modify: `backend/app/services/rag_service.py`

**Interfaces:**
- Consumes: Task 2 recorder and both prompt-version constants.
- Produces: completed/failed streaming Chat Trace and completed/failed RAG Chat
  LLM Trace without retrieval-specific Steps.

- [ ] **Step 1: Add streaming RED assertions**

Extend streaming Service/API success tests to assert one completed `chat` Run
and one Step with:

```python
assert trace_run.metadata_json == {
    "prompt_version": "chat-history-v1",
    "stream": True,
}
assert trace_step.input_json["stream"] is True
assert trace_step.output_json["model"] == "resolved-stream-model"
assert trace_step.output_json["usage"]["total_tokens"] == 9
```

Extend Provider-failure/empty-stream API tests to preserve zero business-row
assertions and prove one committed failed Run/Step with no partial streamed
content or raw Provider diagnostic. Keep the early-consumer-cancellation test
expecting a full rollback and zero durable Trace rows.

- [ ] **Step 2: Add RAG Chat RED assertions**

Extend RAG Service/API success tests to assert:

```python
assert trace_run.run_type == TraceRunType.RAG_CHAT.value
assert trace_run.conversation_id == conversation.id
assert trace_run.user_message_id == result.user_message.id
assert trace_run.metadata_json["prompt_version"] == "naive-rag-v1"
assert len(trace_run.steps) == 1
assert trace_run.steps[0].step_type == TraceStepType.LLM_CALL.value
assert trace_run.steps[0].input_json["message_count"] == len(
    llm_provider.requests[0].messages
)
```

Extend ProviderRequest/invalid-response tests to prove the existing
Conversation survives, new Message/`LLMCall`/`RagQuery` rows roll back, and one
failed `rag_chat` Run/Step retains only the Conversation correlation and
exception class name.

Add or retain retrieval-failure tests proving zero durable Trace rows because
no LLM call was attempted.

- [ ] **Step 3: Run RED and verify only missing hooks fail**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_chat_service.py tests/test_chat_api.py tests/test_rag_service.py tests/test_rag_api.py -q
```

Expected: new streaming/RAG Trace assertions fail; existing Chat/RAG response,
rollback, retrieval, and redaction assertions remain green.

- [ ] **Step 4: Wire streaming Chat**

Create a Chat Run/Step before consuming the Provider stream, using
`stream=True`. On success, call `complete_call()` before the existing commit
and `done` event. In the generic exception branch, call `persist_failure()`
only when an `LLMProviderError` occurred and the call handle exists; then
re-raise so `stream_chat_events()` emits the existing safe SSE error.

Do not persist cancellation/`GeneratorExit`. The existing `finally` rollback
must remain for every path that did not reach the successful business commit.

- [ ] **Step 5: Wire RAG Chat**

Create a `rag_chat` Run after the existing Conversation and new user Message
are available. Run retrieval and prompt building without adding Steps. Start
the `llm_call` Step immediately before `provider.chat()`, using
`NAIVE_RAG_PROMPT_VERSION` and the built message count.

On Provider errors with an existing call handle, `persist_failure()` with the
pre-existing `request.conversation_id`, then re-raise. Retrieval/model/
Conversation/database failures use the existing rollback-only path. On
success, complete the call after operational `LLMCall`, RagQuery links, and
successful-turn state are ready.

- [ ] **Step 6: Run GREEN and complete matching backend group**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_trace.py tests/test_trace_models.py tests/test_trace_schemas.py tests/test_trace_types.py tests/test_trace_service.py tests/test_trace_context.py tests/test_llm_usage.py tests/test_chat_service.py tests/test_chat_api.py tests/test_rag_service.py tests/test_rag_api.py -q
```

Expected: all selected tests pass with only the existing Starlette/httpx
TestClient deprecation warning accepted.

- [ ] **Step 7: Review checkpoint**

Confirm all three paths use the same Recorder contract; RAG has exactly one
LLM Step and no retrieval/prompt/source Step; Agent/Tool files are unchanged;
API bodies contain no new field. Do not stage or commit.

---

### Task 4: Documentation, Full Verification, And Codex Review

**Files:**
- Modify: `docs/30-trace-observability.md`
- Modify: `docs/01-architecture.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs-plan/04-PLAN4/04-PLAN4-执行步骤表 (V1.0).md`
- Create: `docs/reviews/2026-08-08-plan4-m2-s1-s3-review.md`

**Interfaces:**
- Consumes: actual Task 1～3 code and fresh verification output.
- Produces: current-fact S1～S3 documentation, finding classification, and the
  `P4-M2-S4～S6` entry decision.

- [ ] **Step 1: Update current-fact documentation**

Document exactly:

- three supported LLM Trace paths;
- prompt-version and input/output metadata shapes;
- successful shared-transaction behavior;
- failed Provider audit rollback/recreate/commit behavior;
- class-name-only errors and excluded raw data;
- no Agent/Tool hook, retrieval Steps/candidates, API/UI, or cancellation
  persistence;
- Batch 4/S1～S3 complete, with all later batches still incomplete.

Add one Unreleased CHANGELOG bullet and update README English/Chinese stage
wording symmetrically. Do not change release version metadata.

- [ ] **Step 2: Run the fresh matching group**

Run the complete Task 3 matching command again and record the actual pass count
and warnings. Do not reuse the earlier GREEN count in the review.

- [ ] **Step 3: Run the full backend safely**

Create a uniquely named directory beneath `[System.IO.Path]::GetTempPath()`.
Set synthetic `DATABASE_URL`, `DOCUMENT_STORAGE_ROOT`, and `PYTHONPATH`, then
run the complete repository `backend/tests` suite from that temporary working
directory. Validate the resolved cleanup path is a child of the system temp
root before recursively deleting it.

Expected: all tests pass; only the known TestClient deprecation warning is
acceptable. Never run the full suite from `backend/` with its default database
URL.

- [ ] **Step 4: Run dependency and documentation gates**

Run:

```powershell
..\.venv\Scripts\python.exe -m pip check
git diff --check
git diff --cached --name-only
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git rev-parse 'v0.3.1^{}'
```

Validate all tracked/new Markdown local links, then scan changed text for
high-confidence private-key/API-token patterns. Confirm zero migration,
frontend, Agent/Tool, retrieval-candidate, Trace API/UI, database, generated
artifact, and network-client additions. Confirm `backend/ai_agent_lab.db` has
no Git status/diff and do not read it.

Treat `PROJECT_LEARNING_CHECKLIST.md` as a pre-existing user-owned untracked
path, not as batch output; verify it remains unmodified by comparing only its
Git state/name, never its contents.

- [ ] **Step 5: Write the Codex-only review from actual evidence**

Create `docs/reviews/2026-08-08-plan4-m2-s1-s3-review.md` with:

```markdown
# Plan 4 M2 S1～S3 LLM Trace Review

## Decision
## Scope And Git Baseline
## Acceptance Matrix
## Delivered Contracts
## RED/GREEN Evidence
## Fresh Verification
## Findings And Disposition
## Codex Self-Review
## Next-Step Gate
## Git Handoff
```

Classify every finding as must fix, fix later, recorded limitation, or not
applicable. Record actual commands/counts, not planned numbers. State whether
`P4-M2-S4～S6` may begin after the user's manual commit.

- [ ] **Step 6: Re-run final documentation/Git/hygiene checks**

After the review file exists, rerun local-link, secret/artifact/scope,
`git diff --check`, status, staged paths, and ref checks. Correct every mismatch
before completion.

- [ ] **Step 7: Perform final Codex self-review and handoff**

Confirm:

```text
- all three approved LLM paths and both success/failure contracts are covered;
- Provider adapters, DB schema/migrations, API responses, frontend, Agent/Tool,
  retrieval candidates, and later runtime are unchanged;
- no raw Provider error or secret marker is persisted/logged;
- successful and failed transaction boundaries are directly tested;
- docs match code and fresh evidence;
- the user-owned untracked file is untouched;
- staged paths remain zero.
```

Do not stage or commit. Suggest this manual commit message:

```text
feat(observability): trace chat llm calls
```
