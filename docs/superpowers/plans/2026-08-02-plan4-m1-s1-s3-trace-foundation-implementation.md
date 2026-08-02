# Plan 4 M1 S1～S3 Trace Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify the repaired Plan 3 handoff and add SQLite-portable TraceRun/TraceStep persistence, strict schemas, and stable string-enum contracts without activating Trace runtime behavior.

**Architecture:** A dependency-free observability type module defines all persisted Trace values. SQLAlchemy stores those values as strings protected by named checks, preserves TraceRun audit rows when operational records are deleted, and cascades only TraceRun deletion into TraceStep. Pydantic schemas reuse the same enums; Alembic revision `20260802_0008` creates the two new tables.

**Tech Stack:** Python 3.12, FastAPI/Pydantic v2, SQLAlchemy 2, Alembic, SQLite, pytest.

## Global Constraints

- Implement only `P4-M1-S1～S3` from the current execution table.
- Do not implement Trace Service, Trace Context, runtime hooks, Trace API/UI, Advanced RAG, reranking, evaluation, Memory, Agent Runtime v2, MCP, or multimodal behavior.
- Keep SQLite as the default and supported database; use portable SQLAlchemy/Alembic constructs.
- Preserve TraceRun on Conversation/AgentRun/Message deletion with `SET NULL`; cascade only TraceRun deletion to TraceStep.
- Use Chinese only for necessary non-obvious code comments.
- Use mocks/system-temporary SQLite only; do not read `.env`, real credentials, paid Providers, network Tools, or `backend/ai_agent_lab.db`.
- Do not create/switch a branch or worktree and do not stage, commit, push, pull, merge, rebase, or modify tags; the user performs Git actions manually.
- The current execution table overrides the older combined Step 3 wording: Service/Context remain `P4-M1-S4～S6`.

---

### Task 1: Verify And Freeze The Plan 3 Handoff

**Files:**
- Read: `docs/reviews/2026-08-02-plan3-final-audit-plan4-entry.md`
- Create later in Task 5: `docs/reviews/2026-08-02-plan4-m1-s1-s3-review.md`

**Interfaces:**
- Consumes: Plan 3 RAG Query/Chat APIs, `search_knowledge_base`, Simple Agent compatibility, Git refs.
- Produces: fresh S1 evidence and an exact immutable starting baseline for the batch review.

- [ ] **Step 1: Capture the immutable Git baseline**

Run from repository root:

```powershell
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git rev-parse 'v0.3.0^{}'
git rev-parse 'v0.3.1^{}'
git status --short
git diff --cached --name-only
```

Expected: `main`; HEAD/origin/v0.3.1 at the repair commit; v0.3.0 at the
original release commit; no pre-existing status or staged paths except the
approved spec/plan documents created during this workflow.

- [ ] **Step 2: Run the Plan 3 bridge compatibility group**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_rag_api.py tests/test_rag_service.py tests/test_search_knowledge_base_tool.py tests/test_simple_agent.py -q
```

Expected: PASS with Mock Provider/temp-database behavior only. Record the exact
pass/warning counts for Task 5. If a failure is reproducible, invoke
systematic-debugging and fix only a Plan 3 regression that blocks S1.

- [ ] **Step 3: Preserve the boundary**

Review the changed-path list and confirm that Task 1 made no production code,
database, tag, or staging changes. Do not commit; continue with Task 2.

---

### Task 2: Define Trace Enums And Strict Schemas With TDD

**Files:**
- Create: `backend/app/observability/__init__.py`
- Create: `backend/app/observability/trace_types.py`
- Create: `backend/app/schemas/trace.py`
- Modify: `backend/app/schemas/__init__.py`
- Create: `backend/tests/test_trace_types.py`
- Create: `backend/tests/test_trace_schemas.py`

**Interfaces:**
- Produces: `TraceRunType`, `TraceStatus`, `TraceStepType`, `TraceRunCreate`, `TraceRunRead`, `TraceStepCreate`, and `TraceStepRead`.
- Consumed by: Task 3 ORM constraints/defaults and future S4～S6 Trace Service.

- [ ] **Step 1: Write failing enum contract tests**

Create `backend/tests/test_trace_types.py` with exact value and string
serialization assertions:

```python
import json

