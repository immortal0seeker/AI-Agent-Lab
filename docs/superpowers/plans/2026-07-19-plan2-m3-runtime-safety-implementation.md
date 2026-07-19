# Plan 2 M3 Agent Loop Runtime Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This repository explicitly forbids subagents and automatic commits for this batch, so execution stays inline and the user performs the final commit manually.

**Goal:** Complete `P2-M3-S7～S8` by adding a bounded multi-step Simple Agent Loop, per-Tool timeouts, structured persisted failures, bounded Tool observations, M3 documentation, and a full Codex self-review.

**Architecture:** Extend the existing backend-only `SimpleAgentService`; each Provider decision consumes one request-level step, Tool calls execute sequentially with their own timeout, and post-persistence runtime failures return a failed `SimpleAgentResult`. Keep full ToolResult persistence while bounding only the Provider observation. Reuse existing ORM states and migrations.

**Tech Stack:** Python 3.11, asyncio, Pydantic v2, SQLAlchemy 2, SQLite, pytest, FastAPI, React/TypeScript/Vitest/Vite verification only.

## Global Constraints

- Work only on `P2-M3-S7～S8`; do not start M4 or add Agent API/frontend behavior.
- Do not add migrations, ORM fields, runtime states, Provider capabilities, dependencies, or future directories.
- Do not implement retry, cancellation API, parallel Tool execution, RAG, Embedding, Memory, MCP, Shell Tool, `write_file`, or `delete_file`.
- Use only Mock Providers, controlled Tools, temporary SQLite, and temporary directories; never call a real Provider/network Tool or read real secrets/user databases.
- Preserve ordinary Chat/Streaming and tracked `supports_tools=false` model configuration.
- Service methods may `flush` but must not `commit`; the user performs the Git commit manually.

---

## File Structure

- Modify `backend/app/agents/simple_agent.py`: request/result contracts, bounded loop, failure result construction, timeout execution, observation compaction.
- Modify `backend/tests/test_simple_agent.py`: all S7 RED/GREEN behavior and SQLite round-trip evidence.
- Modify `backend/app/tools/base.py`: reject non-finite Tool timeouts found by S7 self-review.
- Modify `backend/tests/test_tool_base.py`: regression coverage for finite timeout policy.
- Create `docs/11-simple-agent-loop.md`: formal M3 Agent Loop contract and limitations.
- Modify `docs/10-tool-calling-design.md`: replace the one-round/S7-deferred statements with current bounded-loop facts.
- Modify `docs/03-llm-provider.md`: document failure ownership and observation bound without changing Provider transport.
- Modify `docs/00-project-overview.md` and `docs/01-architecture.md`: advance current backend capability and next batch to M4.
- Modify `README.md`, `README_CN.md`, and `CHANGELOG.md`: record completed backend M3 without claiming API/UI availability.
- Modify `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`: mark Batch 9/S7/S8 complete and record exact verification/review evidence.
- Modify `docs/superpowers/specs/2026-07-19-plan2-m3-runtime-safety-design.md`: only if implementation review finds a genuine design contradiction; otherwise leave unchanged.
- Modify this plan: mark each completed checkbox `[x]` as evidence; do not add unverifiable results in advance.

---

### Task 1: Request and Result Runtime Contracts

**Files:**
- Modify: `backend/tests/test_simple_agent.py`
- Modify: `backend/app/agents/simple_agent.py`

**Interfaces:**
- Consumes: existing `SimpleAgentRequest`, `SimpleAgentResult`.
- Produces: `SimpleAgentRequest.max_steps: int = 3` constrained to `1..10`; `SimpleAgentResult.assistant_message: Message | None`.

- [x] **Step 1: Write failing request-policy tests**

Extend the invalid-request parametrization with `max_steps=0`, `max_steps=11`, and `max_steps=True`. Add:

```python
def test_simple_agent_request_defaults_to_three_steps() -> None:
    request = SimpleAgentRequest(
        provider="mock",
        model="tool-model",
        content="hello",
    )

    assert request.max_steps == 3
```

Also add a typing assertion in an existing direct-answer test that successful results still provide a non-None assistant message before dereferencing it.

