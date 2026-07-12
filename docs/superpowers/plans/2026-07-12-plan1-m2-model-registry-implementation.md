# Plan 1 M2 Model Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `P1-M2-S7` through `P1-M2-S8` with a dependency-free JSON Model Registry, strict metadata validation, complete M2 tests, and Provider documentation.

**Architecture:** `registry.py` owns Pydantic model metadata, JSON loading, uniqueness, filtering, and lookup. A tracked `models.json` provides honest example configuration, while future APIs consume the Registry without owning parsing or validation.

**Tech Stack:** Python 3.11 standard-library JSON and pathlib, Pydantic 2, pytest 9.

## Global Constraints

- Work only on `P1-M2-S7` through `P1-M2-S8`.
- Do not add Chat services, API routes, frontend model selection, persistence behavior, Tool Calling, JSON-mode requests, RAG, Memory, MCP, Voice, Vision, or Desktop behavior.
- Do not add PyYAML or any other dependency.
- Capability labels describe features implemented by this workspace.
- Prices remain optional and must not contain invented or stale values.
- Do not read a real `.env` or invoke a real Provider.
- The user creates the Git commit manually.

---

### Task 1: JSON Model Registry

**Files:**
- Create: `backend/app/providers/llm/models.json`
- Create: `backend/app/providers/llm/registry.py`
- Modify: `backend/app/providers/llm/__init__.py`
- Create: `backend/tests/test_llm_model_registry.py`

**Interfaces:**
- Produces: `ModelInfo`, `ModelRegistryError`, `ModelRegistry`, `DEFAULT_MODEL_CONFIG_PATH`, and `load_default_registry()`.

- [ ] **Step 1: Write failing list and lookup tests**

Import `load_default_registry()`, assert the example model can be listed, filtered by provider, and looked up by `(provider, model)`, and assert a missing identity returns `None`.

- [ ] **Step 2: Verify RED**

Run from `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_model_registry.py -q
```

Expected: collection fails because `app.providers.llm.registry` does not exist.

- [ ] **Step 3: Implement the minimal Registry**

Define strict `ModelInfo` and Registry-file Pydantic models, parse JSON with `json.loads()`, reject duplicates, preserve order, return defensive list copies, and expose exact lookup.

- [ ] **Step 4: Verify list and lookup GREEN**

Run the focused test file and expect the initial Registry tests to pass.

- [ ] **Step 5: Write failing configuration-error tests**

Use temporary files for malformed JSON, an unknown field, a negative price, and duplicate `(provider, model)` entries. Assert each raises `ModelRegistryError` with a readable category.

- [ ] **Step 6: Verify error-path RED**

Run the error tests and confirm they fail because validation/error translation is missing or incomplete.

- [ ] **Step 7: Implement strict validation and error translation**

Use `ConfigDict(extra="forbid")`, non-empty string constraints, non-negative optional `Decimal` prices, and chained `ModelRegistryError` exceptions.

- [ ] **Step 8: Verify Registry GREEN**

Run Registry tests and then the full backend suite.

---

### Task 2: Provider Documentation And M2 Completion

**Files:**
- Create: `docs/03-llm-provider.md`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`

**Interfaces:**
- Consumes: the Batch 4 database foundation, Batch 5 Provider layer, and Task 1 Registry.
- Produces: accurate M2 operational documentation and completion status.

- [ ] **Step 1: Complete the Provider guide**

Document the Provider contract, OpenAI-compatible configuration, Registry JSON fields, capability semantics, safe API-key handling, mock-test commands, and deferred API/UI behavior.

- [ ] **Step 2: Synchronize milestone status**

Mark Batch 6 and M2 complete, change the next scope to `P1-M3-S1` through `P1-M3-S3`, and avoid claiming real Provider calls or Chat behavior.

- [ ] **Step 3: Run full verification**

Run backend pytest, frontend typecheck/test/build, backend and frontend startup smoke checks, `pip check`, `git diff --check`, `git status --short`, and credential/generated-artifact scans.

- [ ] **Step 4: Complete M2 review**

Review S1-S8 coverage, Plan boundaries, secrets, tests, docs, migration/Registry consistency, and deferred limitations. Prepare one focused external-review prompt for the M2 milestone; do not invoke repeated per-batch Fable 5 reviews.