from app.observability.trace_types import (
    TraceRunType,
    TraceStatus,
    TraceStepType,
)


def test_trace_enum_values_are_stable_strings() -> None:
    assert [item.value for item in TraceRunType] == [
        "chat", "agent", "rag_query", "rag_chat", "evaluation", "tool"
    ]
    assert [item.value for item in TraceStatus] == [
        "pending", "running", "completed", "failed", "cancelled"
    ]
    assert [item.value for item in TraceStepType] == [
        "build_context", "llm_call", "tool_call", "rag_retrieve",
        "query_rewrite", "bm25_search", "vector_search", "hybrid_fusion",
        "parent_child_expand", "rerank", "build_prompt", "final_answer",
        "eval_metric",
    ]


def test_trace_enums_serialize_as_json_strings() -> None:
    payload = {
        "run_type": TraceRunType.RAG_QUERY,
        "status": TraceStatus.RUNNING,
        "step_type": TraceStepType.RAG_RETRIEVE,
    }
    assert json.loads(json.dumps(payload)) == {
        "run_type": "rag_query",
        "status": "running",
        "step_type": "rag_retrieve",
    }
```

- [ ] **Step 2: Write failing schema validation tests**

Create `backend/tests/test_trace_schemas.py`. Cover valid JSON-mode dumps,
isolated metadata/input defaults, enum rejection, blank input/name rejection,
extra-field rejection, strict step index, negative usage/cost/latency rejection,
and ORM read validation. Use fixed UUIDs and UTC-naive datetimes; the central
examples are:

```python
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.observability.trace_types import TraceRunType, TraceStatus, TraceStepType
from app.schemas.trace import TraceRunCreate, TraceRunRead, TraceStepCreate, TraceStepRead


def test_trace_run_schema_serializes_enum_and_uuid_values() -> None:
    conversation_id = uuid4()
    payload = TraceRunCreate(
        run_type=TraceRunType.RAG_QUERY,
        conversation_id=conversation_id,
        input_text="Why provider abstraction?",
        metadata_json={"strategy": "naive_vector"},
    )
    assert payload.model_dump(mode="json") == {
        "run_type": "rag_query",
        "conversation_id": str(conversation_id),
        "agent_run_id": None,
        "user_message_id": None,
        "title": None,
        "input_text": "Why provider abstraction?",
        "provider": None,
        "model": None,
        "status": "pending",
        "metadata_json": {"strategy": "naive_vector"},
    }


def test_trace_step_schema_rejects_invalid_values() -> None:
    with pytest.raises(ValidationError):
        TraceStepCreate(
            trace_run_id=uuid4(), step_index=0,
            step_type=TraceStepType.LLM_CALL, name="LLM", input_json={}
        )
    with pytest.raises(ValidationError):
        TraceStepCreate(
            trace_run_id=uuid4(), step_index=1,
            step_type="unknown", name="LLM", input_json={}
        )


def test_trace_read_schemas_accept_orm_attributes() -> None:
    now = datetime(2026, 8, 2, 12, 0, 0)
    run_id = uuid4()
    run = TraceRunRead.model_validate(SimpleNamespace(
        id=run_id, run_type="chat", conversation_id=None,
        agent_run_id=None, user_message_id=None, title=None,
        input_text="hello", output_text=None, status="running",
        provider=None, model=None, total_input_tokens=None,
        total_output_tokens=None, total_tokens=None, estimated_cost=None,
        latency_ms=None, error_message=None, metadata_json={},
        started_at=now, ended_at=None, created_at=now,
    ))
    assert run.id == run_id
    assert run.status is TraceStatus.RUNNING
```

Include parametrized invalid metrics for `total_input_tokens`,
`total_output_tokens`, `total_tokens`, `estimated_cost`, and `latency_ms`, and
assert `Decimal("0.00000001")` remains exact.

- [ ] **Step 3: Run the new tests and verify RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_types.py tests/test_trace_schemas.py -q
```