- [x] **Step 2: Run RED for the request contract**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -k "request" -q
```

Expected: fail because `max_steps` is absent or accepts invalid inputs.

- [x] **Step 3: Implement the minimal contract**

In `SimpleAgentRequest` add strict integer validation:

```python
max_steps: int = Field(default=3, ge=1, le=10, strict=True)
```

Change the result field without adding a second DTO:

```python
assistant_message: Message | None
```

Do not change successful construction behavior in this task.

- [x] **Step 4: Run GREEN and focused compatibility tests**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -q
```

Expected: all existing Simple Agent tests pass after only the request/result type change.

---

### Task 2: Bounded Multi-Step Loop and Structured Failures

**Files:**
- Modify: `backend/tests/test_simple_agent.py`
- Modify: `backend/app/agents/simple_agent.py`

**Interfaces:**
- Consumes: `SimpleAgentRequest.max_steps`, existing Provider-neutral `ChatMessage`/`LLMResponse`.
- Produces: a loop with at most `max_steps` Provider calls; failed `SimpleAgentResult` with `assistant_message=None`.

- [x] **Step 1: Write RED tests for a three-step successful loop**

Add a test whose Provider responses are:

1. one `read_file` Tool Call,
2. one `list_dir` Tool Call,
3. final text.

Assert:

```python
assert len(provider.requests) == 3
assert result.agent_run.status == "completed"
assert result.assistant_message is not None
assert [call.tool_call_id for call in result.tool_calls] == [
    "call_read",
    "call_list",
]
```

Verify the third request contains both earlier assistant Tool Call messages and both correlated observations in protocol order.

Add a second test with two Tool Calls in the first response and final text in the second response under `max_steps=2`; it must complete because calls in one Provider response consume one step.

- [x] **Step 2: Run RED for multi-step behavior**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -k "three_step or multiple_calls_count_as_one_step" -q
```

Expected: fail because the current service stops when the second response requests another Tool.

- [x] **Step 3: Write RED tests for the maximum-step failure result**

Replace the old exception-based second-response test with a test using `max_steps=2`. Assert:

```python
assert len(provider.requests) == 2
assert result.assistant_message is None
assert result.agent_run.status == "failed"
assert result.agent_run.error_message == (
    "Agent reached the maximum number of steps"
)
assert [call.tool_call_id for call in result.tool_calls] == ["call_1"]
stored_calls = session.scalars(select(ToolCall)).all()
assert [call.tool_call_id for call in stored_calls] == ["call_1"]
```

The Tool Call requested in the final Provider response must not execute and must not create a row. Add `max_steps=1` coverage proving an initial Tool response executes no Tool.

Change the blank-terminal test to expect a returned failed result with `assistant_message=None` and the existing error `Agent did not produce a final answer`.

- [x] **Step 4: Run RED for structured terminal failures**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -k "maximum or blank_terminal" -q
```

Expected: fail because the current service raises `AgentLoopIncompleteError`.

- [x] **Step 5: Implement the bounded loop**

Refactor `run()` so it owns one message list and one executed-call list:

```python
executed_tool_calls: list[ToolCall] = []
for step_index in range(request.max_steps):
    response = await provider.chat(
        ChatRequest(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=tool_definitions,
        )
    )
    if not response.tool_calls:
        return self._complete_run(
            request=request,
            response=response,
            conversation=conversation,
            user_message=user_message,
            agent_run=agent_run,
            started=started,
            is_new_conversation=is_new_conversation,
            tool_calls=tuple(executed_tool_calls),
        )
    if step_index == request.max_steps - 1:
        return self._fail_run(
            request=request,
            conversation=conversation,
            user_message=user_message,
            agent_run=agent_run,
            started=started,
            tool_calls=tuple(executed_tool_calls),
            error_message=MAX_STEPS_ERROR,
            model=response.model,
        )
    round_messages, round_calls = await self._execute_tool_round(
        agent_run=agent_run,
        response=response,
    )
    executed_tool_calls.extend(round_calls)
    messages.extend(round_messages)
```

The actual implementation may use small private methods, but it must not introduce a general Runtime engine. Remove the single-use `_run_tool_round()` control flow after equivalent tests are green.

Use this focused round helper contract:

```python
async def _execute_tool_round(
    self,
    *,
    agent_run: AgentRun,
    response: LLMResponse,
) -> tuple[list[ChatMessage], tuple[ToolCall, ...]]:
    """Execute one Provider Tool response and return protocol messages plus rows."""
```

