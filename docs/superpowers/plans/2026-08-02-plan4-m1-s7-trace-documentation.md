# Plan 4 M1 S7 Trace Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the current-fact Trace foundation contract, synchronize project status, and close Plan 4 M1 with a fresh Codex-only review.

**Architecture:** One formal document owns the implemented M1 Trace contract; README and architecture files link to it instead of duplicating all details. A consolidated final review maps S1-S7 to fresh test, migration, documentation, hygiene, and Git evidence while keeping all M2 behavior explicitly deferred.

**Tech Stack:** Markdown, Python 3.11, pytest 9, SQLAlchemy/Alembic, temporary SQLite, PowerShell, Git read-only verification.

## Global Constraints

- Work only on `P4-M1-S7`; do not add or modify production code, ORM/schema/migration behavior, API routes, frontend behavior, or any M2/Plan 5 runtime.
- Describe only behavior already implemented through S6. Do not present planned Trace API, Timeline, Chat/RAG/Agent hooks, cancellation, aggregation, Advanced RAG, reranking, or evaluation as available.
- Codex self-review is the only review gate; do not request, run, await, or cite Claude Code, Fable, or another external review.
- Use the current clean `main` workspace. Do not create a branch/worktree or stage, commit, push, pull, rebase, merge, or move tags.
- Never read or mutate `backend/ai_agent_lab.db`, a real `.env`, credentials, paid Providers, or network Tools.
- Backend and migration verification use explicit system-temporary SQLite/storage paths.
- The user performs the final Git commit manually.

## File Structure

- Create `docs/30-trace-observability.md`: canonical current-fact M1 Trace contract.
- Modify `docs/01-architecture.md`: current stage, `observability/` layer, and S1-S6 runtime-foundation summary.
- Modify `README.md`: English current stage, verified scope, documentation links, limitations, and roadmap.
- Modify `README_CN.md`: Chinese mirror of the README status changes.
- Modify `docs-plan/04-PLAN4/04-PLAN4-执行步骤表 (V1.0).md`: mark Batch 3/S7 complete and use Codex-only M1 review wording.
- Create `docs/reviews/2026-08-02-plan4-m1-final-review.md`: consolidated S1-S7 acceptance and verification record.
- Preserve `CHANGELOG.md` unless verification finds an actual factual mismatch; S1-S6 feature behavior is already recorded there.
- Preserve all production and test source files.

---

### Task 1: Publish The Formal Trace Foundation Contract

**Files:**
- Create: `docs/30-trace-observability.md`
- Source-check: `backend/app/models/trace.py`
- Source-check: `backend/app/schemas/trace.py`
- Source-check: `backend/app/observability/trace_types.py`
- Source-check: `backend/app/observability/trace_service.py`
- Source-check: `backend/app/observability/trace_context.py`
- Source-check: `backend/app/observability/token_cost.py`
- Source-check: `backend/alembic/versions/20260802_0008_trace_foundation.py`

**Interfaces:**
- Consumes: the implemented S1-S6 ORM/schema/type/lifecycle/context/usage contracts.
- Produces: one canonical documentation page for developers and later M2 consumers.

- [ ] **Step 1: Reconcile every documented field against source**

Build the document from these exact implemented groups:

```text
TraceRun
- id, run_type, status
- conversation_id, agent_run_id, user_message_id
- title, input_text, output_text
- provider, model
- total_input_tokens, total_output_tokens, total_tokens
- estimated_cost, latency_ms
- error_message, metadata_json
- started_at, ended_at, created_at

TraceStep
- id, trace_run_id, step_index
- step_type, name, status
- input_json, output_json
- error_message, latency_ms
- started_at, ended_at, created_at
```

Confirm the direct correlation FKs use `SET NULL`, composite ownership FKs use
`NO ACTION`, TraceRun deletion cascades TraceStep, step indexes are positive
and unique per run, and costs use `Numeric(18, 8)`.

- [ ] **Step 2: Write the formal document with fixed headings**

Create `docs/30-trace-observability.md` with exactly these top-level sections:

```markdown
# Trace Observability Foundation

## Current Scope
## Component Map
## TraceRun Contract
## TraceStep Contract
## Types And Statuses
## Lifecycle And Transactions
## Trace Context
## Token, Cost, And Latency Metadata
## Persistence And Deletion
## Security And Reliability Boundaries
## Verification
## Deferred To Later Plan 4 Batches
```

Required lifecycle content:

```text
create_run(pending input) -> running TraceRun
running TraceRun -> add_step -> running TraceStep
running TraceStep -> finish_step -> completed TraceStep
running TraceStep -> fail_step -> failed TraceStep
running TraceRun -> finish_run -> completed TraceRun
running TraceRun -> fail_run -> failed TraceRun
```

State that terminal methods reject non-running records, missing start times are
rejected, elapsed UTC duration is clamped to non-negative milliseconds, and
explicit errors must already be product-normalized. State that Trace Service
flushes but never commits/rolls back; the caller owns atomicity.