Expected: collection errors because `app.observability.trace_types` and
`app.schemas.trace` do not exist. This is the required RED evidence.

- [ ] **Step 4: Implement the dependency-free enum module**

Create `backend/app/observability/__init__.py` with only the public enum
re-exports. Create `trace_types.py` using `StrEnum`:

```python
from enum import StrEnum


class TraceRunType(StrEnum):
    CHAT = "chat"
    AGENT = "agent"
    RAG_QUERY = "rag_query"
    RAG_CHAT = "rag_chat"
    EVALUATION = "evaluation"
    TOOL = "tool"


class TraceStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TraceStepType(StrEnum):
    BUILD_CONTEXT = "build_context"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    RAG_RETRIEVE = "rag_retrieve"
    QUERY_REWRITE = "query_rewrite"
    BM25_SEARCH = "bm25_search"
    VECTOR_SEARCH = "vector_search"
    HYBRID_FUSION = "hybrid_fusion"
    PARENT_CHILD_EXPAND = "parent_child_expand"
    RERANK = "rerank"
    BUILD_PROMPT = "build_prompt"
    FINAL_ANSWER = "final_answer"
    EVAL_METRIC = "eval_metric"
```

- [ ] **Step 5: Implement strict create/read schemas**

Create `backend/app/schemas/trace.py` with bounded identifiers, blank-string
validators, `StrictInt`/`FiniteFloat` constraints, object JSON fields, and
`from_attributes=True` reads. Use these signatures exactly:

```python
class TraceRunCreate(BaseModel):
    run_type: TraceRunType
    conversation_id: UUID | None = None
    agent_run_id: UUID | None = None
    user_message_id: UUID | None = None
    title: str | None = Field(default=None, max_length=255)
    input_text: str = Field(min_length=1)
    provider: TraceProviderIdentifier | None = None
    model: TraceModelIdentifier | None = None
    status: TraceStatus = TraceStatus.PENDING
    metadata_json: dict[str, JsonValue] = Field(default_factory=dict)


class TraceRunRead(TraceRunCreate):
    id: UUID
    output_text: str | None
    total_input_tokens: StrictInt | None = Field(default=None, ge=0)
    total_output_tokens: StrictInt | None = Field(default=None, ge=0)
    total_tokens: StrictInt | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=0)
    latency_ms: StrictInt | None = Field(default=None, ge=0)
    error_message: str | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


class TraceStepCreate(BaseModel):
    trace_run_id: UUID
    step_index: StrictInt = Field(gt=0)
    step_type: TraceStepType
    name: str = Field(min_length=1, max_length=255)
    status: TraceStatus = TraceStatus.PENDING
    input_json: dict[str, JsonValue] = Field(default_factory=dict)


class TraceStepRead(TraceStepCreate):
    id: UUID
    output_json: dict[str, JsonValue] | None
    error_message: str | None
    latency_ms: StrictInt | None = Field(default=None, ge=0)
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
```

Set `ConfigDict(extra="forbid")` on create schemas and
`ConfigDict(extra="forbid", from_attributes=True)` on read schemas. Add field
validators that reject whitespace-only `input_text`/`name` without altering
the stored content. Re-export all four schemas and all enums from the schema
package as appropriate.

