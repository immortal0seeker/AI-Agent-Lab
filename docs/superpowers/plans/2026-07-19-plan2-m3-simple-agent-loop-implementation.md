# Plan 2 M3 Simple Agent Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Repository and user instructions require inline execution without subagents for this batch.

**Goal:** Complete `P2-M3-S4～S6` with a Provider-neutral single-tool-round Agent service that executes registered Tools, backfills observations, and persists AgentRun/ToolCall audit records.

**Architecture:** Extend the typed Provider message DTO so the OpenAI-compatible adapter alone owns assistant Tool Call and Tool observation wire serialization. Add a small `SimpleAgentService` that owns the two-call orchestration, Tool validation/execution, Conversation messages, and existing AgentRun/ToolCall state updates without adding API routes, frontend code, statuses, or migrations.

**Tech Stack:** Python 3.11, Pydantic v2, SQLAlchemy 2, SQLite, FastAPI project services, pytest, JSON Schema, existing Tool Registry and Mock Providers.

## Global Constraints

- Work only on `P2-M3-S4～S6`; do not implement `max_steps`, timeout enforcement, retry, cancel, parallel Tool execution, Agent API/UI, streaming Tool Calls, RAG, Embedding, Memory, MCP, Shell Tool, or file-writing/deleting tools.
- The loop permits one Tool round: first response may contain multiple ordered calls; after observations, exactly one second Provider call must produce non-blank final text and no further Tool Calls.
- Do not call a real Provider, paid API, network Tool, real `.env`, credential path, or user database. Use Mock Providers, disposable SQLite, `tmp_path`, and built-in read-only Tools only.
- Keep the tracked example model at `supports_tools=false`; service tests inject a tools-capable ModelRegistry entry.
- Reuse existing AgentRun/ToolCall columns and statuses. Do not create a migration or sequence field.
- The service flushes but never commits. Tests explicitly commit only successful executions before querying a fresh session state.
- Ordinary Plan 1 Chat and Streaming payloads and behavior must remain backward compatible.
- The user creates commits manually. Do not stage, commit, push, tag, switch branches, or create a worktree.
- Codex self-review is the only batch review. Do not use Claude Code; do not request Fable 5 before all six Plans are complete.

---

### Task 1: Provider-Neutral Tool Observation Messages

**Files:**
- Modify: `backend/app/providers/llm/base.py`
- Modify: `backend/app/providers/llm/openai_compatible.py`
- Test: `backend/tests/test_llm_provider_base.py`
- Test: `backend/tests/test_openai_compatible_provider.py`

**Interfaces:**
- Produces: validated `ChatMessage(role, content, tool_calls, tool_call_id)`.
- Produces: `OpenAICompatibleProvider._serialize_message(message) -> dict[str, Any]`.
- Consumed by: Tasks 2～4 through `ChatRequest.messages`.

- [x] **Step 1: Write failing ChatMessage contract tests**

Add tests proving ordinary messages remain valid, assistant Tool Call messages and Tool observations are expressible, invalid field combinations fail, duplicate assistant call IDs fail, and manually constructed Tool arguments must be standard JSON objects:

```python
def test_chat_message_supports_tool_call_and_observation() -> None:
    call = LLMToolCall(
        tool_call_id="call_1",
        tool_name="read_file",
        arguments={"path": "README.md"},
    )

    assistant = ChatMessage(
        role="assistant",
        content=None,
        tool_calls=(call,),
    )
    observation = ChatMessage(
        role="tool",
        content='{"success":true}',
        tool_call_id="call_1",
    )

    assert assistant.tool_calls == (call,)
    assert observation.tool_call_id == "call_1"


@pytest.mark.parametrize(
    "message",
    [
        {"role": "user", "content": None},
        {"role": "user", "content": "hello", "tool_call_id": "call_1"},
        {"role": "assistant", "content": None},
        {"role": "tool", "content": "result"},
    ],
)
def test_chat_message_rejects_invalid_role_field_combinations(
    message: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ChatMessage.model_validate(message)


@pytest.mark.parametrize("arguments", [{"value": object()}, {"value": float("nan")}])
def test_llm_tool_call_rejects_non_standard_json_arguments(
    arguments: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="JSON serializable"):
        LLMToolCall(
            tool_call_id="call_1",
            tool_name="read_file",
            arguments=arguments,
        )
```

Use separate explicit tests for duplicate call IDs and for `system`/`user`/ordinary `assistant` compatibility. A forbidden non-empty Tool Call on `role="tool"` covers that role's extra-field boundary.