Required context and usage examples:

```python
with trace_context.activate():
    with trace_context.step(
        TraceStepType.LLM_CALL,
        name="Call model",
    ) as trace_step:
        trace_step.output_json = metrics.to_step_metadata()
```

```json
{
  "usage": {
    "input_tokens": 1000,
    "output_tokens": 500,
    "total_tokens": 1500,
    "estimated_cost": "0.00125000"
  },
  "latency_ms": 123
}
```

Explain that automatic context failure stores only the exception class name,
clears partial output, and re-raises the original exception. Document nested
ContextVar restoration and copied-context isolation.

- [ ] **Step 3: State current non-capabilities without speculative API**

The deferred section must explicitly say:

```text
- No Chat, RAG, Tool, or Agent runtime currently creates TraceRun/TraceStep.
- No Trace list/detail/step API exists.
- No frontend Trace Timeline exists.
- No automatic multi-step run cost aggregation or cancellation policy exists.
- Advanced retrieval candidate records, reranking, and evaluation remain later Plan 4 work.
```

Do not include planned endpoint paths or a future frontend wireframe.

- [ ] **Step 4: Run a factual keyword and diff check**

Run:

```powershell
Select-String -LiteralPath 'docs/30-trace-observability.md' -Pattern 'TraceRun','TraceStep','flush','commit','ContextVar','estimated_cost','No Trace'
git diff --check
```

Expected: every contract family is present and `git diff --check` exits zero.

- [ ] **Step 5: Review checkpoint without Git mutation**

Compare every table/enum/status/example against the source files listed above.
Do not stage or commit.

---

### Task 2: Synchronize Project Status And Architecture

**Files:**
- Modify: `docs/01-architecture.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs-plan/04-PLAN4/04-PLAN4-执行步骤表 (V1.0).md`

**Interfaces:**
- Consumes: Task 1 canonical document and completed S1-S7 scope.
- Produces: consistent English/Chinese project status and one authoritative M1 completion marker.

- [ ] **Step 1: Update architecture current stage and boundaries**

In `docs/01-architecture.md`:

```text
- record that v0.3.1 is the repaired Plan 3 baseline and Plan 4 M1 S1-S7 is complete;
- add observability/ beside rag/ and tools/ in the repository tree;
- add an observability/ row to Backend Boundaries;
- replace the stale statement that Trace Service/Context are the next M1 batch;
- describe flush-only lifecycle writes, ContextVar propagation, and JSON-safe usage metadata;
- link to docs/30-trace-observability.md;
- keep Chat/RAG/Agent runtime integration explicitly absent.
```

Do not rewrite unrelated Plan 1-3 architecture history.

- [ ] **Step 2: Update English and Chinese README symmetrically**

Replace both stale “Plan 4 has not started” statements with the exact status:

```text
Plan 4 M1 is complete through P4-M1-S7. TraceRun/TraceStep persistence,
strict lifecycle writes, request-local Trace Context, and JSON-safe token/cost/
latency metadata exist, but Chat/RAG/Agent runtime hooks, Trace API, and
Timeline UI do not yet exist.
```

Apply an accurate Chinese equivalent in `README_CN.md`. Add links to the formal
Trace document and M1 final review in both documentation indexes. Update both
roadmap lines from “foundation in progress” to “M1 foundation complete; runtime
integration deferred to M2”. Preserve all Plan 3 release facts and current
limitations.

- [ ] **Step 3: Close only S7 in the execution table**

Change Batch 3 to:

```markdown
| Batch 3 | P4-M1-S7 | 完成 Trace 基础文档和 M1 review | Codex self-review M1 | 已完成（正式 Trace 文档、全量回归、迁移生命周期与 Codex self-review 通过） |
```

Change the S7 Review cell from `Codex + Claude review` to `Codex`. Do not mark
any M2 or later batch complete and do not edit their deliverables.

- [ ] **Step 4: Check bilingual and cross-document consistency**

Run:

```powershell
Select-String -LiteralPath 'README.md','README_CN.md','docs/01-architecture.md','docs-plan/04-PLAN4/04-PLAN4-执行步骤表 (V1.0).md' -Pattern 'P4-M1-S7','M1','Trace runtime','Trace Service','Codex self-review'
git diff --check
```

Expected: no document says Plan 4 has not started, no document claims runtime
integration exists, S7 alone is newly complete, and diff check exits zero.

- [ ] **Step 5: Review checkpoint without Git mutation**

Inspect the complete documentation diff for scope, bilingual equivalence,
broken claims, and external-review language at the S7/M1 gate. Do not stage or
commit.

---

### Task 3: Verify M1 And Publish The Consolidated Codex Review

**Files:**
- Create: `docs/reviews/2026-08-02-plan4-m1-final-review.md`
- Verify: all Task 1-2 documents and all S1-S6 Trace implementation/tests.

