# Plan 4 M2 S4-S6 RAG Trace Integration Implementation Plan

> **For Codex:** Use the `executing-plans`, `test-driven-development`,
> `systematic-debugging`, and `verification-before-completion` skills while
> executing this plan. Do not use subagents for this repository task.

**Goal:** Persist normalized Naive RAG retrieval runs/candidates and ordered
retrieval, prompt, LLM, and final-answer Trace steps for standalone RAG Query
and RAG Chat without changing public response contracts.

**Architecture:** A service-level `RAGTraceRecorder` maps validated Retriever
batch results into new retrieval audit models and the generic `TraceService`.
`RagQueryService` owns standalone RAG Query orchestration; `RagService` reuses
one existing `rag_chat` TraceRun. Successful records share the caller's
transaction. Retrieval failures and RAG Chat Provider failures rebuild only
safe, durable audit state after rollback. Retriever/Provider/vector-store
adapters remain independent of SQLAlchemy and Trace.

**Tech stack:** Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2,
SQLite, pytest 9, React/TypeScript/Vitest/Vite, Mock Providers, fake Vector
Stores, Markdown, PowerShell, and read-only Git verification.

## Global Constraints

- Work only on `P4-M2-S4-S6`.
- Do not implement S7 Trace APIs, S8 frontend Trace types, S9 Timeline UI, or
  expose `trace_run_id` in current RAG responses.
- Do not implement Advanced RAG, evaluation, Memory, Agent Runtime v2, Human
  Approval, MCP, OCR, multimodal behavior, or later-Plan runtime.
- Preserve SQLite as the default supported database and keep reasonable
  SQLAlchemy/Alembic portability.
- Keep routes thin. Business orchestration stays in services; persistence
  mapping stays in the RAG Trace recorder.
- `TraceService` stays flush-only. The request/service owner owns transaction
  commit and rollback.
- `Retriever`, embedding Providers, vector stores, and prompt builder do not
  receive Sessions, TraceRuns, or observability dependencies.
- The HTTP RAG Query path enables standalone durable tracing. The Agent-owned
  `search_knowledge_base` executor explicitly disables it so this batch does
  not roll back/commit an Agent transaction or implement Agent/Tool Trace
  early.
- Do not persist vectors, full document text, full RAG context, full prompts,
  raw Provider diagnostics, exception strings, file paths, or secrets.
- Use only Mock LLM/Embedding Providers, fake Vector Stores, system-temporary
  SQLite/storage, and synthetic values. Do not read `.env`, credential stores,
  or `backend/ai_agent_lab.db`, and do not call paid/network Providers/Tools.
- Use TDD. Observe each expected RED failure before implementing its matching
  production behavior.
- Do not create a branch/worktree or stage, commit, push, pull, rebase, merge,
  or alter tags. The user performs Git mutations manually.
- Preserve unrelated user changes. Necessary code comments are Chinese and
  explain only non-obvious transaction/security boundaries.
- Codex self-review is the only review gate.

## Planned File Map

Create:

- `backend/app/models/retrieval.py`
- `backend/app/schemas/retrieval.py`
- `backend/app/rag/retrieval_recorder.py`
- `backend/alembic/versions/20260808_0009_rag_retrieval_trace.py`
- `backend/tests/test_retrieval_models.py`
- `backend/tests/test_retrieval_schemas.py`
- `backend/tests/test_retrieval_migration.py`
- `backend/tests/test_rag_trace.py`
- `docs/reviews/2026-08-08-plan4-m2-s4-s6-review.md`

Modify:

- `backend/app/models/__init__.py`
- `backend/app/models/trace.py`
- `backend/app/rag/retriever.py`
- `backend/app/observability/llm_trace.py`
- `backend/app/services/rag_service.py`
- `backend/app/api/dependencies.py`
- `backend/tests/test_retriever.py`
- `backend/tests/test_llm_trace.py`
- `backend/tests/test_rag_service.py`
- `backend/tests/test_rag_api.py`
- `backend/tests/test_search_knowledge_base_tool.py` or the narrow dependency
  test location selected from existing patterns
- `docs/01-architecture.md`
- `docs/23-naive-rag.md`
- `docs/30-trace-observability.md`
- `README.md`
- `README_CN.md`
- `CHANGELOG.md`
- `docs-plan/04-PLAN4/04-PLAN4-执行步骤表 (V1.0).md`

Do not modify frontend source or API types in this batch.

---

## Task 1: Retrieval ORM Models And Migration

**Files:**