- [x] **Step 2: Run RED for the contract**

Run from `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_provider_base.py -q
```

Expected: new Tool observation construction fails because role `tool` and message correlation fields do not exist; invalid argument tests also expose missing JSON validation.

- [x] **Step 3: Implement the minimal typed message contract**

In `base.py`, make `ChatMessage` frozen/forbid-extra and add a model validator:

```python
class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: tuple[LLMToolCall, ...] = ()
    tool_call_id: LLMToolCallIdentifier | None = None

    @model_validator(mode="after")
    def validate_message_shape(self) -> Self:
        if self.role in {"system", "user"}:
            if self.content is None or self.tool_calls or self.tool_call_id is not None:
                raise ValueError("text messages require content only")
            return self
        if self.role == "assistant":
            if self.tool_call_id is not None:
                raise ValueError("assistant messages must not include tool_call_id")
            if not self.tool_calls and self.content is None:
                raise ValueError("assistant messages require content or tool calls")
            ids = [call.tool_call_id for call in self.tool_calls]
            if len(ids) != len(set(ids)):
                raise ValueError("assistant tool call ids must be unique")
            return self
        if self.content is None or self.tool_call_id is None or self.tool_calls:
            raise ValueError("tool messages require content and tool_call_id only")
        return self
```

Extend `LLMToolCall.copy_arguments()` to deep-copy and run `json.dumps(copied, allow_nan=False)`, converting failure to `ValueError("tool arguments must be JSON serializable")`.

- [x] **Step 4: Run GREEN for the contract**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_provider_base.py -q
```

Expected: all Provider base tests pass.

- [x] **Step 5: Write failing OpenAI-compatible observation payload test**

Add one exact-payload test using MockTransport:

```python
def test_chat_serializes_assistant_tool_calls_and_tool_observations() -> None:
    call = LLMToolCall(
        tool_call_id="call_1",
        tool_name="read_file",
        arguments={"path": "指南.md"},
    )
    messages = [
        ChatMessage(role="user", content="读取文件"),
        ChatMessage(role="assistant", content=None, tool_calls=(call,)),
        ChatMessage(
            role="tool",
            content='{"tool_name":"read_file","success":true}',
            tool_call_id="call_1",
        ),
    ]

    # Capture MockTransport JSON and return a normal text response.
    assert payload["messages"] == [
        {"role": "user", "content": "读取文件"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": '{"path":"指南.md"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "content": '{"tool_name":"read_file","success":true}',
            "tool_call_id": "call_1",
        },
    ]
```

- [x] **Step 6: Run RED for wire serialization**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_openai_compatible_provider.py -q
```

Expected: the new request fails JSON serialization because `_build_payload()` still uses raw `model_dump()` and normalized LLMToolCall fields do not match the wire format.

- [x] **Step 7: Implement explicit message serialization**

Add `_serialize_message()` and replace the current message `model_dump()` call:

```python
@staticmethod
def _serialize_message(message: ChatMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "role": message.role,
        "content": message.content,
    }
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": call.tool_call_id,
                "type": "function",
                "function": {
                    "name": call.tool_name,
                    "arguments": json.dumps(
                        call.arguments,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        allow_nan=False,
                    ),
                },
            }
            for call in message.tool_calls
        ]
    if message.tool_call_id is not None:
        payload["tool_call_id"] = message.tool_call_id
    return payload
```

Import `ChatMessage` in the adapter. Keep ordinary payload snapshots exactly unchanged.

- [x] **Step 8: Run GREEN and Plan 1 Provider regression**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_openai_compatible_provider.py tests/test_chat_service.py tests/test_chat_api.py -q
```

Expected: all selected tests pass; ordinary messages still serialize as only role/content.

---

### Task 2: S4 Direct-Answer Simple Agent Service

**Files:**
- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/agents/errors.py`
- Create: `backend/app/agents/simple_agent.py`
- Create: `backend/tests/test_simple_agent.py`

**Interfaces:**
- Produces: `SimpleAgentRequest`, `SimpleAgentResult`, `SimpleAgentService.run()`.
- Produces: `AgentError`, `AgentModelNotFoundError`, `AgentModelToolsUnsupportedError`, `AgentProviderUnavailableError`, `AgentLoopIncompleteError`.
- Consumes: ModelRegistry, BaseLLMProvider mapping, ToolRegistry, ConversationService, AgentRun/ToolCall ORM, and `build_llm_tool_definitions()`.

