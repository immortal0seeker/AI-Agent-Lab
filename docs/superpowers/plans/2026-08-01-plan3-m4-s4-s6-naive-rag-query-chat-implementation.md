# Plan 3 M4 S4～S6 Naive RAG Query / Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Repository policy forbids subagents for this batch and reserves all Git writes for the user.

**Goal:** Add an independently testable RAG Prompt Builder, a retrieval-only Query API, and a persisted non-streaming RAG Chat API over the existing Retriever and conversation/provider contracts.

**Architecture:** `RagPromptBuilder` is pure and owns source formatting plus context budgeting. `RagQueryService` owns Knowledge Base validation and retrieval without any LLM dependency; `RagService` inherits it and adds conversation orchestration across Prompt, Provider, Message, and LLMCall. Thin FastAPI routes expose `/api/v1/rag/query` and `/api/v1/rag/chat`; `rag_queries` writes and Agent Tool integration remain deferred.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, existing LLM/Embedding Provider abstractions, Qdrant VectorStore, pytest.

## Global Constraints

- Implement only `P3-M4-S4～S6`; do not implement S7/S8, M5, Plan 4+, streaming RAG, frontend RAG, rerank, evaluation, memory, OCR, or multimodal behavior.
- Do not read real `.env`, credentials, paid providers, network Tools, or `backend/ai_agent_lab.db`.
- Tests use complete Mock Providers, system temporary SQLite/workspaces, and temporary local Qdrant collections.
- Keep routes thin and place business logic in `RagService`.
- Do not create/switch branches or worktrees and do not stage, commit, push, or tag.
- Required comments are Chinese and explain only non-obvious boundaries.

---

## File Map

- Create `backend/app/rag/rag_prompt.py`: pure Prompt/source-budget boundary.
- Modify `backend/app/schemas/rag.py`: request, metadata, source, and response contracts.
- Modify `backend/app/schemas/__init__.py`: export public RAG schemas.
- Create `backend/app/services/rag_service.py`: query/chat orchestration and result dataclasses.
- Modify `backend/app/services/__init__.py`: export service contract only if consistent with existing package style.
- Modify `backend/app/api/dependencies.py`: separately construct LLM-free RagQueryService and full Prompt/Provider RagService.
- Create `backend/app/api/v1/rag.py`: two thin endpoints and response mapping.
- Modify `backend/app/api/errors.py`: safe Retriever response mapping.
- Modify `backend/app/main.py`: register RAG router.
- Modify `backend/app/core/config.py` and `.env.example`: bounded context configuration.
- Create `backend/tests/test_rag_prompt.py`, `test_rag_schemas.py`, `test_rag_service.py`, and `test_rag_api.py`.
- Create `docs/23-naive-rag.md`; update current README/docs/CHANGELOG/Plan table.

---

### Task 1: RAG Prompt Builder RED/GREEN

**Files:**
- Create: `backend/tests/test_rag_prompt.py`
- Create: `backend/app/rag/rag_prompt.py`

**Interfaces:**
- Consumes: `tuple[RetrievalResult, ...]`, optional `tuple[ChatMessage, ...]`.
- Produces: `RagPrompt(messages, sources, context_characters)` and `RagPromptBuilder.build()`.

- [x] **Step 1: Write the missing-module RED**

Create a test importing `RagPromptBuilder`, build two complete RetrievalResult values, and assert:

```python
prompt = RagPromptBuilder(max_context_characters=2_000).build(
    query="What is the architecture?",
    retrieval_results=(first, second),
)
assert [message.role for message in prompt.messages] == ["system", "user"]
assert "[1] 文件：guide.md" in prompt.messages[-1].content
assert "[2] 文件：manual.pdf，第 3 页" in prompt.messages[-1].content
assert [source.source_index for source in prompt.sources] == [1, 2]
```