- Create `backend/tests/test_retrieval_models.py`
- Create `backend/tests/test_retrieval_migration.py`
- Create `backend/app/models/retrieval.py`
- Modify `backend/app/models/trace.py`
- Modify `backend/app/models/__init__.py`
- Create `backend/alembic/versions/20260808_0009_rag_retrieval_trace.py`

### Step 1.1: Write model RED tests

Write tests that import `RagRetrievalRun` and `RagRetrievalCandidate` through
both `app.models.retrieval` and `app.models`. Use a temporary SQLite engine
with foreign keys enabled through the existing `create_db_engine` helper.

Cover:

- persistence of one TraceRun, one RetrievalRun, and ordered candidates;
- relationship ordering by candidate `rank`;
- isolated JSON defaults;
- multiple RetrievalRuns allowed for one TraceRun;
- deleting a TraceRun cascades RetrievalRuns and candidates;
- deleting a source Document/DocumentChunk preserves retrieval audit rows;
- invalid blank strategy/query/preview, out-of-range top_k/counts, selected
  count greater than candidate count, negative latency, non-positive ranks,
  unknown candidate source, and duplicate rank/final-rank constraints fail at
  the database boundary;
- audit UUID snapshots do not require source rows.

Run:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest tests/test_retrieval_models.py -q
```

Expected RED: import/module failure because retrieval models do not exist.

### Step 1.2: Write migration RED tests

Create a focused migration test using a temporary SQLite URL. Assert the new
tables, exact columns, indexes, foreign keys, unique constraints, checks, and
`ON DELETE CASCADE` from RetrievalRun to TraceRun and candidate to
RetrievalRun. Assert there are no source-table foreign keys for KB/document/
chunk snapshot IDs.

Cover upgrade to head, downgrade from `20260808_0009` to `20260802_0008`, and
re-upgrade plus `alembic check`.

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_retrieval_migration.py -q
```

Expected RED: head lacks the retrieval tables/revision.

### Step 1.3: Implement the minimal models and revision

Implement:

```python
class RagRetrievalRun(Base):
    # trace_run_id owns lifecycle; source IDs are immutable audit snapshots.
    ...


class RagRetrievalCandidate(Base):
    ...
```

Use explicit named constraints consistent with current migration/model style.
Add `TraceRun.retrieval_runs` with `cascade="all, delete-orphan"`,
`passive_deletes=True`, and deterministic creation ordering. Export both new
models from `app.models` so Alembic metadata discovers them.

Create revision `20260808_0009` with `down_revision = "20260802_0008"`.
Downgrade drops candidate objects before retrieval-run objects.

### Step 1.4: Reach GREEN and run adjacent model/migration regression

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_retrieval_models.py tests/test_retrieval_migration.py tests/test_trace_models.py tests/test_trace_migration.py -q
```

Expected GREEN: all selected tests pass from temporary databases.

---

## Task 2: Strict Retrieval Metadata And Backward-Compatible Batch Result

**Files:**

- Create `backend/tests/test_retrieval_schemas.py`
- Modify `backend/tests/test_retriever.py`
- Create `backend/app/schemas/retrieval.py`
- Modify `backend/app/rag/retriever.py`

### Step 2.1: Write strict schema RED tests

Define exact JSON-contract tests for:

- retrieval Step input/output;
- persisted RetrievalRun/candidate creation payloads;
- prompt Step input/source/output;
- final-answer Step input/output.

Assert UUIDs serialize as strings, score fields remain finite numbers,
booleans/integers are strict, identifiers are trimmed and bounded, candidate
preview is non-blank and at most 500 characters, counts/ranks are bounded,
unknown fields fail, and metadata is JSON-safe.

Representative retrieval output contract:

```python
{
    "retrieval_run_id": str(retrieval_run_id),
    "candidate_count": 1,
    "selected_count": 1,
}
```

Representative prompt source contract:

```python
{
    "source_index": 1,
    "candidate_id": str(candidate_id),
    "document_id": str(document_id),
    "chunk_id": str(chunk_id),
    "included_characters": 120,
    "truncated": False,
}
```

Run and observe schema-import RED:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_retrieval_schemas.py -q
```

### Step 2.2: Write Retriever batch RED tests

Extend `test_retriever.py` to assert a new immutable batch API returns:

- the same ordered `RetrievalResult` tuple as `retrieve()`;
- resolved embedding Provider/model identity from the query embedding;
- the same identity for a zero-hit vector search;
- defensive metadata/result behavior already guaranteed by current tests.