- [x] **Step 1: Write failing request and capability-gate tests**

Create local SQLite and ModelRegistry helpers. Test invalid blank content/provider/model and ranges through `SimpleAgentRequest`, then test missing model, `supports_tools=false`, and missing Provider without creating AgentRun rows:

```python
def create_registry(*, supports_tools: bool = True) -> ModelRegistry:
    return ModelRegistry([
        ModelInfo(
            provider="mock",
            model="tool-model",
            display_name="Tool Model",
            supports_tools=supports_tools,
        )
    ])


def test_agent_rejects_model_without_tool_capability_before_persistence(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    service = SimpleAgentService(
        session,
        registry=create_registry(supports_tools=False),
        providers={"mock": SequenceProvider([])},
        tools=ToolRegistry(),
    )

    with pytest.raises(AgentModelToolsUnsupportedError):
        asyncio.run(service.run(SimpleAgentRequest(
            provider="mock", model="tool-model", content="hello"
        )))

    assert session.scalars(select(AgentRun)).all() == []
    session.close()
    engine.dispose()
```

- [x] **Step 2: Run RED for Agent domain types**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -q
```

Expected: collection fails because `app.agents` does not exist.

- [x] **Step 3: Implement request/result/errors and constructor gates**

Create `errors.py` with fixed domain errors derived from `ServiceError`; store provider/model attributes but do not store goal or Tool arguments. In `simple_agent.py` define:

```python
NonEmptyIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class SimpleAgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    conversation_id: UUID | None = None
    provider: NonEmptyIdentifier = Field(max_length=100)
    model: NonEmptyIdentifier = Field(max_length=255)
    content: str = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value


@dataclass(frozen=True, slots=True)
class SimpleAgentResult:
    conversation: Conversation
    user_message: Message
    assistant_message: Message
    agent_run: AgentRun
    tool_calls: tuple[ToolCall, ...]
    provider: str
    model: str
```

Use these exact errors and lookup helper:

```python
class AgentError(ServiceError):
    """Simple Agent 服务边界的基础异常。"""


class AgentModelNotFoundError(AgentError):
    def __init__(self, provider: str, model: str) -> None:
        super().__init__(f"Model not found: {provider}/{model}")
        self.provider = provider
        self.model = model


class AgentModelToolsUnsupportedError(AgentError):
    def __init__(self, provider: str, model: str) -> None:
        super().__init__(f"Model does not support tools: {provider}/{model}")
        self.provider = provider
        self.model = model


class AgentProviderUnavailableError(AgentError):
    def __init__(self, provider: str) -> None:
        super().__init__(f"Provider is not configured: {provider}")
        self.provider = provider


class AgentLoopIncompleteError(AgentError):
    def __init__(self) -> None:
        super().__init__("Agent did not produce a final answer")
```

Constructor stores dependencies. Implement:

```python
def _resolve_model_and_provider(
    self,
    request: SimpleAgentRequest,
) -> tuple[ModelInfo, BaseLLMProvider]:
    model_info = self._registry.get_model(request.provider, request.model)
    if model_info is None:
        raise AgentModelNotFoundError(request.provider, request.model)
    if not model_info.supports_tools:
        raise AgentModelToolsUnsupportedError(request.provider, request.model)
    provider = self._providers.get(request.provider)
    if provider is None:
        raise AgentProviderUnavailableError(request.provider)
    return model_info, provider
```

- [x] **Step 4: Run GREEN for gates only**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -q
```

Expected: request/gate tests pass while direct-flow test is not added yet.

- [x] **Step 5: Write failing direct-answer flow test**

Use a SequenceProvider returning one text response and assert:

```python
assert len(provider.requests) == 1
assert [definition.function.name for definition in provider.requests[0].tools] == [
    "read_file", "list_dir"
]
assert [(message.role, message.content) for message in provider.requests[0].messages] == [
    ("user", "Answer directly")
]
assert result.agent_run.status == "completed"
assert result.agent_run.final_answer == "Direct answer"
assert result.agent_run.user_message_id == result.user_message.id
assert result.tool_calls == ()
assert result.assistant_message.content == "Direct answer"
assert result.agent_run.started_at is not None
assert result.agent_run.ended_at is not None
assert result.agent_run.latency_ms is not None
```

Also assert a supplied existing Conversation history is included and new-conversation title/provider/model metadata is updated only on success.