**Interfaces:**
- Consumes: the synchronized current-fact documentation and fresh command output.
- Produces: final M1 acceptance decision, residual limitations, M2 entry gate, and manual Git handoff.

- [ ] **Step 1: Run the focused M1 backend group**

From `backend/` run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_trace_service.py tests/test_trace_context.py tests/test_trace_models.py tests/test_trace_schemas.py tests/test_trace_types.py tests/test_trace_migration.py tests/test_llm_usage.py tests/test_chat_service.py tests/test_rag_service.py -q
```

Expected: all selected tests pass; only the already-known Starlette/httpx
TestClient deprecation warning is acceptable.

- [ ] **Step 2: Run the complete backend suite safely**

Create a uniquely named directory under `[System.IO.Path]::GetTempPath()`, set
synthetic `DATABASE_URL`, `DOCUMENT_STORAGE_ROOT`, and `PYTHONPATH`, run the
complete `backend/tests` suite from that directory, and validate the resolved
cleanup target is beneath the system temp root before recursively removing it.

Expected: all tests pass with only the known TestClient warning. Never run the
full suite with the repository backend directory as the current directory and
the default user-database URL.

- [ ] **Step 3: Run dependency and temporary migration lifecycle checks**

Run `python -m pip check`. In a separate validated system-temporary directory,
set a temporary SQLite `DATABASE_URL` and `PYTHONPATH`, then run with the
repository Alembic configuration:

```powershell
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic -c F:\MyProjects\AI-Agent-Lab\backend\alembic.ini upgrade head
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic -c F:\MyProjects\AI-Agent-Lab\backend\alembic.ini current --check-heads
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic -c F:\MyProjects\AI-Agent-Lab\backend\alembic.ini check
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic -c F:\MyProjects\AI-Agent-Lab\backend\alembic.ini downgrade 20260801_0007
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic -c F:\MyProjects\AI-Agent-Lab\backend\alembic.ini upgrade head
F:\MyProjects\AI-Agent-Lab\.venv\Scripts\python.exe -m alembic -c F:\MyProjects\AI-Agent-Lab\backend\alembic.ini current --check-heads
```

Expected: head is `20260802_0008`, no autogenerate drift is reported, downgrade
and re-upgrade both succeed, and the validated temporary directory is removed.

- [ ] **Step 4: Run documentation, hygiene, and Git gates**

Validate every tracked/new Markdown link/image with
`git -c core.quotepath=false ls-files`. Scan changed text for high-confidence
private-key/credential markers. Confirm zero changed production/test files,
zero network Tool/runtime additions, zero generated/database artifacts, and no
`backend/ai_agent_lab.db` Git change.

Run:

```powershell
git diff --check
git status --short
git diff --cached --name-only
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git rev-parse 'v0.3.1^{}'
```

Expected: only the approved S7 Markdown files are modified/new, staged paths
are zero, branch/refs are unchanged, links have zero missing targets, and all
hygiene scans are clean.

- [ ] **Step 5: Write the final review from actual evidence**

Create `docs/reviews/2026-08-02-plan4-m1-final-review.md` with exactly these
top-level sections:

```markdown
# Plan 4 M1 Trace Foundation Final Review

## Decision
## Scope And Git Baseline
## S1-S7 Acceptance Matrix
## Delivered Foundation
## Fresh Verification Evidence
## Findings And Disposition
## Codex Self-Review
## M2 Entry Gate
## Git Handoff
```

Link the S1-S3 and S4-S6 reviews instead of copying every debugging log. Record
the actual focused/full/migration/link/hygiene results produced in Steps 1-4.
Include the earlier S4-S6 process incident accurately: a broad read-only
PowerShell command touched the prohibited user SQLite file, no write occurred,
and explicit whitelists replaced that method.

The M2 entry gate must conclude separately on:

```text
1. Trace ORM/schema/migration integrity
2. lifecycle Service and caller-owned transactions
3. request-local ContextVar and safe automatic failures
4. token/cost/latency metadata compatibility
5. current limitations and absence of accidental M2 runtime
```

- [ ] **Step 6: Re-run final documentation and Git checks**

After the final review exists, rerun all Markdown local-link checks,
high-confidence secret/artifact/scope scans, `git diff --check`, status, staged
paths, and refs. Correct every factual or link mismatch before completion.

- [ ] **Step 7: Perform Codex final self-review and handoff**

Classify findings as must fix, fix later, recorded limitation, or not
applicable. Confirm:

```text
- no production/test source changed;
- formal docs match source and fresh evidence;
- no current document presents M2 behavior as implemented;
- M1 review is Codex-only;
- no secret, database, generated artifact, network Tool, or unrelated path changed;
- staged paths remain zero.
```

Do not stage or commit. Suggest this manual commit message:

```text
docs(observability): complete trace foundation review
```

State whether Plan 4 M1 is closed and whether `P4-M2-S1-S3` may begin after the
user manually commits S7.