- [x] **Step 2: Run RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_rag_prompt.py -q
```

Expected: collection fails because `app.rag.rag_prompt` does not exist.

- [x] **Step 3: Implement minimal formatting GREEN**

Add immutable `RagPrompt`, fixed system instruction, source formatting, history placement, and 1-based source mapping. Require actual RetrievalResult/ChatMessage values and user/assistant-only history.

- [x] **Step 4: Add budget/error RED**

Add tests for a source truncated inside the exact context budget, omission of later sources, zero results, blank query, invalid result tuple/history, bool/too-small context limit, and nested source metadata isolation.

- [x] **Step 5: Implement budget/error GREEN**

Validate constructor limit in 128～1,000,000. Add source blocks in retrieval order; truncate only the final included content with `…`; ensure `len(context_text) <= max_context_characters` and `sources` includes only injected blocks.

- [x] **Step 6: Run GREEN/refactor**

Run the prompt tests and adjacent RetrievalResult tests. Expected: all pass with no network/database calls.

---

### Task 2: RAG API Schema And Settings RED/GREEN

**Files:**
- Create: `backend/tests/test_rag_schemas.py`
- Modify: `backend/tests/test_config.py`
- Modify: `backend/app/schemas/rag.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/core/config.py`
- Modify: `.env.example`

**Interfaces:**
- Produces: `RagRetrievalRequest`, `RagChatRequest`, `RagRetrievalMetadata`, `RagAnswerMetadata`, `RagSource`, `RagQueryResponse`, `RagChatResponse` and `Settings.rag_max_context_characters`.

- [x] **Step 1: Write schema/config RED**

Assert valid default `top_k == 5`, optional threshold, required Chat identifiers, canonical JSON UUIDs, exact source indices, response shapes, and default context budget 12,000. Parameterize blank query/identifiers, bool or out-of-range Top-K, bool/string/NaN/infinite threshold, invalid temperature/max_tokens, extra fields, and context values outside 128～1,000,000.

- [x] **Step 2: Run RED**

Run schema/config tests. Expected: imports/setting fail because new contracts do not exist.

- [x] **Step 3: Implement minimal GREEN**

Use frozen `extra="forbid"` Pydantic models, StrictInt, FiniteFloat, pre-validators rejecting bool/string numeric coercion, and nonblank bounded identifiers/query. Add `RAG_MAX_CONTEXT_CHARACTERS=12000` to `.env.example` without any credential value.

- [x] **Step 4: Run GREEN**

Run schema, RetrievalResult, knowledge schema, and config tests. Expected: all pass.

---

### Task 3: Retrieval-Only RagService RED/GREEN

**Files:**
- Create: `backend/tests/test_rag_service.py`
- Create: `backend/app/services/rag_service.py`

**Interfaces:**
- Consumes: Session, Retriever, RagPromptBuilder, ModelRegistry, Mapping[str, BaseLLMProvider].
- Produces: `RagQueryService.query()` and immutable `RagQueryResult`; `RagService` inherits the same retrieval behavior.

- [x] **Step 1: Write query service RED**

With temporary SQLite, a real KnowledgeBase row, a complete recording EmbeddingProvider/VectorStore, and a Provider that fails if called, assert `query()` returns ordered RetrievalResults plus `naive_vector` metadata and creates no Message, LLMCall, or RagQuery rows.

- [x] **Step 2: Add missing-KB/error RED**

Assert missing Knowledge Base raises existing KnowledgeBaseNotFoundError before embedding, and Retriever Provider/VectorStore exceptions preserve their identity without database writes.

- [x] **Step 3: Run RED**

Run the service test. Expected: collection fails because `app.services.rag_service` does not exist.

- [x] **Step 4: Implement query GREEN**

Add `RagQueryService._get_knowledge_base()` and call Retriever exactly once with request query/KB/Top-K/threshold. Build typed metadata from the request and result count; do not resolve/call LLM or Prompt Builder and do not write any row.

- [x] **Step 5: Run GREEN**

Run service + Retriever tests. Expected: all pass.

---

### Task 4: Persisted RAG Chat Service RED/GREEN

**Files:**
- Modify: `backend/tests/test_rag_service.py`
- Modify: `backend/app/services/rag_service.py`

**Interfaces:**
- Produces: `RagService.chat()` and immutable `RagChatResult`.

- [x] **Step 1: Write happy-path RED**

Create an existing conversation with one prior user/assistant turn and a Knowledge Base. Assert Chat:

```python
result = asyncio.run(service.chat(request))
assert result.answer == "Grounded answer [1]"
assert [source.source_index for source in result.sources] == [1]
assert provider.requests[0].messages[0].role == "system"
assert [m.content for m in provider.requests[0].messages[1:3]] == [
    "Earlier question", "Earlier answer",
]
```

Also assert persisted Message roles are user/assistant/user/assistant, the raw query (not expanded Prompt) is stored, one LLMCall points to the new assistant, conversation metadata advances, and RagQuery count stays zero.

- [x] **Step 2: Add zero-hit and bounded-source RED**

Assert zero hits still call LLM with the no-source marker and return empty sources. Configure a small legal budget and assert response sources exactly match what the model saw while metadata distinguishes retrieved and injected counts.

- [x] **Step 3: Add rollback/selection RED**

Assert unknown model/provider and missing KB/conversation fail before writes. Assert Retriever failure, Provider failure, invalid Provider result type, tool-only response, and blank response roll back the new user Message and LLMCall while preserving previously committed history.

- [x] **Step 4: Implement minimal Chat GREEN**

Resolve model/provider and existing KB/conversation first; append the raw user query; retrieve; convert prior persisted messages to user/assistant ChatMessage history; build Prompt; call provider once; require an actual LLMResponse with nonblank content; calculate existing LLMCall metrics; append assistant, create/flush LLMCall, update conversation, and return typed result. Roll back on all exceptions.

- [x] **Step 5: Run GREEN/refactor**

Run RagService, Prompt, ChatService, ConversationService, model and LLM usage tests. Expected: all pass.

---

### Task 5: RAG Dependencies, Error Mapping, And Routes RED/GREEN

**Files:**
- Create: `backend/tests/test_rag_api.py`
- Modify: `backend/app/api/dependencies.py`
- Modify: `backend/app/api/errors.py`
- Create: `backend/app/api/v1/rag.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `get_retriever()`, `get_rag_query_service()`, `get_rag_prompt_builder()`, `get_rag_service()`, POST `/api/v1/rag/query`, POST `/api/v1/rag/chat`.

