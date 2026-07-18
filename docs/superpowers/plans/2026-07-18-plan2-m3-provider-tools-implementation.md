# Plan 2 M3 Provider Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Repository rules prohibit sub-agents for this batch.

**Goal:** Complete `P2-M3-S1～S3` with a typed non-streaming Provider Tool Calling contract, an isolated Tool Registry adapter, and safe OpenAI-compatible request/response mapping.

**Architecture:** Provider DTOs live in `app.providers.llm.base`; `tool_adapter.py` is the only Tool Registry-to-Provider conversion boundary; `OpenAICompatibleProvider` owns wire serialization and raw arguments parsing. Text Chat and text Streaming remain backward compatible, while streaming requests with tools fail locally before HTTP.

**Tech Stack:** Python 3.11, Pydantic v2, FastAPI, httpx MockTransport, pytest, existing JSON Schema/Tool Registry.

## Global Constraints

- Work only on `P2-M3-S1～S3`; do not implement Agent Loop, Tool execution, persistence service, Agent API, frontend Tool UI, RAG, Memory, MCP, Shell Tool, or file-writing tools.
- Do not call a real Provider, paid API, or network Tool; all HTTP evidence uses `httpx.MockTransport`.
- Keep `backend/app/providers/llm/models.json` example entry at `supports_tools=false` because no real model capability is verified.
- Support only non-streaming Tool Calling in this batch; `stream_chat()` with tools must fail before network I/O.
- Preserve ordinary Chat and Streaming payloads, persistence, error classification, and API behavior.
- Tool names are at most 64 ASCII letters, digits, underscores, or hyphens; raw Tool arguments and upstream bodies never enter errors or logs.
- The user creates commits manually; do not stage, commit, push, tag, switch branches, or create worktrees.

---

### Task 1: Typed Provider Tool Contract

**Files:**
- Modify: `backend/app/providers/llm/base.py`
- Modify: `backend/app/providers/llm/__init__.py`
- Test: `backend/tests/test_llm_provider_base.py`

**Interfaces:**
- Produces: `LLMFunctionDefinition`, `LLMToolDefinition`, `LLMToolCall`, `ProviderUnsupportedFeatureError`.
- Produces: `ChatRequest.tools: tuple[LLMToolDefinition, ...]` and `LLMResponse.tool_calls: tuple[LLMToolCall, ...]`.
- Consumed by: Tasks 2 and 3.

- [x] **Step 1: Write failing contract tests**

Add tests that construct a function definition, pass it through `ChatRequest`, return a content-less Tool Call response from a Mock Provider, and reject an `LLMResponse` with neither text nor Tool Calls:

```python
def build_tool_definition() -> LLMToolDefinition:
    return LLMToolDefinition(
        function=LLMFunctionDefinition(
            name="read_file",
            description="Read a workspace text file",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        )
    )


def test_provider_contract_accepts_tools_and_returns_tool_calls() -> None:
    request = ChatRequest(
        messages=[ChatMessage(role="user", content="read README")],
        tools=(build_tool_definition(),),
    )
    response = LLMResponse(
        model="mock-model",
        content=None,
        finish_reason="tool_calls",
        tool_calls=(
            LLMToolCall(
                tool_call_id="call_1",
                tool_name="read_file",
                arguments={"path": "README.md"},
            ),
        ),
    )

    assert request.tools[0].function.name == "read_file"
    assert response.content is None
    assert response.tool_calls[0].arguments == {"path": "README.md"}


def test_llm_response_requires_content_or_tool_calls() -> None:
    with pytest.raises(ValidationError, match="content or tool calls"):
        LLMResponse(model="mock-model", content=None)
```

Also cover invalid function names, non-object/non-serializable parameters, duplicate response Tool Call IDs, defensive parameter/argument copies, and the default empty tools tuple.

- [x] **Step 2: Run RED**

Run from `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_provider_base.py -q
```

Expected: collection/import failure because the new DTOs do not exist.

- [x] **Step 3: Implement the minimal contract**

Add constrained names and Pydantic DTOs to `base.py`:

```python
LLMToolName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
]


class LLMFunctionDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: LLMToolName
    description: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
    ]
    parameters: dict[str, Any]

    @field_validator("parameters")
    @classmethod
    def validate_parameters(cls, value: dict[str, Any]) -> dict[str, Any]:
        copied = deepcopy(value)
        if copied.get("type") != "object":
            raise ValueError("tool parameters root must be an object")
        try:
            json.dumps(copied, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("tool parameters must be JSON serializable") from exc
        return copied


class LLMToolDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["function"] = "function"
    function: LLMFunctionDefinition


class LLMToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_call_id: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
    ]
    tool_name: LLMToolName
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator("arguments")
    @classmethod
    def copy_arguments(cls, value: dict[str, Any]) -> dict[str, Any]:
        return deepcopy(value)
```