Keep a compatibility assertion that `retrieve()` still returns a tuple and
continues forwarding Top-K and score threshold exactly.

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_retriever.py -q
```

Expected RED: the batch method/result is absent.

### Step 2.3: Implement schemas and Retriever batch method

Create frozen, `extra="forbid"` schemas. Centralize identifier and finite-score
validation rather than duplicating loose dictionaries in the recorder.

Add an immutable Retriever batch result and an async batch method. Move the
existing retrieval implementation behind that method. Keep `retrieve()` as a
thin compatibility wrapper returning `.results` so Tool and existing callers
retain their contract.

Do not expose vector values or add Session/Trace imports to `retriever.py`.

### Step 2.4: Reach GREEN

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_retrieval_schemas.py tests/test_retriever.py tests/test_search_knowledge_base_tool.py -q
```

---

## Task 3: RAGTraceRecorder And Standalone RAG Query Trace

**Files:**

- Create `backend/tests/test_rag_trace.py`
- Modify `backend/tests/test_rag_service.py`
- Modify `backend/tests/test_rag_api.py`
- Modify the narrow Tool/dependency regression test
- Create `backend/app/rag/retrieval_recorder.py`
- Modify `backend/app/services/rag_service.py`
- Modify `backend/app/api/dependencies.py`

### Step 3.1: Write recorder RED tests

Using temporary SQLite and synthetic retrieval results, test that the recorder:

- starts a `rag_query` Run and `rag_retrieve` Step;
- persists one normalized RetrievalRun and ordered candidates;
- truncates previews to at most 500 Unicode characters without mutating the
  original RetrievalResult;
- stores `source="dense"`, `dense_score`, equal rank/final-rank, and null
  future-strategy scores;
- stores exact KB/embedding Provider/model vector filters, including zero hits;
- copies only `source_format`, `start_char`, `end_char`, and `heading_level`
  from chunk metadata and drops synthetic unknown/path-like keys;
- finishes the Step/Run but never commits on success;
- persists a class-name-only failed Run/Step after rollback and commits only
  that audit transaction;
- returns `None` and logs class/code only if failure-audit persistence itself
  fails, without leaking the raw exception text.

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_rag_trace.py -q
```

Expected RED: recorder module does not exist.

### Step 3.2: Write standalone service/API RED tests

Update existing RAG tests rather than duplicating their response assertions.
On success assert:

- exactly one completed `rag_query` TraceRun;
- exact `rag_retrieve` Step input/output;
- one RetrievalRun and correctly ordered candidates;
- zero hits still record Provider/model filters and zero counts;
- existing RagQuery snapshots and HTTP response bodies are unchanged;
- missing Knowledge Base still fails before embedding and creates no Trace.

On Retriever/Embedding/Vector Store failure assert:

- original safe-mapped exception/HTTP contract is unchanged;
- no RagQuery, RetrievalRun, or candidate survives;
- exactly one failed Run and one failed retrieval Step survive;
- only the exception class name is persisted and raw diagnostics are absent.

### Step 3.3: Write Agent Tool transaction-boundary RED test

Prove `get_rag_tool_query_executor` constructs the RAG query service with
standalone durable tracing disabled. Cover a retrieval failure inside the
Tool path and assert it does not call rollback/commit on the Agent-owned
Session, does not create a standalone TraceRun, and retains the existing safe
Tool failure result. Also assert a successful Tool search retains its legacy
RagQuery audit without creating a standalone TraceRun.

This is a regression boundary test only; do not add Agent or Tool Trace.

### Step 3.4: Implement the recorder and query orchestration

Implement a `RAGTraceRecorder` composed around `TraceService`. Use immutable
snapshots for failure reconstruction. Its successful methods add/flush but do
not commit or roll back. Its explicit retrieval-failure method owns the
approved rollback/recreate/commit boundary and never masks the original
exception.

Build candidate metadata through an explicit allowlist. Do not treat generic
JSON-safe metadata as safe for Trace persistence.

Refactor `RagQueryService` into one shared internal retrieval operation plus
two orchestration policies:

- traced standalone execution for HTTP/direct RAG Query;
- untraced, caller-transaction-preserving execution for the Agent Tool
  dependency.

Do not put a trace flag in HTTP request schemas or public API. Configure the
policy only at service construction in `api/dependencies.py`.

### Step 3.5: Reach GREEN

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_rag_trace.py tests/test_rag_service.py tests/test_rag_api.py tests/test_search_knowledge_base_tool.py tests/test_simple_agent.py -q
```

---

## Task 4: RAG Chat Retrieval, Prompt, And Final-Answer Steps

**Files:**