- [x] **Step 1: Write OpenAPI/query endpoint RED**

Build TestClient with temporary Session and complete dependency overrides. Assert OpenAPI exposes both endpoints; `/rag/query` returns the exact results/metadata schema, uses default Top-K 5, does not resolve ModelRegistry/LLM dependencies, does not call LLM, and writes no Message/LLMCall/RagQuery.

- [x] **Step 2: Write chat endpoint RED**

Assert `/rag/chat` returns conversation/message IDs, answer, indexed sources, metadata, provider/model/usage/LLMCall ID, and subsequent conversation messages contain the raw user query plus answer.

- [x] **Step 3: Write API error RED**

Cover malformed schema 422, missing KB/conversation 404, unknown model 400, unavailable provider 503, Retriever invalid response safe 502, Embedding/VectorStore 503, Provider error mapping, no leaked query/source/diagnostic, and rollback after failure.

- [x] **Step 4: Run RED**

Run API tests. Expected: route imports or paths are missing.

- [x] **Step 5: Implement minimal wiring GREEN**

Construct Retriever from existing embedding/vector dependencies. Build RagQueryService only from DB/Retriever; build Prompt Builder from Settings and RagService from DB/Retriever/registry/providers. Add thin route response mappers and register the router. Map only RetrieverInputError/ResponseError with fixed safe codes/messages; preserve existing Provider/VectorStore mappings.

- [x] **Step 6: Run GREEN**

Run RAG API plus existing Chat/Knowledge Base/error tests. Expected: all pass with the known Starlette/httpx deprecation warning only.

---

### Task 6: Matching Verification And Documentation

**Files:**
- Create: `docs/23-naive-rag.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/20-knowledge-base-design.md`
- Modify: `docs/21-embedding-provider.md`
- Modify: `docs/22-document-ingestion-pipeline.md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`

**Interfaces:**
- Documents the implemented S4～S6 contract and explicit S7+ limitations.

- [x] **Step 1: Run focused matching verification**

Run Prompt/schema/service/API/Retriever/Provider/VectorStore/Chat/Conversation tests and record exact counts.

- [x] **Step 2: Run local Qdrant API smoke**

Use a random `codex_p3_m4_s4_s6_*` collection, deterministic Mock Embedding, Mock LLM, and system temporary SQLite. Through TestClient, verify query Top-K/KB isolation and chat answer/source/message persistence. Delete the collection and temporary database in `finally`; verify no matching collection remains.

- [x] **Step 3: Update docs**

Document request/response examples, Prompt budget/index behavior, transaction/error contract, non-streaming limitation, and explicit deferral of RagQuery audit, Agent Tool, frontend, and Advanced RAG. Do not claim a real Provider acceptance.

- [x] **Step 4: Run complete verification**

Run full backend tests, pip check, temporary SQLite Alembic upgrade/check/downgrade/re-upgrade, frontend typecheck/tests/build, Docker Compose config/ps/Qdrant health, Markdown link checks, secret/private-key scan, artifact scan, later-Plan runtime scan, `git diff --check`, exact diff allowlist, staged count, HEAD/origin/tags, and `git status`.

- [x] **Step 5: Codex self-review and fixes**

Classify findings as must fix, fix later, accepted limitation, or not applicable. For every behavior bug, first add a focused failing regression test, then implement the minimal fix and rerun affected plus full verification.

- [x] **Step 6: Manual Git handoff**

Leave the normal `main` workspace unstaged and uncommitted. Report whether S4～S6 are complete and whether the project can enter S7～S8. Suggest `feat(rag): add naive rag query and chat APIs` without executing Git writes.
