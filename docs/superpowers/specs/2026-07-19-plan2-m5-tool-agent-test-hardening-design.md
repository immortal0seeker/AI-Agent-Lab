# Plan 2 M5 Tool / Agent Test Hardening Design

**Date:** 2026-07-19

**Scope:** `P2-M5-S1` through `P2-M5-S3` only.

## Decision

Use the existing unit and integration suites as the baseline and add only the
missing security and boundary regressions. Do not duplicate already-covered
Tool, Registry, builtin, Agent loop, or Agent API happy paths.

The batch adds four focused guarantees:

1. Tool arguments reject non-standard JSON numeric values (`NaN` and
   infinities) before Tool execution.
2. `.envrc` is treated as an environment-secret file by shared path policy,
   `read_file`, and `list_dir`.
3. `web_fetch` remains absent from module discovery, builtin exports, and the
   executable Registry.
4. The Agent API safely persists a blocked builtin ToolCall, returns its safe
   failure result, feeds the failure observation to a Mock Provider, and still
   completes with a final answer.

## Acceptance Matrix

| Plan acceptance requirement | Existing evidence | Gap | Minimal addition |
|---|---|---|---|
| Tool abstraction | `test_tool_base.py` covers async execution, immutable normalized metadata, timeout bounds, defensive schema copies, ToolError, and ToolResult invariants | No material gap | No duplicate test |
| Tool Registry | `test_tool_registry.py` and builtin registration tests cover order, lookup, duplicates, invalid schema atomicity, defensive exports, and all-or-nothing builtin registration | No material gap | No duplicate test |
| Argument validation | Missing/type/unknown/nested/multi-error/schema safety tests exist | Standard JSON excludes non-finite floats, but direct validation currently accepts them | Add non-finite argument regression and a safe `json` validation issue |
| Read-only path security | Traversal, absolute/drive/UNC, sensitive directories, credentials, keys, ADS, size, depth, symlink/junction boundaries are covered | `.envrc` is not classified as sensitive despite the documented `.env*` boundary | Add shared/read/list regressions and minimally widen the `.env` prefix rule |
| `read_file` / `list_dir` | Normal, bounded, failure, encoding, truncation, filtering, ordering, symlink/junction, and Registry behavior are covered | `.envrc` can be read/listed | Reuse the shared policy fix and strengthen both builtin suites |
| `web_fetch` | Formal deferral docs exist | No automated regression prevents accidental module/export/Registry exposure | Add an absence contract test; make no runtime or dependency change |
| Simple Agent Loop | Mock Provider + temporary SQLite/workspace tests cover direct, multi-round, ordering, failures, timeouts, limits, compaction, cancellation, and persistence | Core loop coverage is sufficient | No duplicate service-level test |
| Agent API | Temporary SQLite + Mock Provider tests cover create/query, real `read_file`, structured failure, errors, transaction rollback, and deterministic queries | No end-to-end case for a builtin security rejection becoming a safe persisted ToolCall and Provider observation | Add one API integration regression using a synthetic `.envrc` in `tmp_path` |

## Test Isolation

- Use only pytest `tmp_path` workspaces and SQLite files created under that
  temporary directory.
- Mock only the external Provider decision boundary; keep FastAPI,
  `SimpleAgentService`, Tool Registry, builtin Tool, SQLAlchemy, and response
  serialization real.
- Use synthetic secret text and assert it never appears in ToolResult,
  observations, API responses, or persisted ToolCall JSON.
- Do not read `backend/ai_agent_lab.db`, `.env`, credentials, or user files.
- Do not call a real Provider or make any network request.

## Production Changes

Only two minimal behavior corrections are allowed if the new tests fail for the
expected reasons:

- validate Tool argument payloads with standard JSON serialization
  (`allow_nan=False`) and return a fixed safe validation issue;
- classify every filename beginning with `.env` as sensitive, matching the
  documented `.env*` boundary.

No Tool, schema, Registry entry, dependency, API route, database model,
migration, Agent state, frontend behavior, or later-Plan capability is added.

## Documentation Boundary

This batch may update only the Plan 2 execution table and the two superpowers
design/plan files with literal test evidence. Release documentation, screenshots,
`v0.2.0` packaging, M5-S4 through M5-S8, and Plan 3 remain out of scope.