Extend the request/response and add the invariant:

```python
class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    model: str | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    tools: tuple[LLMToolDefinition, ...] = ()


class LLMResponse(BaseModel):
    id: str | None = None
    model: str
    content: str | None = None
    finish_reason: str | None = None
    usage: TokenUsage | None = None
    tool_calls: tuple[LLMToolCall, ...] = ()

    @model_validator(mode="after")
    def validate_output(self) -> Self:
        if self.content is None and not self.tool_calls:
            raise ValueError("response requires content or tool calls")
        ids = [call.tool_call_id for call in self.tool_calls]
        if len(ids) != len(set(ids)):
            raise ValueError("tool call ids must be unique")
        return self


class ProviderUnsupportedFeatureError(LLMProviderError):
    """Provider adapter 尚未支持请求的本地能力。"""
```

Export the four new symbols from `app.providers.llm.__init__`.

- [x] **Step 4: Run GREEN and provider contract regression**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_provider_base.py tests/test_chat_service.py tests/test_chat_api.py -q
```

Expected: all selected tests pass; ordinary Mock Providers remain source-compatible.

- [x] **Step 5: Record checkpoint**

Do not commit. Record suggested message: `feat(provider): add typed tool calling contracts`.

---

### Task 2: Tool Registry to LLM Schema Adapter

**Files:**
- Create: `backend/app/providers/llm/tool_adapter.py`
- Modify: `backend/app/providers/llm/__init__.py`
- Create: `backend/tests/test_llm_tool_adapter.py`

**Interfaces:**
- Consumes: `ToolRegistry`, immutable Tool metadata, `LLMFunctionDefinition`, `LLMToolDefinition`.
- Produces: `build_llm_tool_definitions(registry: ToolRegistry) -> tuple[LLMToolDefinition, ...]`.
- Consumed by: future Agent service; Task 3 tests use its definitions.

- [x] **Step 1: Write failing adapter tests**

```python
def test_adapter_builds_serializable_builtin_definitions(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry, workspace_root=tmp_path)

    definitions = build_llm_tool_definitions(registry)
    payload = [definition.model_dump(mode="json") for definition in definitions]

    assert [definition.function.name for definition in definitions] == [
        "read_file",
        "list_dir",
    ]
    assert [item["type"] for item in payload] == ["function", "function"]
    assert json.loads(json.dumps(payload)) == payload


def test_adapter_returns_empty_tuple_for_empty_registry() -> None:
    assert build_llm_tool_definitions(ToolRegistry()) == ()
```

Add a defensive-copy test that mutates `model_dump()` output and verifies a second adapter call and the Registry schema remain unchanged. Add a non-Registry type rejection test.

- [x] **Step 2: Run RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_tool_adapter.py -q
```

Expected: collection/import failure because `tool_adapter.py` does not exist.

- [x] **Step 3: Implement the adapter**

```python
from app.providers.llm.base import LLMFunctionDefinition, LLMToolDefinition
from app.tools.registry import ToolRegistry


def build_llm_tool_definitions(
    registry: ToolRegistry,
) -> tuple[LLMToolDefinition, ...]:
    if not isinstance(registry, ToolRegistry):
        raise TypeError("registry must be a ToolRegistry")
    return tuple(
        LLMToolDefinition(
            function=LLMFunctionDefinition(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters_schema,
            )
        )
        for tool in registry.list_tools()
    )
```

Export `build_llm_tool_definitions` from the LLM package.

- [x] **Step 4: Run GREEN and Tool regression**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_tool_adapter.py tests/test_tool_registry.py tests/test_tool_read_file.py tests/test_tool_list_dir.py -q
```

Expected: all selected tests pass; no file is read by adapter tests.

- [x] **Step 5: Record checkpoint**

Do not commit. Record suggested message: `feat(provider): adapt tool registry schemas`.

---

### Task 3: OpenAI-Compatible Non-Streaming Tool Mapping

**Files:**
- Modify: `backend/app/providers/llm/openai_compatible.py`
- Test: `backend/tests/test_openai_compatible_provider.py`

**Interfaces:**
- Consumes: `ChatRequest.tools`, `LLMToolDefinition`, `LLMToolCall`.
- Produces: exact Chat Completions `tools` payload and normalized Tool Call responses.

- [x] **Step 1: Write failing happy-path HTTP tests**

Add local test helpers, then one test that sends a definition and returns a content-less Tool Call:

```python
def build_provider(client: httpx.AsyncClient) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url="https://provider.example/v1",
        api_key="test-secret-key",
        default_model="tool-model",
        client=client,
    )