- [ ] **Step 6: Run the focused tests and verify GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_types.py tests/test_trace_schemas.py -q
```

Expected: all new enum/schema tests PASS. Run `git diff --check` and leave the
files unstaged for the user's final batch commit.

---

### Task 3: Add TraceRun And TraceStep ORM Models With TDD

**Files:**
- Create: `backend/app/models/trace.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/conversation.py`
- Modify: `backend/app/models/message.py`
- Modify: `backend/app/models/agent_run.py`
- Create: `backend/tests/test_trace_models.py`

**Interfaces:**
- Consumes: Task 2 enums and existing `Base`, `utc_now`, Conversation, Message, AgentRun.
- Produces: `TraceRun` and `TraceStep` ORM classes plus audit-preserving relationships.

- [ ] **Step 1: Write failing persistence and default tests**

Create a temporary-SQLite fixture using `create_db_engine` and
`Base.metadata.create_all`. Add a helper that persists Conversation, Message,
and AgentRun, then test a TraceRun with two ordered TraceSteps. Assert UUIDs,
`pending` defaults, naive-UTC timestamps, relationship order, and isolated
`metadata_json` / `input_json` dict defaults.

Core construction:

```python
run = TraceRun(
    run_type=TraceRunType.AGENT.value,
    conversation=conversation,
    agent_run=agent_run,
    user_message=message,
    input_text="Use one safe tool",
)
run.steps.extend([
    TraceStep(step_index=1, step_type=TraceStepType.BUILD_CONTEXT.value,
              name="Build context"),
    TraceStep(step_index=2, step_type=TraceStepType.LLM_CALL.value,
              name="Call model"),
])
```

- [ ] **Step 2: Write failing integrity/deletion tests**

Add tests that prove:

- deleting TraceRun deletes its TraceSteps;
- deleting Message sets only `user_message_id` to null and retains the run;
- deleting AgentRun sets only `agent_run_id` to null and retains the run;
- deleting Conversation clears all three operational links and retains the
  run/steps;
- cross-Conversation Message or AgentRun references fail with
  `IntegrityError`;
- step index `0` and duplicate `(trace_run_id, step_index)` fail;
- unknown run type/status/step type and negative tokens/cost/latency fail.

Always call `session.rollback()` after each expected integrity failure so one
case does not contaminate the next.

- [ ] **Step 3: Run the model tests and verify RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_models.py -q
```

Expected: collection/import failure because `app.models.trace` and its exports
do not exist.

- [ ] **Step 4: Implement TraceRun and TraceStep**

Create both models in `backend/app/models/trace.py`. Use plain `String(32)`
columns plus named checks built from the Task 2 enum values. Required database
constraints are:

```python
CheckConstraint("run_type IN ('chat', 'agent', 'rag_query', 'rag_chat', 'evaluation', 'tool')", name="ck_trace_runs_run_type")
CheckConstraint("status IN ('pending', 'running', 'completed', 'failed', 'cancelled')", name="ck_trace_runs_status")
CheckConstraint("total_input_tokens IS NULL OR total_input_tokens >= 0", name="ck_trace_runs_total_input_tokens_non_negative")
CheckConstraint("total_output_tokens IS NULL OR total_output_tokens >= 0", name="ck_trace_runs_total_output_tokens_non_negative")
CheckConstraint("total_tokens IS NULL OR total_tokens >= 0", name="ck_trace_runs_total_tokens_non_negative")
CheckConstraint("estimated_cost IS NULL OR estimated_cost >= 0", name="ck_trace_runs_estimated_cost_non_negative")
CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="ck_trace_runs_latency_ms_non_negative")
ForeignKeyConstraint(["agent_run_id", "conversation_id"], ["agent_runs.id", "agent_runs.conversation_id"], name="fk_trace_runs_agent_run_conversation_agent_runs", ondelete="NO ACTION")
ForeignKeyConstraint(["user_message_id", "conversation_id"], ["messages.id", "messages.conversation_id"], name="fk_trace_runs_user_message_conversation_messages", ondelete="NO ACTION")
```

Also use direct `SET NULL` foreign keys for each optional correlation. Define
TraceRun relationships with explicit `foreign_keys` to avoid composite-FK
ambiguity. Use `before_insert` / `before_update` ORM validation to require a
Conversation whenever AgentRun or user Message is present. This replaces an
initial database `CHECK` design that conflicts with SQLite's sequential
`SET NULL` actions during Conversation deletion. Define steps as:

```python
steps: Mapped[list[TraceStep]] = relationship(
    back_populates="trace_run",
    cascade="all, delete-orphan",
    passive_deletes=True,
    order_by="TraceStep.step_index",
)
```