- Modify `backend/tests/test_llm_trace.py`
- Modify `backend/tests/test_rag_trace.py`
- Modify `backend/tests/test_rag_service.py`
- Modify `backend/tests/test_rag_api.py`
- Modify `backend/app/observability/llm_trace.py`
- Modify `backend/app/rag/retrieval_recorder.py`
- Modify `backend/app/services/rag_service.py`

### Step 4.1: Write LLM completion compatibility RED test

Add a test that `LLMTraceRecorder.complete_call(..., finish_run=False)`:

- completes the `llm_call` Step;
- copies resolved model, tokens, cost, and latency to the Run;
- leaves the Run in `running` status with no end timestamp/output;
- preserves the existing default `finish_run=True` behavior for non-RAG Chat.

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_trace.py -q
```

Expected RED: the completion option is absent.

### Step 4.2: Write RAG Chat success RED tests

Extend the existing grounded-turn and zero-hit tests. Assert one Run with
exact step order:

```python
[
    "rag_retrieve",
    "build_prompt",
    "llm_call",
    "final_answer",
]
```

Assert:

- no nested/duplicate `rag_query` Run is created;
- RetrievalRun/candidates match Retriever result order and scores;
- prompt input references the RetrievalRun and `naive-rag-v1`;
- prompt output source order maps to candidate/document/chunk IDs;
- `included_characters` and `truncated` agree with the Prompt Builder's
  context-budget behavior;
- zero hits produce zero candidates/sources but still complete all four Steps;
- final answer output contains RagQuery, answer Message, and LLMCall IDs plus
  source/character counts;
- no Step JSON contains the full context or answer text;
- Run output/totals match the response and legacy LLMCall;
- existing RAG Chat response shape remains byte-structure compatible.

Add one small-context test with two candidates to prove the prompt subset and
truncation semantics, rather than adding repetitive happy-path cases.

### Step 4.3: Implement success orchestration

Use the existing RAG Chat `LLMTraceRecorder.start_run` result as the one Run.
Pass its `TraceRun` record into RAGTraceRecorder for retrieval/prompt/final
steps. Call the shared internal retrieval operation directly so it cannot
create a second Run.

Implement prompt source mapping from the persisted ordered candidate list.
Finish the LLM Step with `finish_run=False`, record final-answer correlation
metadata, then finish the Run with the answer text. Keep all records in the
same request transaction.

### Step 4.4: Reach GREEN and run non-RAG Chat regression

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_trace.py tests/test_rag_trace.py tests/test_rag_service.py tests/test_rag_api.py tests/test_chat_service.py tests/test_chat_api.py -q
```

---

## Task 5: Provider-Failure Audit Reconstruction

**Files:**

- Modify `backend/tests/test_llm_trace.py`
- Modify `backend/tests/test_rag_trace.py`
- Modify `backend/tests/test_rag_service.py`
- Modify `backend/tests/test_rag_api.py`
- Modify `backend/app/observability/llm_trace.py`
- Modify `backend/app/rag/retrieval_recorder.py`
- Modify `backend/app/services/rag_service.py`

### Step 5.1: Write failure reconstruction RED tests

For `ProviderRequestError` and invalid/blank Provider completions mapped to
`ProviderResponseError`, assert:

- provisional user/assistant Messages, RagQuery, and legacy LLMCall are gone;
- one failed `rag_chat` Run remains correlated only to the pre-existing
  Conversation;
- completed retrieval and prompt Steps are reconstructed at indexes 1 and 2;
- normalized RetrievalRun and candidates are reconstructed with the same IDs,
  scores, ranks, previews, and safe metadata snapshots;
- failed `llm_call` is index 3 with `output_json=None`;
- no `final_answer` Step exists because no answer completed;
- Run/Step error text is only the exception class;
- raw Provider diagnostics, full prompt/context, and rolled-back user Message
  ID are absent.

Retain existing generic Chat failure tests unchanged.

### Step 5.2: Implement a narrow pre-failed-call replay hook

Extend `LLMTraceRecorder.persist_failure` with an optional internal callback
that runs after the failed Run is recreated and before the failed LLM Step is
added. Existing Chat callers pass nothing and retain exactly one failed LLM
Step. RAG Chat supplies a RAGTraceRecorder callback that replays only already
completed retrieval/prompt audit data.

The LLM recorder remains the owner of Provider-failure rollback, explicit
audit commit, safe error normalization, and best-effort logging. The replay
callback must not receive or persist the raw exception.