Add module constants:

```python
MAX_STEPS_ERROR = "Agent reached the maximum number of steps"
INCOMPLETE_ERROR = "Agent did not produce a final answer"
```

- [x] **Step 6: Return failed results instead of raising terminal loop errors**

Replace `_fail_run()` with a constructor that marks and flushes the run, then returns:

```python
def _fail_run(
    self,
    *,
    request: SimpleAgentRequest,
    conversation: Conversation,
    user_message: Message,
    agent_run: AgentRun,
    started: float,
    tool_calls: tuple[ToolCall, ...],
    error_message: str,
    model: str,
) -> SimpleAgentResult:
    agent_run.status = "failed"
    agent_run.final_answer = None
    agent_run.error_message = error_message
    agent_run.ended_at = utc_now()
    agent_run.latency_ms = self._elapsed_ms(started)
    self._session.flush()
    return SimpleAgentResult(
        conversation=conversation,
        user_message=user_message,
        assistant_message=None,
        agent_run=agent_run,
        tool_calls=tool_calls,
        provider=request.provider,
        model=model,
    )
```

The returned value is therefore exactly:

```python
SimpleAgentResult(
    conversation=conversation,
    user_message=user_message,
    assistant_message=None,
    agent_run=agent_run,
    tool_calls=tuple(tool_calls),
    provider=request.provider,
    model=model,
)
```

It must set `status="failed"`, `final_answer=None`, fixed `error_message`, `ended_at`, and non-negative `latency_ms`. It must not update successful-turn Conversation metadata.

Keep the existing preflight model/provider exceptions unchanged and before persistence. Retain the exported `AgentLoopIncompleteError` for compatibility in this batch, but stop using it for post-AgentRun terminal outcomes.

- [x] **Step 7: Run GREEN and Agent/Provider regressions**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py tests/test_llm_provider_base.py tests/test_openai_compatible_provider.py -q
```

Expected: all selected tests pass and the Provider request count never exceeds `max_steps`.

---

### Task 3: Provider Failure Boundary

**Files:**
- Modify: `backend/tests/test_simple_agent.py`
- Modify: `backend/app/agents/simple_agent.py`

**Interfaces:**
- Consumes: `ProviderTimeoutError`, other `LLMProviderError` subclasses, the failed-result builder from Task 2.
- Produces: persisted safe failure results after AgentRun creation; unchanged preflight exceptions.

- [x] **Step 1: Add a raising Mock Provider and RED tests**

Add a Provider whose `chat()` appends the request and raises an injected exception. Parametrize:

```python
(
    (ProviderTimeoutError("synthetic-secret"), "Model request timed out"),
    (ProviderServerError("synthetic-secret"), "Model request failed"),
    (RuntimeError("synthetic-secret"), "Model request failed"),
)
```

For both first-call failure and a failure after one completed Tool round, assert the service returns a failed result, preserves already terminal ToolCalls, does not expose `synthetic-secret`, sets terminal timing, and remains committable/reloadable.

- [x] **Step 2: Run RED for Provider failure returns**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -k "provider_failure or provider_timeout" -q
```

Expected: errors propagate from the current Provider call boundary.

- [x] **Step 3: Implement a narrow Provider request boundary**

Import `ProviderTimeoutError`. Around only `await provider.chat(request)`:

```python
try:
    response = await provider.chat(chat_request)
except ProviderTimeoutError:
    return self._fail_run(
        request=request,
        conversation=conversation,
        user_message=user_message,
        agent_run=agent_run,
        started=started,
        tool_calls=tuple(executed_tool_calls),
        error_message="Model request timed out",
        model=request.model,
    )
except Exception:
    return self._fail_run(
        request=request,
        conversation=conversation,
        user_message=user_message,
        agent_run=agent_run,
        started=started,
        tool_calls=tuple(executed_tool_calls),
        error_message="Model request failed",
        model=request.model,
    )
```

Do not wrap database flushes, Conversation persistence, Tool execution, or result construction in this catch. Do not catch `BaseException`; cancellation/system-exit signals must propagate.