- [x] **Step 6: Run RED for S4**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -q
```

Expected: direct flow fails because `run()` has no orchestration implementation.

- [x] **Step 7: Implement minimal direct-answer orchestration**

Implement `run()` through the first Provider response:

```python
async def run(self, request: SimpleAgentRequest) -> SimpleAgentResult:
    _, provider = self._resolve_model_and_provider(request)
    is_new = request.conversation_id is None
    conversation = self._create_or_load_conversation(request)
    user_message = self._conversations.append_message(MessageCreate(...))
    history = self._conversations.list_messages(conversation.id)
    started_at = utc_now()
    started = perf_counter()
    agent_run = AgentRun(
        conversation=conversation,
        user_message=user_message,
        status="running",
        goal=request.content,
        started_at=started_at,
    )
    self._session.add(agent_run)
    self._session.flush()
    messages = [ChatMessage(role=m.role, content=m.content) for m in history]
    tools = build_llm_tool_definitions(self._tools)
    response = await provider.chat(ChatRequest(...))
    if response.tool_calls:
        return await self._run_tool_round(...)
    return self._complete_run(...)
```

`_complete_run()` requires `content is not None and content.strip()`, appends the assistant Message, updates AgentRun terminal fields using monotonic elapsed milliseconds, records successful Conversation metadata, flushes, and returns `SimpleAgentResult`. Blank terminal text marks the run failed and raises `AgentLoopIncompleteError` without a third Provider call.

- [x] **Step 8: Run GREEN for S4 and Chat regression**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py tests/test_chat_service.py tests/test_chat_api.py -q
```

Expected: all selected tests pass; direct agent uses one Provider call and creates no ToolCall.

---

### Task 3: S5 Tool Selection, Execution, and Observation Backfill

**Files:**
- Modify: `backend/app/agents/simple_agent.py`
- Modify: `backend/tests/test_simple_agent.py`

**Interfaces:**
- Produces: single Tool-round execution inside `SimpleAgentService`.
- Consumes: ordered `LLMResponse.tool_calls`, `validate_tool_arguments()`, Tool `run()`, and Task 1 message DTOs.

- [x] **Step 1: Write failing read_file closed-loop test**

Create a temporary UTF-8 file, register builtins, return one `read_file` call then a final text response. Assert exact second request shape:

```python
assert len(provider.requests) == 2
second_messages = provider.requests[1].messages
assert second_messages[-2].role == "assistant"
assert second_messages[-2].tool_calls[0].tool_call_id == "call_1"
assert second_messages[-1].role == "tool"
assert second_messages[-1].tool_call_id == "call_1"
observation = json.loads(second_messages[-1].content or "")
assert observation["tool_name"] == "read_file"
assert observation["success"] is True
assert observation["content"] == "workspace guide"
assert result.assistant_message.content == "The guide was read"
```

- [x] **Step 2: Run RED for S5 happy path**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -q
```

Expected: `_run_tool_round()` is absent or does not execute/backfill the Tool.

- [x] **Step 3: Implement one ordered Tool round**

Set AgentRun to `waiting_tool`, iterate calls in response order, execute each through `_execute_tool_call()`, and append observations after one assistant Tool Call message:

```python
assistant_call_message = ChatMessage(
    role="assistant",
    content=first_response.content,
    tool_calls=first_response.tool_calls,
)
observations = [
    ChatMessage(
        role="tool",
        content=_serialize_tool_result(result),
        tool_call_id=call.tool_call_id,
    )
    for call, result in executed
]
agent_run.status = "running"
second_response = await provider.chat(ChatRequest(
    messages=[*messages, assistant_call_message, *observations],
    model=request.model,
    temperature=request.temperature,
    max_tokens=request.max_tokens,
    tools=tool_definitions,
))
```

The second response must have no Tool Calls and non-blank content; otherwise `_fail_run()` and raise `AgentLoopIncompleteError`. Never make a third Provider call. In S5, `_execute_tool(call) -> ToolResult` and `_run_tool_round()` keep ToolResults in a local ordered list; `SimpleAgentResult.tool_calls` remains empty until Task 4 adds S6 persistence.

- [x] **Step 4: Run GREEN for read_file loop**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -q
```

Expected: read_file closed loop passes.

- [x] **Step 5: Write failing ordered multi-call and safe-failure tests**

Add tests for:

- first response calls `read_file` then `list_dir`; second request observations preserve Provider order;
- unknown Tool yields failed observation with `error == "Tool is not available"`;
- invalid arguments yield the stable safe `ToolArgumentValidationError` summary without rejected values;
- Tool returning failed ToolResult remains failed but is observed;
- Tool raising `RuntimeError("synthetic-secret")` yields `error == "Tool execution failed"` and no secret in observation/ORM/error;
- Tool returning a mismatched `tool_name` also yields `Tool execution failed`;
- second response requests another Tool and raises `AgentLoopIncompleteError` after exactly two calls.

- [x] **Step 6: Run RED for edge behavior**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -q
```

Expected: at least unknown/malformed/exception/multiple-call behavior is missing.

- [x] **Step 7: Implement safe Tool result normalization**

Use these fixed boundaries:

```python
try:
    tool = self._tools.get_tool(call.tool_name)
except ToolNotFoundError:
    return ToolResult(
        tool_name=call.tool_name,
        success=False,
        error="Tool is not available",
    )

try:
    validated = validate_tool_arguments(tool, call.arguments)
except ToolArgumentValidationError as exc:
    return ToolResult(
        tool_name=call.tool_name,
        success=False,
        error=str(exc),
    )

try:
    result = await tool.run(validated)
    if result.tool_name != call.tool_name:
        raise ValueError("tool result name mismatch")
    return result
except Exception:
    return ToolResult(
        tool_name=call.tool_name,
        success=False,
        error="Tool execution failed",
    )
```

Do not log caught exception text. Serialize ToolResult with `model_dump(mode="json")` and deterministic compact standard JSON.

- [x] **Step 8: Run GREEN for S5**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py tests/test_tool_registry.py tests/test_tool_validation.py tests/test_tool_read_file.py tests/test_tool_list_dir.py -q
```

Expected: all Agent and Tool tests pass.

---

### Task 4: S6 AgentRun and ToolCall Persistence

**Files:**
- Modify: `backend/app/agents/simple_agent.py`
- Modify: `backend/tests/test_simple_agent.py`

**Interfaces:**
- Produces: one ToolCall ORM row per attempted Provider Tool Call with safe terminal result and timing.
- Consumes: existing AgentRun/ToolCall ORM; no schema or migration changes.

- [x] **Step 1: Write failing successful persistence round-trip test**

After the read_file flow, commit, expire, and query using SQLAlchemy:

```python
session.commit()
session.expire_all()
loaded_run = session.scalar(select(AgentRun).where(AgentRun.id == result.agent_run.id))
loaded_calls = session.scalars(
    select(ToolCall).where(ToolCall.agent_run_id == result.agent_run.id)
).all()

assert loaded_run is not None
assert loaded_run.status == "completed"
assert loaded_run.final_answer == "The guide was read"
assert loaded_run.error_message is None
assert loaded_run.user_message_id == result.user_message.id
assert len(loaded_calls) == 1
assert loaded_calls[0].tool_call_id == "call_1"
assert loaded_calls[0].arguments_json == {"path": "guide.txt"}
assert loaded_calls[0].status == "success"
assert loaded_calls[0].result_json["success"] is True
assert loaded_calls[0].started_at is not None
assert loaded_calls[0].ended_at is not None
assert loaded_calls[0].latency_ms is not None
```

- [x] **Step 2: Run RED for persistence**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -q
```

Expected: no ToolCall ORM row exists yet or terminal fields are missing.

- [x] **Step 3: Persist every attempted Tool Call**

Before lookup/validation, create and flush the row:

```python
row = ToolCall(
    agent_run=agent_run,
    conversation_id=agent_run.conversation_id,
    tool_call_id=call.tool_call_id,
    tool_name=call.tool_name,
    arguments_json=deepcopy(call.arguments),
    status="running",
    started_at=utc_now(),
)
self._session.add(row)
self._session.flush()
started = perf_counter()
result = await self._execute_tool(call)
payload = result.model_dump(mode="json")
row.result_json = payload
row.status = "success" if result.success else "failed"
row.error_message = None if result.success else result.error
row.ended_at = utc_now()
row.latency_ms = _elapsed_ms(started)
self._session.flush()
```

Return both ORM row and ToolResult so the service result and observations preserve runtime order independent of relationship query order.

- [x] **Step 4: Run GREEN for successful persistence**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -q
```

Expected: commit/reload test passes.

- [x] **Step 5: Add failed-call persistence tests**

Commit successful Agent runs containing unknown/invalid/raising Tool calls and assert each row is `failed`, has full safe `result_json`, has only safe `error_message`, and still belongs to the completed AgentRun. Also assert no migration files changed and direct-answer runs persist zero ToolCalls.

