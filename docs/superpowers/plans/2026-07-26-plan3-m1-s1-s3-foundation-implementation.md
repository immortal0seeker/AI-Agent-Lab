# Plan 3 M1 S1～S3 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `executing-plans` inline.
> Subagents and Git mutations are forbidden by the active handoff. Steps use
> checked task syntax for tracking.

**Goal:** Start Plan 3 from the published `v0.2.1` baseline by correcting the
handoff truth, adding reproducible Qdrant configuration, and creating only the
current RAG/Knowledge package boundaries.

**Architecture:** Keep SQLite as the business/audit database and add Qdrant as
an independent vector-storage service. Extend the existing Pydantic Settings
pattern with a non-secret URL, and establish empty Python packages that later
Steps can fill without creating those later capabilities now.

**Tech Stack:** Python 3.11, Pydantic Settings, pytest, Docker Compose, Qdrant,
FastAPI, SQLite, React 19, TypeScript 5.9.

## Global Constraints

- Work only on `P3-M1-S1～S3`; do not begin S4 or later.
- Preserve `v0.2.0` and `v0.2.1` tags/history; do not stage, commit, push, tag,
  or change branches.
- Do not read or migrate `backend/ai_agent_lab.db`.
- Do not add ORM models, schemas, migrations, services, APIs, document
  processing, Embedding, Vector Store clients, RAG Tools, or frontend RAG code.
- Do not use a real Provider, real network Tool, secret, or paid API.
- Runtime Qdrant health is conditional on local Docker availability; never
  substitute a static check for a health claim.

---

### Task 1: Lock the S2/S3 foundation contract with RED tests

**Files:**
- Modify: `backend/tests/test_config.py`
- Create: `backend/tests/test_plan3_foundation.py`

**Interfaces:**
- Consumes: `Settings`, root `docker-compose.yml`, and Python package imports.
- Produces: executable contracts for `qdrant_url`, Qdrant Compose semantics,
  and explicit `app.rag` / `app.knowledge` ownership boundaries.

- [x] **Step 1: Add the failing Settings assertions**

Extend the default Settings test and add an override test:

```python
assert settings.qdrant_url == "http://localhost:6333"


def test_settings_accepts_qdrant_url_override() -> None:
    settings = Settings(
        _env_file=None,
        QDRANT_URL="http://qdrant.internal:6333",
    )
    assert settings.qdrant_url == "http://qdrant.internal:6333"
```

- [x] **Step 2: Add the failing tracked-foundation test**

Create a repository-level test that requires the exact service contract and
package boundaries:

```python
def test_qdrant_compose_contract() -> None:
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text("utf-8")
    assert "qdrant/qdrant:v1.15.4" in compose
    assert '"6333:6333"' in compose
    assert "qdrant_data:/qdrant/storage" in compose
    assert "\n  qdrant_data:\n" in compose


@pytest.mark.parametrize(
    ("package_name", "ownership"),
    [
        ("app.knowledge", "知识库结构化元数据与编排边界。"),
        ("app.rag", "文档处理与 Naive RAG 流水线边界。"),
    ],
)
def test_plan3_packages_define_ownership(
    package_name: str,
    ownership: str,
) -> None:
    package = importlib.import_module(package_name)
    assert package.__doc__ == ownership
```

- [x] **Step 3: Run RED and confirm the expected cause**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests\test_config.py tests\test_plan3_foundation.py
```

Expected: failures report missing `Settings.qdrant_url`,
`docker-compose.yml`, `app.knowledge`, and `app.rag`.

---

### Task 2: Add the minimal Qdrant and package foundation

**Files:**
- Create: `docker-compose.yml`
- Modify: `backend/.env.example`
- Modify: `backend/app/core/config.py`
- Create: `backend/app/knowledge/__init__.py`
- Create: `backend/app/rag/__init__.py`

**Interfaces:**
- Consumes: local Docker Compose and backend environment variables.
- Produces: `Settings.qdrant_url: str` and two empty Plan 3 module boundaries.

- [x] **Step 1: Add the Qdrant setting and environment example**

Add:

```python
qdrant_url: str = Field(
    default="http://localhost:6333",
    alias="QDRANT_URL",
)
```

and:

```text
QDRANT_URL=http://localhost:6333
```

- [x] **Step 2: Add the minimal Compose service**

Create:

```yaml
name: ai-agent-lab