### Step 5.3: Reach GREEN

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_trace.py tests/test_rag_trace.py tests/test_rag_service.py tests/test_rag_api.py tests/test_chat_service.py tests/test_chat_api.py -q
```

If any failure is not the expected missing behavior, stop and use systematic
debugging before modifying production code.

---

## Task 6: Documentation, Matching Regression, And Final Review

**Files:**

- Modify the current-fact docs listed in the Planned File Map
- Create `docs/reviews/2026-08-08-plan4-m2-s4-s6-review.md`

### Step 6.1: Update documentation after implementation is GREEN

Document:

- normalized retrieval audit tables and source-snapshot lifecycle;
- successful RAG Query/RAG Chat step order;
- zero-hit and failure behavior;
- prompt/source/answer metadata and excluded sensitive payloads;
- `search_knowledge_base` transaction/Trace boundary;
- the current limitation that prompt-construction failures use ordinary
  rollback and do not rebuild a durable failed Trace;
- S7-S9 API/UI work remains pending;
- migration head `20260808_0009`.

Mark only Batch 5 and S4-S6 complete in the active Plan 4 execution table.
Do not edit later Step status or claim frontend Timeline availability.

### Step 6.2: Run focused and matching verification

From `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_retrieval_models.py tests/test_retrieval_schemas.py tests/test_retrieval_migration.py tests/test_rag_trace.py tests/test_retriever.py tests/test_rag_prompt.py tests/test_rag_service.py tests/test_rag_api.py tests/test_llm_trace.py tests/test_trace_models.py tests/test_trace_schemas.py tests/test_trace_service.py tests/test_trace_migration.py tests/test_chat_service.py tests/test_chat_api.py tests/test_search_knowledge_base_tool.py tests/test_simple_agent.py -q
```

Record the exact fresh count and warnings.

### Step 6.3: Run full backend and dependency verification

Create explicit system-temporary paths outside the repository for database and
document storage. Point `DATABASE_URL` and `DOCUMENT_STORAGE_ROOT` at those
paths, run the full suite, and remove only the verified temporary directory.

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Never allow the command to resolve to `backend/ai_agent_lab.db`.

### Step 6.4: Run temporary SQLite migration lifecycle

Against a fresh system-temporary SQLite URL run:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current --check-heads
..\.venv\Scripts\python.exe -m alembic check
..\.venv\Scripts\python.exe -m alembic downgrade 20260802_0008
..\.venv\Scripts\python.exe -m alembic upgrade head
```

Verify head is `20260808_0009` and both retrieval tables disappear/reappear at
the expected lifecycle points.

### Step 6.5: Run frontend regression

From `frontend`:

```powershell
npm run typecheck
npm test
npm run build
```

No browser replay is required because no response or UI contract changes.
No live Qdrant smoke is required because Retriever/vector-store behavior and
payload filtering are unchanged; fake Vector Store tests cover the new batch
result and recorder boundary. Record both risk judgments in the review.

### Step 6.6: Run repository safety and documentation checks

Use repository-local or read-only scripts where available to verify:

- all Markdown local links/images resolve;
- no secret/private-key patterns were added;
- no unexpected generated artifacts, SQLite databases, coverage outputs,
  caches, or logs are included in the diff;
- no network Tool, Advanced RAG, evaluation, S7-S9 UI/API, or Plan 5+ runtime
  was added;
- `git diff --check` passes;
- branch remains `main`, staged paths remain zero, and only intended files are
  modified/untracked.

Do not read real `.env`, secret stores, or the user database while scanning.

### Step 6.7: Codex final self-review

Review the complete diff against the approved design and classify every
finding as:

- must fix;
- fix later;
- recorded limitation;
- not applicable.

Specifically inspect transaction rollback/commit ownership, failed audit
reconstruction, candidate/source ordering, snapshot retention, JSON redaction,
zero-hit identity, Tool transaction isolation, migration downgrade, public API
compatibility, Plan boundary, and documentation truthfulness. Fix any current
batch must-fix through a new RED/GREEN cycle and rerun affected plus full
verification.

### Step 6.8: Handoff for manual Git action

Report:

- implementation summary and exact changed files;
- RED/GREEN evidence;
- focused/full backend, `pip check`, frontend, and migration results;
- docs/link/security/artifact/Git checks;
- browser/Qdrant omission rationale;
- Codex review classifications and residual limitations;
- whether P4-M2-S4-S6 is complete and whether S7 may begin;
- suggested commit message:

```text
feat(observability): trace rag retrieval and answers
```

Leave all files unstaged and do not commit or tag.

## Definition Of Done

The batch is complete only when the new retrieval audit schema and migration,
standalone RAG Query Trace, ordered RAG Chat steps, safe retrieval/Provider
failure audits, Tool transaction boundary, compatibility tests, documentation,
full verification, and Codex self-review all pass with no remaining must-fix.