- [x] **Step 4: Run GREEN and confirm secrets do not leak**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -k "provider" -q
```

Expected: all Provider failure tests pass; neither result fields nor persisted rows contain `synthetic-secret`.

---

### Task 4: Per-Tool Timeout

**Files:**
- Modify: `backend/tests/test_simple_agent.py`
- Modify: `backend/app/agents/simple_agent.py`

**Interfaces:**
- Consumes: `Tool.timeout_seconds`, existing `ToolCall.status="timeout"` ORM constraint.
- Produces: internal execution outcome carrying `ToolResult` and one of `success|failed|timeout`.

- [x] **Step 1: Extend the controlled Tool and write RED timeout tests**

Allow `ControlledTool` to receive `name` and `timeout_seconds`. In `mode="timeout"`, await `asyncio.sleep(0.05)` inside `try/finally` so the test fails quickly under the old behavior and can prove cancellation reached the coroutine after the timeout is implemented.

Add one test with a timed-out Tool followed by a successful differently named Tool in the same Provider response. The second Provider response returns final text. Assert:

```python
assert [call.status for call in result.tool_calls] == ["timeout", "success"]
assert result.tool_calls[0].error_message == "Tool execution timed out"
assert timeout_observation["success"] is False
assert timeout_observation["error"] == "Tool execution timed out"
assert result.agent_run.status == "completed"
```

Also assert the timed-out coroutine's `finally` marker ran and the second Tool executed.

- [x] **Step 2: Run RED for Tool timeout**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -k "tool_timeout" -q
```

Expected: fail after roughly 0.05 seconds because the Tool returns success instead of timing out; the production behavior must use Tool metadata.

- [x] **Step 3: Implement timeout-aware execution outcome**

Add an internal frozen dataclass:

```python
@dataclass(frozen=True, slots=True)
class _ToolExecution:
    result: ToolResult
    status: Literal["success", "failed", "timeout"]
```

After lookup and validation, wrap only `tool.run(validated_arguments)`:

```python
try:
    async with asyncio.timeout(tool.timeout_seconds):
        result = await tool.run(validated_arguments)
except TimeoutError:
    return _ToolExecution(
        result=ToolResult(
            tool_name=call.tool_name,
            success=False,
            error="Tool execution timed out",
        ),
        status="timeout",
    )
```

Map all existing outcomes to `_ToolExecution`; `_record_tool_call()` writes `execution.status` rather than deriving every failure as `failed`. Keep the existing JSON/name/exception safety checks.

- [x] **Step 4: Run GREEN plus Tool regressions**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py tests/test_tool_base.py tests/test_tool_read_file.py tests/test_tool_list_dir.py -q
```

Expected: timeout and all existing Tool failure behaviors pass.

---

### Task 5: Bounded Tool Observation

**Files:**
- Modify: `backend/tests/test_simple_agent.py`
- Modify: `backend/app/agents/simple_agent.py`

**Interfaces:**
- Consumes: complete validated `ToolResult`.
- Produces: `DEFAULT_MAX_TOOL_OBSERVATION_CHARS = 32_000`; constructor override with integer minimum 1,024; deterministic bounded JSON sent only to Provider.

- [x] **Step 1: Write RED constructor-policy tests**

Construct `SimpleAgentService` with the normal `session`, `registry`, `providers`, and `tools` dependencies plus `max_tool_observation_chars=True`, a float, and `1023`; assert each raises a stable `TypeError` or `ValueError` before execution. Assert exactly `1024` is accepted.

- [x] **Step 2: Write RED compatibility and truncation tests**

Add a controlled Tool returning:

```python
ToolResult(
    tool_name=self.name,
    success=True,
    content="x" * 2_000,
    data={"large": "y" * 2_000},
    metadata={"large": "z" * 2_000},
)
```

Run the service with `max_tool_observation_chars=1024`. Assert:

- the observation string length is at most 1024 and parses as JSON;
- `tool_name` and `success` are preserved;
- `data is None`;
- `metadata == {"observation_truncated": True, "original_characters": N}`;
- content ends with `…` when truncated;
- the persisted `result_json` retains full content/data/metadata;
- the original ToolResult is not mutated.

Add a small-result test proving exact observation equality with the existing full deterministic ToolResult JSON.

- [x] **Step 3: Run RED for observation bounds**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -k "observation" -q
```

Expected: oversized observations exceed the configured limit and the constructor does not yet validate the limit.

- [x] **Step 4: Implement deterministic compaction**

Add constants:

```python
DEFAULT_MAX_TOOL_OBSERVATION_CHARS = 32_000
MAX_COMPACT_ERROR_CHARS = 256
```

Validate the constructor input with explicit bool/type checks and minimum 1,024. Convert `_serialize_tool_result()` to an instance method:

1. Serialize the full `mode="json"` dict using existing compact UTF-8 JSON options.
2. Return it unchanged when within the limit.
3. Build a compact dict with `data=None`, special metadata, error truncated to at most 256 characters with a final `…`, and initially empty content.
4. Binary-search the greatest content prefix whose serialized envelope fits the limit. A truncated non-empty content ends in `…`; zero budget yields an empty string.
5. Assert or defensively check the final serialized length before return; never return invalid JSON or mutate the input.

- [x] **Step 5: Run GREEN and all Agent/Tool tests**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py tests/test_tool_*.py -q
```

Expected: all selected tests pass, including the previous NaN ToolResult boundary.

---

### Task 6: Persistence Round-Trips and Focused M3 Review

**Files:**
- Modify: `backend/tests/test_simple_agent.py`
- Modify: `backend/app/agents/simple_agent.py` only if RED exposes a production defect.

**Interfaces:**
- Consumes: all Tasks 1～5 behavior.
- Produces: commit/reload evidence for successful multi-step, max-step failure, Provider failure, and timeout ToolCall.

- [x] **Step 1: Add round-trip assertions**

For each terminal class, commit, expire, and reload via a fresh query. Assert:

- `AgentRun.status`, `final_answer`, `error_message`, start/end/latency;
- all executed ToolCall terminal states/results/errors/timing;
- no ToolCall for a max-step response that was not executed;
- failed runs do not append an assistant Message or update successful-turn metadata;
- returned `tool_calls` preserve actual execution order even though the ORM has no sequence field.

- [x] **Step 2: Run focused M3 suite**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py tests/test_agent_models.py tests/test_agent_migrations.py tests/test_llm_provider_base.py tests/test_openai_compatible_provider.py tests/test_llm_tool_adapter.py tests/test_chat_service.py tests/test_chat_api.py -q
```

Expected: all focused M3 and Plan 1 regression tests pass.

- [x] **Step 3: Perform Codex code self-review**

Review the full M3 implementation against the source plan and both M3 specs. Classify every issue as:

- must fix now;
- fix in later batch;
- record as limitation;
- not applicable with reason.

Explicitly check: off-by-one step counting, final-step Tool non-execution, multiple Tool Calls per step, timeout cancellation, Provider exception scope, database failure propagation, failed-run transaction usability, error/secret leakage, observation length under escaped JSON, persistence mutation, existing Chat/Streaming compatibility, no new state/migration, and no M4/future Plan surface.

- [x] **Step 4: Fix each must-fix issue with a new RED/GREEN test**

For every must-fix defect, first add the smallest reproducing test and run it to observe the expected failure. Apply one root-cause fix, rerun the focused test, then rerun the focused M3 suite. Do not bundle unrelated refactors.

---

### Task 7: S8 Formal Documentation and Execution Record

**Files:**
- Create: `docs/11-simple-agent-loop.md`
- Modify: `docs/10-tool-calling-design.md`
- Modify: `docs/03-llm-provider.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`
- Modify: `docs/superpowers/plans/2026-07-19-plan2-m3-runtime-safety-implementation.md`

**Interfaces:**
- Consumes: verified actual implementation and test outputs.
- Produces: accurate M3 documentation, review classification, M4 handoff, and completed checklist.

- [x] **Step 1: Create `docs/11-simple-agent-loop.md`**

Write concrete sections for ownership, request/result API, loop sequence, max-step examples, timeout behavior, Tool observation shape/compaction, AgentRun/ToolCall state mapping, failure/transaction semantics, tests, security boundaries, limitations, and M4 integration. State explicitly:

- backend service only; no Agent API/UI yet;
- default 3 Provider decisions, maximum 10;
- no automatic retry;
- cooperative cancellation limitation for thread-backed Tool work;
- tracked models still advertise `supports_tools=false`;
- no real Provider acceptance evidence.

- [x] **Step 2: Synchronize existing docs**