services:
  qdrant:
    image: qdrant/qdrant:v1.15.4
    restart: unless-stopped
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  qdrant_data:
```

- [x] **Step 3: Add only the package markers**

Each `__init__.py` contains only a short ownership docstring. Do not export a
class or create another file in either package.

- [x] **Step 4: Run GREEN**

Run the Task 1 command. Expected: all focused foundation tests pass.

---

### Task 3: Correct release truth and document conditional Qdrant acceptance

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/10-tool-calling-design.md`
- Modify: `docs/11-simple-agent-loop.md`
- Modify: `docs/12-agent-api.md`
- Modify: `docs/13-plan-2-basic-agent.md`
- Modify: `docs/reviews/2026-07-19-plan2-v0.2.0-final-review.md`
- Modify: `docs-plan/00-ALL PLAN/03-PLAN-3 (V1.0).md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify only if required by the truth scan:
  `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`

**Interfaces:**
- Consumes: verified Git targets and the local Docker capability audit.
- Produces: current documentation that distinguishes the historical `v0.2.0`
  release from the active published `v0.2.1` Plan 3 base.

- [x] **Step 1: Correct current release and Plan 3 base statements**

State that `v0.2.1` is published at `872310b`, `v0.2.0` remains at `0e3f3a6`,
Plan 2 is complete, and this batch starts only Plan 3 S1～S3.

- [x] **Step 2: Add Qdrant startup and limitation text**

Document:

```powershell
docker compose up -d qdrant
Invoke-RestMethod http://localhost:6333/healthz
```

Record the initial lack of a container runtime without fabricating health
evidence. Task 5 supersedes that limitation after Docker becomes available.

- [x] **Step 3: Run the stale-truth and boundary scans**

Use tracked-file searches to ensure no current-stage document still presents
`v0.2.1` as pending. Historical design/implementation evidence may retain its
time-scoped wording.

---

### Task 4: Verify, review, and prepare the manual handoff

**Files:**
- Modify: this plan only to mark steps complete with observed evidence.

**Interfaces:**
- Consumes: the complete working-tree diff.
- Produces: fresh verification and Codex self-review evidence.

- [x] **Step 1: Run focused Plan 2 bridge regression**

From `backend/`, run the Tool Registry, builtins, Simple Agent, Agent API,
configuration, release-version, web-fetch deferral, and Plan 3 foundation
tests with Mock Providers and temporary data only.

- [x] **Step 2: Run complete regression**

Backend:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Frontend:

```powershell
npm run test
npm run typecheck
npm run build
```

- [x] **Step 3: Verify a fresh temporary Alembic database**

Point `DATABASE_URL` only at a newly created system-temporary SQLite file.
Run `upgrade head`, `current --check-heads`, and `alembic check`, then remove
only the verified temporary directory.

- [x] **Step 4: Run repository gates**

Check Markdown links, high-confidence secret patterns, generated/database
artifacts, `web_fetch` runtime absence, later-Plan runtime absence, no real
Provider host, `git diff --check`, worktree status, and staged paths.

- [x] **Step 5: Perform Codex self-review**

Classify findings as must fix, later Step, accepted limitation, or not
applicable. Fix must-fix findings and rerun affected verification. Do not
commit. Suggested manual commit message:

```text
chore(rag): establish plan 3 qdrant foundation
```

---

### Task 5: Disable Qdrant telemetry and collect live acceptance

**Files:**
- Modify: `backend/tests/test_plan3_foundation.py`
- Modify: `docker-compose.yml`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify: this plan's observed evidence and review classification

**Interfaces:**
- Consumes: the approved local-first Qdrant service and Docker Desktop.
- Produces: a Compose contract with `QDRANT__TELEMETRY_DISABLED=true` and
  real container/HTTP health evidence.

- [x] **Step 1: Add the failing telemetry assertion**

Add to `test_qdrant_compose_contract`:

```python
assert "QDRANT__TELEMETRY_DISABLED: \"true\"" in compose
```

- [x] **Step 2: Run RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests\test_plan3_foundation.py
```