- [x] **Step 6: Run failed-call persistence coverage**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -q
```

Measured result: the new commit/reload failure-row test passed immediately because the already RED-driven safe-failure normalization and generic ToolCall terminal mapping covered the same path. No additional production change was needed and no extra RED is claimed.

- [x] **Step 7: Run focused Agent/Provider/ORM regression**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py tests/test_agent_models.py tests/test_agent_migrations.py tests/test_llm_provider_base.py tests/test_openai_compatible_provider.py tests/test_chat_service.py tests/test_chat_api.py -q
```

Expected: all selected tests pass with only the already accepted Starlette TestClient/httpx deprecation warning where applicable.

---

### Task 5: Documentation, Full Verification, and Codex Self-Review

**Files:**
- Modify: `docs/03-llm-provider.md`
- Modify: `docs/10-tool-calling-design.md`
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`
- Modify if current-stage text is stale: `README.md`
- Modify if current-stage text is stale: `README_CN.md`
- Modify if current-stage text is stale: `docs/00-project-overview.md`
- Modify if current-stage text is stale: `docs/01-architecture.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: measured RED/GREEN and verification evidence from Tasks 1～4.
- Produces: truthful S4～S6 status and next-batch handoff to `P2-M3-S7～S8`.

- [x] **Step 1: Run focused complete feature verification**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py tests/test_llm_provider_base.py tests/test_openai_compatible_provider.py tests/test_llm_tool_adapter.py tests/test_tool_registry.py tests/test_tool_validation.py tests/test_tool_read_file.py tests/test_tool_list_dir.py tests/test_agent_models.py tests/test_agent_migrations.py tests/test_chat_service.py tests/test_chat_api.py -q
```

Expected: all pass without real Provider/network access.

- [x] **Step 2: Run complete backend verification**

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Expected: full pytest passes with only the accepted Starlette TestClient/httpx deprecation warning; pip reports no broken requirements.

- [x] **Step 3: Run frontend regression verification**

From `frontend`:

```powershell
npm run typecheck
npm test -- --run
npm run build
```

Expected: typecheck, all Vitest files/tests, and production build pass. This batch adds no frontend code.

- [x] **Step 4: Run no-Provider FastAPI smoke**

Use a temporary in-memory/disposable SQLite configuration and TestClient to verify `/api/v1/health`, `/openapi.json`, and server-generated `X-Request-ID`. Do not initialize or call a real Provider.

- [x] **Step 5: Update documentation with actual evidence**

Document exactly:

- Provider-neutral assistant Tool Call and Tool observation messages;
- one Tool round, multiple calls executed sequentially, exactly two Provider calls maximum;
- AgentRun/ToolCall persistence and safe failure observations;
- no API/UI, no streaming Tool Calls, no strict persisted parallel-call order, no LLMCall linkage/usage aggregation;
- S7 owns general max steps, Tool timeouts, retries, and comprehensive failure returns;
- actual focused/full test counts and smoke outputs;
- next batch is `P2-M3-S7～S8`, not M4.

Do not create `docs/11-simple-agent-loop.md`; the execution table assigns that formal M3 review document to S8.

- [x] **Step 6: Run documentation and boundary checks**

Run:

```powershell
git diff --check
git status --short
git diff --name-only
```

Additionally scan changed/committed-scope files for credential patterns, local Markdown links, tracked generated artifacts, migration changes, executable `web_fetch`, API/frontend additions, and later-Plan directories. Expected: no suspected secrets, no missing links, no migration, no `web_fetch` runtime, no API/UI/later-Plan implementation.

- [x] **Step 7: Codex self-review and repair loop**

Review the full diff for:

1. exact `P2-M3-S4～S6` scope;
2. Provider-neutral business layer and exact wire serialization boundary;
3. ordinary Chat/Streaming compatibility;
4. single-round boundedness and multiple-call ordering;
5. safe Tool validation/execution failures without raw exception leakage;
6. AgentRun/ToolCall terminal field consistency and transaction truthfulness;
7. no DB/schema/status/Plan-boundary drift;
8. documentation facts matching measured verification.

Classify every finding as must fix, later Step, limitation, or not applicable. Every must-fix behavior receives a failing regression test before repair, followed by affected focused and full verification.

- [x] **Step 8: Prepare manual commit handoff**

Do not stage or commit. Suggested batch commit message:

```text
feat(agent): add simple tool calling loop
```