def build_tool_definition() -> LLMToolDefinition:
    return LLMToolDefinition(
        function=LLMFunctionDefinition(
            name="read_file",
            description="Read a workspace text file",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        )
    )


def test_chat_sends_tools_and_parses_tool_call() -> None:
    async def exercise() -> tuple[dict[str, object], LLMResponse]:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(
                200,
                json={
                    "id": "chatcmpl-tools",
                    "model": "tool-model",
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": "read_file",
                                            "arguments": '{"path":"README.md"}',
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = build_provider(client)
            response = await provider.chat(
                ChatRequest(
                    messages=[ChatMessage(role="user", content="read README")],
                    tools=(build_tool_definition(),),
                )
            )
        return captured, response

    payload, response = asyncio.run(exercise())

    assert payload["tools"] == [build_tool_definition().model_dump(mode="json")]
    assert response.content is None
    assert response.tool_calls[0].arguments == {"path": "README.md"}
```

Add a multiple-Tool-Call case that verifies order, finish reason, and usage. Keep the existing ordinary request assertion unchanged to prove `tools` is omitted when empty.

- [x] **Step 2: Run RED for happy path**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_openai_compatible_provider.py -q
```

Expected: new payload/response assertions fail because tools are not serialized or parsed.

- [x] **Step 3: Implement request serialization and response parsing**

Extend `_build_payload()`:

```python
if request.tools:
    payload["tools"] = [
        tool.model_dump(mode="json") for tool in request.tools
    ]
```

Pass `tools_requested=bool(request.tools)` from `chat()` and implement a helper with fixed failure semantics:

```python
@staticmethod
def _parse_tool_calls(payload: Any) -> tuple[LLMToolCall, ...]:
    if not isinstance(payload, list) or not payload:
        raise TypeError("tool_calls must be a non-empty array")
    calls: list[LLMToolCall] = []
    for item in payload:
        if not isinstance(item, dict) or item.get("type") != "function":
            raise TypeError("tool call type must be function")
        function = item["function"]
        if not isinstance(function, dict):
            raise TypeError("function must be an object")
        raw_arguments = function["arguments"]
        if not isinstance(raw_arguments, str):
            raise TypeError("arguments must be a string")
        arguments = json.loads(raw_arguments)
        if not isinstance(arguments, dict):
            raise TypeError("arguments root must be an object")
        calls.append(
            LLMToolCall(
                tool_call_id=item["id"],
                tool_name=function["name"],
                arguments=arguments,
            )
        )
    return tuple(calls)
```

Update `_parse_response(payload, *, tools_requested: bool)` so it validates optional string content, rejects Tool Calls when tools were not requested, constructs `LLMResponse`, and converts `KeyError`, `IndexError`, `TypeError`, `ValueError`, JSON decoding, and Pydantic validation into the existing fixed `ProviderResponseError("Provider response format is invalid")`.

- [x] **Step 4: Run GREEN for happy path**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_openai_compatible_provider.py -q
```

Expected: happy paths and existing Provider tests pass.

- [x] **Step 5: Write failing malformed-response tests**

Use parametrized MockTransport responses for:

```python
[
    [],
    [{"id": "call_1", "type": "custom", "function": {}}],
    [{"id": "call_1", "type": "function", "function": {"name": "read_file", "arguments": "{"}}],
    [{"id": "call_1", "type": "function", "function": {"name": "read_file", "arguments": "[]"}}],
]
```

Also add duplicate IDs, blank/invalid names, raw arguments containing a synthetic secret, and Tool Calls returned to a request without tools. Assert `ProviderResponseError` and assert the raw argument/secret never appears in the exception string.

- [x] **Step 6: Run RED then make malformed responses GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_openai_compatible_provider.py -q
```

Expected RED: at least one new malformed case is accepted or leaks an unexpected validation exception. Implement only the missing fixed-error wrapping or invariant, then rerun until all pass.

- [x] **Step 7: Record checkpoint**

Do not commit. Record suggested message: `feat(provider): map openai compatible tool calls`.

---

### Task 4: Streaming Guard and Plan 1 Compatibility

**Files:**
- Modify: `backend/app/providers/llm/openai_compatible.py`
- Modify: `backend/app/services/chat_service.py`
- Test: `backend/tests/test_openai_compatible_provider.py`
- Test: `backend/tests/test_chat_service.py`

**Interfaces:**
- Consumes: `ProviderUnsupportedFeatureError` and optional `LLMResponse.content`.
- Produces: fail-closed streaming Tool behavior and explicit text-only ChatService guard.

- [x] **Step 1: Write failing streaming no-I/O test**

```python
def test_stream_chat_rejects_tools_before_http() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(500)

    async def exercise() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = build_provider(client)
            async for _ in provider.stream_chat(
                ChatRequest(
                    messages=[ChatMessage(role="user", content="read README")],
                    tools=(build_tool_definition(),),
                )
            ):
                pass

    with pytest.raises(ProviderUnsupportedFeatureError, match="streaming tool calls"):
        asyncio.run(exercise())
    assert called is False
```

- [x] **Step 2: Run RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_openai_compatible_provider.py::test_stream_chat_rejects_tools_before_http -q
```

Expected: request reaches MockTransport or no unsupported-feature error is raised.

- [x] **Step 3: Implement the local streaming guard**

At the beginning of `stream_chat()`:

```python
if request.tools:
    raise ProviderUnsupportedFeatureError(
        "Provider streaming tool calls are not supported"
    )
```

- [x] **Step 4: Protect the Plan 1 text Chat service**

Add a failing service test where a Mock Provider returns `content=None` plus a Tool Call to a normal text Chat request. Expect a fixed `ProviderResponseError` and transaction rollback. Then add this check inside the existing provider-call `try` block:

```python
response = await provider.chat(provider_request)
if response.content is None:
    raise ProviderResponseError("Provider response did not contain text")
```

This does not execute tools and only preserves the existing text Chat contract.

- [x] **Step 5: Run selected compatibility tests**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_openai_compatible_provider.py tests/test_chat_service.py tests/test_chat_api.py -q
```

Expected: all pass; existing ordinary streaming tests still parse text chunks and `[DONE]`.

- [x] **Step 6: Record checkpoint**

Do not commit. Record suggested message: `fix(chat): reject tool-only responses on text path`.

---

### Task 5: Documentation, Full Verification, and Self-Review

**Files:**
- Modify: `docs/03-llm-provider.md`
- Modify: `docs/10-tool-calling-design.md`
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`
- Review and conditionally modify only if stale: `README.md`, `README_CN.md`, `docs/00-project-overview.md`, `docs/01-architecture.md`

**Interfaces:**
- Consumes: actual code/test outputs from Tasks 1～4.
- Produces: truthful current-scope documentation and Batch 7 acceptance evidence.

- [x] **Step 1: Run focused Provider and Tool tests**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_provider_base.py tests/test_llm_tool_adapter.py tests/test_openai_compatible_provider.py tests/test_tool_registry.py tests/test_tool_read_file.py tests/test_tool_list_dir.py tests/test_chat_service.py tests/test_chat_api.py -q
```

Expected: all pass with no real network or Provider.

- [x] **Step 2: Run complete backend verification**

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Expected: complete pytest pass with only the already accepted Starlette TestClient/httpx deprecation warning; pip reports no broken requirements.

- [x] **Step 3: Run frontend regression verification**

```powershell
npm run typecheck
npm test -- --run
npm run build
```

Run from `frontend`. Expected: typecheck, complete Vitest, and production build pass. Use the already approved build permission only if the managed sandbox blocks `dist` writes.

- [x] **Step 4: Run no-Provider application smoke**

Use the existing FastAPI TestClient fixture or a temporary port to verify `/api/v1/health`, `/openapi.json`, and `X-Request-ID`; do not initialize a real Provider or read a local `.env`.

- [x] **Step 5: Update docs with measured evidence**

Document exactly:

- typed non-streaming tools request and Tool Call response support;
- Registry adapter and defensive copies;
- malformed arguments fixed-error behavior;
- streaming Tool Calls explicitly unsupported in this batch;
- example model remains `supports_tools=false`;
- Agent Loop, Tool execution, persistence service, API, and frontend remain pending;
- actual focused/full test counts from Steps 1～4.

- [x] **Step 6: Run documentation and repository checks**

```powershell
git diff --check
git status --short
```

Additionally scan committed-scope Markdown local links, common credential patterns in the diff, tracked/generated Python artifacts, `web_fetch` executable surface, database migrations, and later-Plan directories. Expected: zero missing links, zero suspected real secrets, no tracked generated artifacts, no new migration, no Agent Loop/API/frontend/later-Plan implementation.

- [x] **Step 7: Codex self-review and repair loop**

Review the full diff for:

1. `P2-M3-S1～S3` scope only;
2. Provider/Tool dependency direction;
3. content/tool_calls invariants and multiple-call ordering;
4. safe JSON parsing and non-leaking failures;
5. ordinary Chat/Streaming regression;
6. documentation truthfulness and `models.json` capability accuracy.

Classify findings as must fix, later Step, limitation, or not applicable. Apply every must-fix item through a new failing regression test, then rerun the affected focused suite and all required full verification.

- [x] **Step 8: Prepare manual commit handoff**

Do not stage or commit. Suggested batch commit message:

```text
feat(provider): add non-streaming tool calling support
```