TraceStep must include checked status/step type, positive step index,
non-negative latency, `UniqueConstraint("trace_run_id", "step_index")`, and
`ForeignKey("trace_runs.id", ondelete="CASCADE")`.

- [ ] **Step 5: Add operational-record back-references and exports**

Add `trace_runs` relationships to Conversation, Message, and AgentRun. Use
`passive_deletes=True`, explicit foreign keys, and no cascade/delete-orphan.
Export `TraceRun` and `TraceStep` from `app.models` so Alembic imports their
metadata.

- [ ] **Step 6: Run model tests and verify GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_models.py tests/test_agent_models.py tests/test_knowledge_models.py -q
```

Expected: all Trace and adjacent ownership/deletion model tests PASS without
SQLAlchemy relationship warnings.

---

### Task 4: Add Alembic Revision 0008 With TDD

**Files:**
- Create: `backend/alembic/versions/20260802_0008_trace_foundation.py`
- Create: `backend/tests/test_trace_migration.py`

**Interfaces:**
- Consumes: Task 3 `Base.metadata` table definitions.
- Produces: migration head `20260802_0008` whose schema matches ORM metadata.

- [ ] **Step 1: Write failing migration inspector tests**

Create a temporary database and Alembic config following existing migration
tests. After `command.upgrade(config, "head")`, assert exact table columns,
named checks, indexes, uniqueness, and FK actions. Key expectations:

```python
assert {"trace_runs", "trace_steps"} <= set(inspector.get_table_names())
assert trace_run_fks[("conversation_id",)]["options"]["ondelete"] == "SET NULL"
assert trace_run_fks[("agent_run_id",)]["options"]["ondelete"] == "SET NULL"
assert trace_run_fks[("user_message_id",)]["options"]["ondelete"] == "SET NULL"
assert trace_run_fks[("agent_run_id", "conversation_id")]["options"]["ondelete"] == "NO ACTION"
assert trace_run_fks[("user_message_id", "conversation_id")]["options"]["ondelete"] == "NO ACTION"
assert trace_step_fks[("trace_run_id",)]["options"]["ondelete"] == "CASCADE"
assert {item["name"] for item in inspector.get_unique_constraints("trace_steps")} == {"uq_trace_steps_trace_run_id_step_index"}
```

Also assert downgrade from head to `20260801_0007` removes only the Trace
tables while preserving Plan 3 tables, followed by a successful re-upgrade.

- [ ] **Step 2: Run the migration test and verify RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_migration.py -q
```

Expected: FAIL because Alembic head is still `20260801_0007` and the Trace
tables do not exist.

- [ ] **Step 3: Implement revision 20260802_0008**

Create `backend/alembic/versions/20260802_0008_trace_foundation.py` with:

```python
revision = "20260802_0008"
down_revision = "20260801_0007"
```

In `upgrade()`, call `op.create_table("trace_runs", ...)` with the exact ORM
columns/constraints, then create indexes for `conversation_id`, `agent_run_id`,
and `user_message_id`. Create `trace_steps` second, including the cascade FK,
positive index/status/type/latency checks, unique step position, and a
`trace_run_id` index. Do not add a data backfill or access existing rows.

In `downgrade()`, drop the TraceStep index/table first, then TraceRun indexes
and table. Use explicit constraint names matching Task 3.

