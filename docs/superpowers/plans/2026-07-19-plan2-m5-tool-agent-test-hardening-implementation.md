# Plan 2 M5 Tool / Agent Test Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan inline. Subagents are forbidden by the active user constraint. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `P2-M5-S1` through `P2-M5-S3` with minimal high-value Tool, builtin deferral, Simple Agent, and Agent API regression coverage.

**Architecture:** Extend the existing pytest suites and keep all real local layers below the Mock Provider boundary. Make only the two security/validation corrections proved necessary by failing tests; preserve the explicit absence of `web_fetch`.

**Tech Stack:** Python 3.11, pytest 9, FastAPI TestClient, Pydantic, JSON Schema Draft 2020-12, SQLAlchemy 2, temporary SQLite, temporary workspaces.

## Global Constraints

- Scope is exactly `P2-M5-S1` through `P2-M5-S3`.
- Do not start M5-S4 through M5-S8 or Plan 3.
- Do not implement or expose `web_fetch`; do not add a network dependency.
- Do not use a real Provider, real network request, real `.env`, credential,
  user SQLite database, or `backend/ai_agent_lab.db`.
- Use Mock Providers, pytest `tmp_path`, and new temporary SQLite files only.
- Do not add a migration, Agent state, route, frontend behavior, RAG, Memory,
  MCP, Shell Tool, or file-writing Tool.
- Do not stage, commit, push, tag, or change branches.
- The user performs all Git mutations manually.

---

### Task 1: Add The Missing Regressions First

**Files:**
- Modify: `backend/tests/test_tool_validation.py`
- Modify: `backend/tests/test_tool_security.py`
- Modify: `backend/tests/test_tool_read_file.py`
- Modify: `backend/tests/test_tool_list_dir.py`
- Create: `backend/tests/test_web_fetch_deferral.py`
- Modify: `backend/tests/test_agent_api.py`

**Interfaces:**
- Consumes: `validate_tool_arguments()`, shared sensitive-path policy,
  `register_builtin_tools()`, and plural Agent Run API routes.
- Produces: regressions for standard JSON arguments, `.envrc`, deferred
  `web_fetch`, and the blocked-Tool Agent API flow.

- [x] **Step 1: Add a non-finite Tool argument regression**

Add a number-schema test parameterized with `NaN`, positive infinity, and
negative infinity. It must expect `ToolArgumentValidationError`, one root issue
with code `json`, and a fixed message that does not contain the rejected value.

- [x] **Step 2: Add `.envrc` to shared and builtin security cases**

Add `.envrc` to the shared sensitive-component test, `read_file` unsafe-path
test, `list_dir` unsafe-root test, and the list filtering fixture. The synthetic
file content must never appear in a serialized result.

- [x] **Step 3: Add the `web_fetch` absence contract**

Create a test that asserts:

```python
importlib.util.find_spec("app.tools.builtin.web_fetch") is None
"WebFetchTool" not in app.tools.builtin.__all__
"web_fetch" not in app.tools.builtin.__all__
```

Then register builtins into a caller-owned Registry rooted at `tmp_path` and
assert both Tool names and exported function-schema names are exactly
`["read_file", "list_dir"]`.

- [x] **Step 4: Add the Agent API blocked-Tool integration regression**

Use the existing temporary API fixture and a complete Mock Provider. On its
first decision, request `read_file({"path": ".envrc"})`; on its second decision,
return final text. Assert HTTP 201 completed, one failed ToolCall with only the
fixed safe path error, a matching safe Tool observation, durable ToolCall
persistence, and no synthetic secret or absolute temporary path in any output.

- [x] **Step 5: Run RED verification**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests\test_tool_validation.py tests\test_tool_security.py tests\test_tool_read_file.py tests\test_tool_list_dir.py tests\test_web_fetch_deferral.py tests\test_agent_api.py
```

Expected: failures only for non-finite arguments and `.envrc` being accepted or
listed. The `web_fetch` absence assertions should already pass because no
implementation is permitted.

---

### Task 2: Apply The Minimal Validation And Security Fixes

**Files:**
- Modify: `backend/app/tools/validation.py`
- Modify: `backend/app/tools/security.py`

**Interfaces:**
- Consumes: Tool argument mappings and path components.
- Produces: standard-JSON validated argument copies and `.env*` rejection.

- [x] **Step 1: Reject non-standard JSON argument values safely**

After the defensive argument copy and before Draft 2020-12 validation, serialize
with `json.dumps(payload, allow_nan=False)`. Convert `TypeError` or `ValueError`
to `ToolArgumentValidationError` with a root `ToolValidationIssue` whose code is
`json` and whose message is `arguments must contain only standard JSON values`.

- [x] **Step 2: Match the documented `.env*` security policy**

In `is_sensitive_path_component()`, replace the two narrow `.env` checks with
one `normalized.startswith(".env")` check. Do not broaden unrelated credential
or dotfile policy; `.gitignore` and non-secret names remain allowed.

- [x] **Step 3: Run GREEN verification**

Run the Task 1 focused command. Expected: all selected tests pass with only the
known Starlette TestClient/httpx deprecation warning.

- [x] **Step 4: Run the complete Tool/Agent focused suite**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests\test_tool_base.py tests\test_tool_registry.py tests\test_tool_validation.py tests\test_tool_security.py tests\test_tool_read_file.py tests\test_tool_list_dir.py tests\test_web_fetch_deferral.py tests\test_simple_agent.py tests\test_agent_service.py tests\test_agent_api.py
```

Expected: all tests pass; no real Provider, network, secret, or user database is
used.

---

### Task 3: Record Evidence, Verify, And Self-Review

**Files:**
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`
- Modify: `docs/superpowers/plans/2026-07-19-plan2-m5-tool-agent-test-hardening-implementation.md`

**Interfaces:**
- Consumes: fresh focused/full verification and the complete Git diff.
- Produces: literal M5-S1 through S3 acceptance evidence and a clean handoff to
  M5-S4 through S6.

- [x] **Step 1: Load `verification-before-completion` before success claims**

Read that skill completely and use fresh command output only.

- [x] **Step 2: Run complete backend and dependency verification**

From `backend/` run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

- [x] **Step 3: Run complete frontend regression verification**

From `frontend/` run:

```powershell
npm run typecheck
npm run test
npm run build
```

- [x] **Step 4: Run temporary SQLite Alembic and boundary checks**

Create only a new system-temporary SQLite path, run `alembic upgrade head`,
`current --check-heads`, and `alembic check`, then remove only that temporary
file/directory. Verify no `web_fetch.py`, module/export/Registry surface, new
dependency, real Provider host use, user database change, later-Plan capability,
tracked generated artifact, or staged path exists.

- [x] **Step 5: Check documentation links, secrets, and diff hygiene**

Check all repository Markdown local links, changed-file secret patterns,
generated files, `git diff --check`, cached diff check, status, HEAD,
`origin/main`, and staged paths. Do not open ignored sensitive paths.

- [x] **Step 6: Run Codex self-review and classify findings**

Classify every finding as must fix, later Step, accepted limitation, or not
applicable. Fix all must-fix findings with a failing regression first and rerun
the affected focused and full verification.

- [x] **Step 7: Update literal acceptance evidence without Git mutation**

Mark only Batch 12 and P2-M5-S1 through S3 complete. Record actual test counts,
the `.envrc` and standard-JSON fixes, the `web_fetch` absence proof, Agent API
integration evidence, Codex self-review conclusion, remaining limitations, and
next batch P2-M5-S4 through S6. Do not commit.

Suggested manual commit message:

```text
test(agent): harden plan 2 tool and agent coverage
```