Expected: only `test_qdrant_compose_contract` fails because the telemetry
override is absent.

- [x] **Step 3: Add the minimal Compose override**

Add to the `qdrant` service:

```yaml
environment:
  QDRANT__TELEMETRY_DISABLED: "true"
```

- [x] **Step 4: Run GREEN and recreate Qdrant**

Run the focused test, `docker compose config --quiet`, and:

```powershell
docker compose up -d --force-recreate qdrant
```

- [x] **Step 5: Verify the runtime and update evidence**

Require the container to be running with zero restarts, the startup log to
report disabled telemetry, and `http://localhost:6333/healthz` to return HTTP
200. Update the execution table and this plan with only the observed facts.

## Observed Execution Evidence

- RED: `5 failed, 8 passed`; every failure came from a missing S2/S3 contract.
- GREEN: focused foundation suite `13 passed`.
- Telemetry follow-up RED: `1 failed, 2 passed`; the only failure was the
  missing Compose override. GREEN: `3 passed`, and `docker compose config
  --quiet` accepted the updated file.
- Plan 2 bridge regression: `322 passed, 1 warning`.
- Full backend: `507 passed, 1 warning`; the warning is the known
  Starlette TestClient/httpx deprecation.
- Python environment: `pip check` reported no broken requirements.
- Frontend: `18` files / `90` tests, typecheck, and production build with
  `1813` transformed modules all passed.
- Temporary SQLite: Alembic `upgrade head`, `current --check-heads`, and
  `check` passed at `20260720_0004`; the verified temporary directory was
  removed.
- Repository: `81` Markdown files, `67` local links/images, `0` missing;
  high-confidence secret, generated/database artifact, `web_fetch` runtime,
  later-Plan runtime, and real Provider host hits were all `0`.
- Git: branch remained `main`; `HEAD == origin/main == v0.2.1^{}` at
  `872310b`; `v0.2.0^{}` remained `0e3f3a6`; staged paths and
  `git diff --check` findings were `0`.
- Qdrant runtime follow-up: Docker Desktop `4.83.0`, Engine `29.6.2`, and
  Compose `5.3.1` accepted the Compose configuration. The
  `qdrant/qdrant:v1.15.4` container ran with zero restarts, its startup log
  reported `Telemetry reporting disabled`, and `/healthz` returned HTTP 200
  with `healthz check passed`.

## Codex Self-Review Classification

| Classification | Result |
|---|---|
| Must fix — fixed | Replaced a brittle “package contains only `__init__.py`” assertion with a durable import/ownership contract. After live startup exposed Qdrant's default telemetry, added an approved test-first Compose override and reverified startup and health. |
| Later Step | KnowledgeBase, Document, DocumentChunk, and RagQuery ORM/schema/migration work remains `P3-M1-S4～S6`; API, parser, Embedding, Vector Store, and RAG runtime remain in their assigned later batches. |
| Accepted limitation | Qdrant is configured as a local development service without an API key; it must not be exposed to an untrusted network. |
| Not applicable | No frontend runtime, database schema, Provider, Tool Registry, Agent state/API, Qdrant client, real network Tool, or paid Provider change was required. |

No blocking self-review finding remains. The user-selected completion path is
to keep the verified working tree on `main` for manual staging and commit; no
branch, stage, commit, push, or tag action is performed here.