- [ ] **Step 4: Run migration/model/schema tests and verify GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_types.py tests/test_trace_schemas.py tests/test_trace_models.py tests/test_trace_migration.py tests/test_migrations.py tests/test_agent_migrations.py tests/test_knowledge_migration.py -q
```

Expected: all focused Trace and migration compatibility tests PASS.

- [ ] **Step 5: Run a standalone temporary migration lifecycle**

Create a system-temporary directory, set only a synthetic `DATABASE_URL`, and
run from that directory so repository `.env` and the user database cannot be
selected:

```powershell
$traceTemp = Join-Path ([System.IO.Path]::GetTempPath()) ("ai-agent-lab-p4-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $traceTemp | Out-Null
$env:DATABASE_URL = "sqlite:///" + (Join-Path $traceTemp 'trace.db').Replace('\','/')
Push-Location $traceTemp
& 'F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe' -m alembic -c 'F:\MyProjects\AI-Agent-Lab\backend\alembic.ini' upgrade head
& 'F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe' -m alembic -c 'F:\MyProjects\AI-Agent-Lab\backend\alembic.ini' current --check-heads
& 'F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe' -m alembic -c 'F:\MyProjects\AI-Agent-Lab\backend\alembic.ini' check
& 'F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe' -m alembic -c 'F:\MyProjects\AI-Agent-Lab\backend\alembic.ini' downgrade 20260801_0007
& 'F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe' -m alembic -c 'F:\MyProjects\AI-Agent-Lab\backend\alembic.ini' upgrade head
Pop-Location
Remove-Item -LiteralPath $traceTemp -Recurse -Force
Remove-Item Env:DATABASE_URL
```

Before removal, resolve and verify `$traceTemp` remains under the system temp
directory. Expected final head: `20260802_0008`; `alembic check` reports no new
upgrade operations.

---

### Task 5: Document, Verify, And Self-Review The Batch

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs-plan/04-PLAN4/04-PLAN4-执行步骤表 (V1.0).md`
- Create: `docs/reviews/2026-08-02-plan4-m1-s1-s3-review.md`
- Review: all Task 2～4 files and this spec/plan.

**Interfaces:**
- Consumes: exact RED/GREEN, regression, migration, Git, and hygiene evidence.
- Produces: truthful batch handoff ready for the user's manual commit.

- [ ] **Step 1: Update durable documentation**

Add an Unreleased CHANGELOG entry for the Trace foundation. Update the
architecture document with the two tables, audit-preserving deletion policy,
enum/check strategy, and explicit “models only; runtime hooks begin in
S4～S6” boundary. Mark only Batch 1 / S1～S3 as completed in the Plan 4
execution table; do not mark M1 complete.

Create the batch review with:

- starting Git/tag baseline;
- S1 Plan 3 compatibility evidence;
- S2/S3 acceptance matrix and exact file locations;
- RED/GREEN evidence;
- focused/full/migration verification results;
- finding classification (`must fix`, `fix later`, `recorded limitation`,
  `not applicable`);
- Plan boundary/security/Git self-review;
- clear statement that Trace runtime is not active until S4～S6.

- [ ] **Step 2: Run the complete backend regression**

Run from `backend/` with a synthetic temp-backed environment that cannot open
the user database:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Expected: zero test failures and `No broken requirements found.` Record exact
counts/warnings. If failures occur, use systematic-debugging; do not weaken
existing tests.

- [ ] **Step 3: Run documentation and hygiene gates**

Check every tracked Markdown local link/image, added lines for high-confidence
secrets/private-key material, executable network Tool or later-Plan runtime,
tracked build/cache/database artifacts, and `git diff --check`. Do not read any
real `.env` or credential path. Expected: zero missing local links, zero new
secrets/keys, zero unexpected artifacts/runtime, and no whitespace errors.

- [ ] **Step 4: Run final Git/ref/scope checks**

```powershell
git diff --name-status
git diff --stat
git diff --cached --name-only
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git rev-parse 'v0.3.0^{}'
git rev-parse 'v0.3.1^{}'
git diff --check
```

Expected: only S1～S3 implementation/test/docs paths; staged paths zero;
branch/HEAD/origin/tags unchanged from Task 1.

- [ ] **Step 5: Perform Codex self-review and remediate must-fix findings**

Review model/schema/migration parity, deletion/ownership semantics, enum
coverage, JSON default isolation, test value, Plan boundary, secrets,
documentation truth, and migration downgrade safety. Classify every finding.
Fix any S1～S3 must-fix through a new RED/GREEN cycle and re-run the affected
plus full gates.

- [ ] **Step 6: Hand off for manual commit**

Do not stage or commit. Report the exact verification evidence, residual
limitations, and readiness for `P4-M1-S4～S6`. Suggested commit message:

```text
feat(observability): add trace run and step foundation
```
