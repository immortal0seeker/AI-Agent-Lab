# Plan 1 M2 LLM Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `P1-M2-S4` through `P1-M2-S6` with a typed LLM Provider contract, a mock-tested OpenAI-compatible adapter, and environment-backed initialization.

**Architecture:** Vendor-neutral Pydantic contracts and an abstract provider interface sit above an `httpx` OpenAI-compatible adapter. Application settings are translated by a small factory, while future Chat services depend only on `BaseLLMProvider`.

**Tech Stack:** Python 3.11, Pydantic 2, pydantic-settings 2, httpx 0.28, pytest 9.

## Global Constraints

- Work only on `P1-M2-S4` through `P1-M2-S6`.
- Do not add Model Registry, Chat API, persistence services, frontend Chat, Tool Calling, RAG, Memory, MCP, Voice, Vision, or Desktop behavior.
- Use mock HTTP only; do not read a real `.env` or invoke a paid API.
- Never expose an API key in exceptions, logs, docs, fixtures, or assertions.
- Keep `httpx` as the only runtime HTTP dependency.
- Defer detailed Provider error classification and retry policy to `P1-M4-S2`.
- The user creates the Git commit manually; implementation checkpoints must not run `git commit`.

---

### Task 1: Vendor-Neutral Provider Contract

**Files:**
- Create: `backend/app/providers/__init__.py`
- Create: `backend/app/providers/llm/__init__.py`
- Create: `backend/app/providers/llm/base.py`
- Create: `backend/tests/test_llm_provider_base.py`

**Interfaces:**
- Produces: `ChatMessage`, `ChatRequest`, `TokenUsage`, `LLMResponse`, `ChatChunk`, `LLMProviderError`, `ProviderConfigurationError`, `ProviderRequestError`, `ProviderResponseError`, and `BaseLLMProvider`.

- [ ] **Step 1: Write failing contract tests**

Define a test-only `MockLLMProvider` that returns an `LLMResponse`, yields a `ChatChunk`, and proves invalid temperature/max-token values are rejected.

- [ ] **Step 2: Verify RED**

Run from `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_provider_base.py -q
```

Expected: collection fails because `app.providers.llm.base` does not exist.

- [ ] **Step 3: Implement the minimal contract**

Use Pydantic models with `Literal["system", "user", "assistant"]`, `temperature` constrained to `0..2`, and positive optional `max_tokens`. Define `BaseLLMProvider` with abstract `chat()` and `stream_chat()` methods.

- [ ] **Step 4: Verify GREEN**

Run the focused test and expect all contract tests to pass.

---

### Task 2: OpenAI-Compatible HTTP Adapter

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `requirements.txt`
- Create: `backend/app/providers/llm/openai_compatible.py`
- Create: `backend/tests/test_openai_compatible_provider.py`

**Interfaces:**
- Consumes: all Task 1 contracts.
- Produces: `OpenAICompatibleProvider(base_url, api_key, default_model, timeout_seconds=30.0, client=None)`.

- [ ] **Step 1: Write failing non-streaming tests**

Use `httpx.MockTransport` to assert the URL, bearer header, model/messages/temperature/max-token payload, and normalized `LLMResponse` including token usage.

- [ ] **Step 2: Verify RED**

Run the focused test and expect import failure for `openai_compatible`.

- [ ] **Step 3: Implement non-streaming chat**

Post to the normalized `/chat/completions` endpoint, parse `choices[0]`, normalize usage, and translate transport, HTTP, and response-shape failures to Provider errors.

- [ ] **Step 4: Verify non-streaming GREEN**

Run the focused non-streaming tests and expect them to pass.

- [ ] **Step 5: Write failing streaming tests**

Return mock `text/event-stream` data containing content deltas, a finish reason, optional usage, and `[DONE]`; assert the yielded `ChatChunk` sequence.

- [ ] **Step 6: Verify streaming RED**

Run the streaming test and expect the unimplemented abstract stream path to fail.

- [ ] **Step 7: Implement SSE parsing**

Send `stream=true`, iterate response lines, ignore empty/non-data lines, stop at `[DONE]`, parse chunk fields, and translate malformed JSON or shapes.

- [ ] **Step 8: Verify adapter GREEN**

Run all adapter tests and then the complete backend test suite.

---

### Task 3: Settings, Provider Factory, And Batch Documentation

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Create: `backend/app/providers/llm/factory.py`
- Create: `backend/tests/test_llm_provider_factory.py`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`

**Interfaces:**
- Consumes: `Settings` and `OpenAICompatibleProvider`.
- Produces: `create_openai_compatible_provider(settings, client=None) -> OpenAICompatibleProvider`.

- [ ] **Step 1: Write failing settings/factory tests**

Assert explicit environment aliases are read, a blank or absent key raises `ProviderConfigurationError` with `OPENAI_COMPATIBLE_API_KEY` in the message, and a configured provider can complete a mock request without exposing the key.

- [ ] **Step 2: Verify RED**

Run the focused test and expect missing settings/factory imports or attributes.

- [ ] **Step 3: Implement settings and factory**

Store the key as `SecretStr | None`, validate it only when provider creation is requested, unwrap it at the adapter boundary, and pass base URL/model/timeout to the adapter.

- [ ] **Step 4: Verify GREEN**

Run the factory tests and complete backend suite.

- [ ] **Step 5: Synchronize operational docs**

Document only mock-verified Provider behavior, mark Batch 5 complete, set the next scope to `P1-M2-S7` through `P1-M2-S8`, and include safe placeholder environment values.

- [ ] **Step 6: Run final verification and review**

Run backend pytest, frontend typecheck/test/build, backend and frontend startup smoke checks, `git diff --check`, `git status --short`, secret scans, and a scope-focused Codex self-review.