Replace statements that S7 will later add max steps/timeout/failure returns. Preserve historical S4～S6 acceptance records as historical facts, but add a current S7～S8 record so readers do not mistake them for current limitations. Do not claim strict persisted ToolCall sequence, Agent-linked LLMCall, API/UI, streaming Tool Calls, retry, cancel, or later-Plan features.

- [x] **Step 3: Update Plan 2 execution status**

Mark Batch 9, `P2-M3-S7`, and `P2-M3-S8` complete only after the matching verification exists. Add a dated acceptance table with TDD RED/GREEN evidence, full verification counts, Codex review findings/fixes, security checks, accepted limitations, and the exact next range `P2-M4-S1～S3`. Update the final acceptance and Plan 2→3 bridge rows that M3 now satisfies, without marking M4/M5 work complete.

- [x] **Step 4: Mark implementation-plan checkboxes accurately**

Change only completed items to `[x]`. No checkbox may be checked based solely on intended behavior or an older test run.

- [x] **Step 5: Check docs for placeholders and stale contradictions**

Run:

```powershell
Get-ChildItem -LiteralPath docs,docs-plan -Recurse -File -Filter '*.md' |
  Select-String -Pattern 'TBD|TODO|P2-M3-S7.*未完成|通用 max_steps.*后续|Tool timeout.*后续' -Encoding UTF8
```

Expected: no unresolved current-state placeholder or stale S7 deferral; historical descriptions may remain only when clearly dated.

---

### Task 8: Fresh Full Verification and Final Boundary Review

**Files:**
- No production edits unless a fresh RED exposes a defect; any fix must follow TDD and then repeat this task.

**Interfaces:**
- Consumes: complete S7～S8 diff.
- Produces: final evidence required for the user's manual commit.

- [x] **Step 1: Run complete backend verification**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m pip check
```

Expected: zero failures and no broken requirements; record the exact test count and warnings.

- [x] **Step 2: Verify migrations only on a fresh temporary SQLite database**

Create a unique file under the system temp directory, set `DATABASE_URL` only for the child PowerShell process, and run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current --check-heads
..\.venv\Scripts\python.exe -m alembic check
```

Resolve and verify the temporary database path is under `[System.IO.Path]::GetTempPath()` before deleting only that file in a `finally` block. Never reference `backend/ai_agent_lab.db` or another existing database.

- [x] **Step 3: Run frontend verification**

From `frontend/`:

```powershell
npm run typecheck
npm run test -- --run
npm run build
```

Expected: TypeScript, all Vitest files/tests, and production build pass. The build may use the already approved `npm run build` escalation if managed sandbox permissions require it.

- [x] **Step 4: Run FastAPI smoke without real Providers**

Use FastAPI `TestClient` with a temporary/in-memory test database and no Provider initialization. Assert `/api/v1/health` and `/openapi.json` return 200, the server-generated request ID is a UUID, and a client-supplied ID is not trusted.

- [x] **Step 5: Run documentation, secret, artifact, and Plan-boundary checks**

Verify all local Markdown links resolve. Scan tracked and changed text for real-secret signatures while treating documented placeholders/test literals as non-secrets. Confirm status contains no `.env`, database, `__pycache__`, `.pyc`, coverage, or frontend `dist` artifacts. Confirm there are no changes under:

- `backend/alembic/`
- `backend/app/api/`
- `frontend/src/`
- `backend/app/providers/llm/models.json`

Confirm no `web_fetch` runtime, RAG, Embedding, Memory, MCP, Shell, write/delete Tool, retry, Agent API/UI, or M4 implementation appeared.

- [x] **Step 6: Run final Git checks**

Run:

```powershell
git diff --check
git status --short --branch
git diff --stat
git diff -- backend/app/agents/simple_agent.py backend/tests/test_simple_agent.py
```

Confirm `HEAD` and `origin/main` remain at the starting commit, nothing is staged, and the diff contains only S7～S8 files.

- [x] **Step 7: Final Codex self-review and handoff**

Re-read the source `P2-M3-S7～S8` rows and create a requirement-to-evidence checklist. Report must-fix findings and their RED/GREEN evidence, later-batch items, accepted limitations, and not-applicable items. If no blocking issue remains, state that M3 is complete and the repository can enter `P2-M4-S1～S3`, but do not implement M4.

Suggested manual commit message after all checks pass:

```text
feat(agent): add bounded agent loop runtime policy
```
