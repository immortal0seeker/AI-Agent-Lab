# Plan 2 M2 web_fetch Deferral Design

**Date:** 2026-07-18

**Scope:** `P2-M2-S7` only.

## Decision

Evaluate `web_fetch` and defer it instead of implementing a partial network
Tool in Plan 2. This is an accepted completion path in both the Plan 2 source
document and execution table.

Plan 2 M2 closes with the implemented read-only builtin set:

1. `read_file`
2. `list_dir`

The next implementation batch is `P2-M3-S1` through `P2-M3-S3`, which extends
the LLM Provider contract for Tool Calling. No `web_fetch` schema or executable
capability is exposed to that work.

## Rationale

A trustworthy `web_fetch` implementation is not only an HTTP GET wrapper. Its
minimum security and reliability boundary includes:

- allowlisted schemes and explicit port policy;
- hostname syntax and credential rejection;
- DNS resolution and public-address validation;
- protection against loopback, private, link-local, reserved, and other
  non-public targets;
- revalidation after every redirect;
- a DNS-rebinding-resistant connection strategy;
- strict connect/read/total timeouts;
- a streamed response-size limit rather than an unbounded body read;
- content-type and decoding policy;
- safe HTML-to-text extraction and output truncation;
- fixed errors without response-body, URL credential, or internal-network
  detail leakage;
- mock coverage for redirects, DNS/address decisions, timeouts, oversized
  bodies, unsupported content, and request failures.

Implementing only part of that boundary would create a misleading "low-risk"
Tool and distract from Plan 2's core learning path: Provider Tool Calling and a
Simple Agent Loop. The repository already has the two read-only local Tools
required by the Plan 2 minimum scope.

## Deferral Target

The feature remains a candidate for reassessment in Plan 4 or Plan 6, matching
the existing roadmap language. Reassessment is a design decision, not a promise
that either Plan must implement it.

Before future implementation, the active Plan must define the complete network
permission model, redirect and address-validation strategy, response-extraction
contract, observability requirements, and mock acceptance suite. A future Step
may choose a more suitable retrieval or browser boundary instead of reviving
this exact Tool shape.

## Repository Changes

This Step is documentation-only.

Update:

- `README.md` and `README_CN.md`;
- `docs/00-project-overview.md`;
- `docs/01-architecture.md`;
- `docs/10-tool-calling-design.md`;
- `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`.

The documentation must state:

- `P2-M2-S7` was evaluated and completed by explicit deferral;
- Plan 2 M2 is complete with `read_file` and `list_dir`;
- `web_fetch` is not implemented, registered, or exposed;
- the next batch is `P2-M3-S1` through `P2-M3-S3`;
- Provider tool calling and the Agent Loop remain unimplemented at this point.

Do not modify `CHANGELOG.md`; it contains released `v0.1.0` history and has no
Unreleased section. Do not create `web_fetch.py`, network-security helpers,
tests for nonexistent behavior, placeholder Registry entries, dependencies,
configuration, APIs, or frontend UI.

## Verification

Close the M2 review with fresh evidence:

- complete backend pytest and `pip check`;
- frontend typecheck, complete Vitest, and production build;
- all repository-local Markdown links resolve;
- changed files contain no secret-like values;
- no tracked or Git-visible generated artifacts are introduced;
- `git diff --check` and cached diff check pass;
- no `web_fetch.py`, `WebFetchTool`, `web_fetch` Registry entry, network helper,
  or new dependency exists;
- the diff contains no Provider tools, Agent Loop, service/API/frontend Agent
  work, or later-Plan capability.

Tests and verification must not make a real network request, resolve a live
hostname for feature testing, call a real Provider, read real secrets, or touch
the user's SQLite database.

## Acceptance Record

Mark only Batch 6 and `P2-M2-S7` complete. Add a dated S7 decision record with:

- the accepted deferral and rationale;
- explicit confirmation that no executable `web_fetch` surface exists;
- fresh backend/frontend and documentation verification evidence;
- Codex M2 self-review conclusion;
- the remaining boundary and reassessment target;
- next batch `P2-M3-S1` through `P2-M3-S3`.

Do not invent Claude Code or other external review evidence. The user performs
any Git commit manually.
