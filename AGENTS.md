# AGENTS.md

This file defines the root collaboration rules for AI Agent Lab / AI Engineering Workspace. It applies to the entire repository. Deeper `AGENTS.md` files may add local rules for specific directories.

The root file should contain only cross-module hard rules. Module-specific details belong in subdirectory `AGENTS.md` files.

---

## 1. Project Goal

The project progresses through 6 plans:

- Plan 1: Project foundation + Basic Chat + LLM Providers
- Plan 2: Tool Calling + Simple Agent Loop
- Plan 3: Knowledge Base + Document Ingestion + Naive RAG
- Plan 4: Trace + Advanced RAG + Rerank + Evaluation
- Plan 5: Memory + Context Engine + Agent Runtime + Human Approval
- Plan 6: MCP + Voice + Vision + Desktop

The goal is not to pile up demos. The goal is to build an AI Engineering Workspace that is observable, evaluable, extensible, and useful for daily work.

---

## 2. Execution Workflow

By default, follow this fixed small loop:

1. Take only 1-3 consecutive Steps at a time.
   - Work only within the user-specified Step range.
   - Do not implement capabilities from later Plans early.
2. Implement with Codex / Cursor.
   - Implement the deliverables for the current Step.
   - Keep the diff scope clean.
   - Use Chinese for necessary code comments.
3. Run the matching verification.
   - Backend: unit tests, API tests, startup checks, or endpoint checks.
   - Frontend: TypeScript checks, build checks, page smoke checks, or manual checks.
   - Docs/config: check links, paths, secrets, and `git status`.
4. Run Codex self-review.
   - Check whether the diff only covers the current Step batch.
   - Check whether the work crosses Plan boundaries.
   - Check for secret leakage.
   - Check whether verification evidence is sufficient.
   - Check whether README / docs / env examples need updates.
   - Clearly tell the user whether this batch needs Claude Code secondary review.
5. Decide on Claude Code secondary review.
   - If Claude Code review is not needed, continue to fixes and re-verification.
   - If Claude Code review is needed, pause before entering the next Step batch and wait for review results.
6. Fix review feedback.
   - Must fix: fix in the current batch.
   - Fix later: record for a later Step or limitation note.
   - Record as limitation: write it in docs / README / review notes.
   - Not applicable: explain why.
7. Re-run verification.
   - After fixes, repeat verification.
   - If issues remain, repeat steps 4-7.
   - Continue until tests, verification, and Codex self-review have no blocking issues.
8. Finish the batch.
   - Provide a change summary.
   - Provide verification results.
   - Provide the Codex review conclusion.
   - State whether Claude Code review is needed.
   - List residual risks or limitations.
   - Suggest the next Step batch.
   - Provide a suggested commit message, but the user creates the actual commit manually unless explicitly requested otherwise.

When the user specifies a range such as `P1-M1-S1～P1-M1-S3`, only work on that range.

---

## 3. Plan Boundaries

Do not implement capabilities from later plans early.

- Plan 1 does not implement Tool Calling, RAG, Memory, MCP, Voice, Vision, or Desktop.
- Plan 2 does not implement RAG, Embedding, Memory, MCP, Shell Tool, or file-writing tools.
- Plan 3 does not implement Advanced RAG, Rerank, Evaluation, Memory, OCR, or multimodal capabilities.
- Plan 4 does not implement Memory, Agent Runtime v2, Planner, Human Approval, MCP, or multimodal capabilities.
- Plan 5 does not implement MCP, Voice, Vision, Desktop, Multi-Agent, Browser Use, or Computer Use.
- Plan 6 does not implement Multi-Agent, A2A, Browser Use, Computer Use, plugin marketplace, or mobile.

If a later-plan capability appears necessary, record it as a bridge item instead of implementing it directly.

---

## 4. Architecture Principles

Prefer small modules, clear boundaries, and independent testability.

Every important module should be able to answer: what it owns, what it depends on, what it outputs, who calls it, and how it is tested.

Keep API routes thin: `Route -> schema validation -> service -> response schema`.

Business logic belongs in services, not routes. Provider details belong in provider adapters and must not leak into the business layer.

Do not create future directories before the current plan reaches them.

Code comments should be written in Chinese by default because this is a learning-oriented project. Add comments only when they clarify non-obvious intent, boundaries, trade-offs, or learning points; do not translate self-explanatory code into comments.

---

## 5. Expected Directory Structure

The repository will gradually form:

- `backend/`
- `frontend/`
- `desktop/`
- `docs/`
- `scripts/`
- `tests/`
- `README.md`
- `CHANGELOG.md`
- `AGENTS.md`

The backend will gradually form: `api/`, `core/`, `db/`, `models/`, `schemas/`, `providers/`, `tools/`, `rag/`, `observability/`, `memory/`, `context_engine/`, `agents/`, `mcp/`, `voice/`, `multimodal/`, `desktop/`.

---

## 6. Backend Rules

Use FastAPI.

Database, schemas, services, APIs, and tests must evolve together.

When changing database fields, update the ORM model, migration, Pydantic schema, service tests, and API tests at the same time. If the change is user-visible, update docs as well.

LLM / Embedding / Rerank / STT / TTS / OCR / Vision / MCP Provider failures must not crash the service. Return errors that are readable, testable, and traceable.

---

## 7. Frontend Rules

Use React + TypeScript.

- `frontend/src/api/`: API wrappers.
- `frontend/src/types/`: shared types.
- `frontend/src/pages/`: pages.
- `frontend/src/components/`: feature components.

This is an engineering workspace, not a marketing page. The UI should be quiet, dense, and easy to scan.

Async flows must have loading, empty, error, and success/result states.

Trace, Tool Call, Approval, and Agent Run pages must preserve traceable IDs.

---

## 8. Testing Rules

Each Step batch must be verified before commit.

Prefer mocks and do not depend on real paid APIs. LLM, Embedding, Rerank, STT, TTS, OCR, Vision, and MCP should all support mock testing.

Backend coverage should include pure logic unit tests, service state tests, API tests, and error-path tests.

Frontend coverage should include at least TypeScript checks, page smoke/manual checks, and screenshots or notes for critical flows.

Do not claim completion without fresh verification results.

---

## 9. Review Rules

Run Codex review after each Step batch.

Prioritize Claude Code secondary review for: database models, Provider abstractions, RAG / ranking, Trace / Evaluation, Memory write strategy, Context Engine, Agent Runtime state machine, Human Approval, MCP Permission, Desktop local file permissions, and release candidates.

Review feedback must be classified as: must fix, fix in later batch, record as limitation, or not applicable with explanation.

After fixes, verify again.

---

## 10. Security Rules

Real secrets must not be committed.

Do not write real values into `.env.example`, README, docs, tests, fixtures, screenshots, Trace, logs, frontend state, or seed data.

API keys, tokens, MCP env secrets, and Provider credentials may only be passed through local untracked `.env` files, environment variables, secret references, or local encrypted configuration.

Do not store secrets in plaintext, write them to logs, or expose them in frontend responses. UI display must be masked.

---

## 11. Tools And Local Permissions

Default to read-only.

Writing files, deleting files, running commands, external paid APIs, high-risk MCP, and access to local sensitive paths all require risk judgment.

Once Human Approval is available, high-risk actions must require approval.

`retry` must not bypass approval. `resume` must not bypass approval. MCP tool calls must not bypass permission policy. Local file access must not bypass `trusted_paths`.

Path traversal is forbidden. Reading `.env`, SSH keys, browser profiles, or system credential stores is forbidden.

---

## 12. Agent Runtime Rules

Agent execution must be replayable.

Important records include `agent_run`, `agent_step`, `tool_call`, `approval_request`, `trace_run`, `trace_step`, and cost / latency metadata.

State machine changes must be tested. Do not casually add runtime states.

When adding a new state, update enum, transition rules, schema, API, frontend badge, tests, and docs together.

Human Approval is a security boundary, not a normal UI.

---

## 13. RAG And Evaluation Rules

RAG must preserve source metadata.

Answers should be traceable: which knowledge base was retrieved, which documents / chunks matched, which retrieval strategy was used, which sources were selected, and which `trace_run` it corresponds to.

Evaluation must be reproducible. Do not judge retrieval quality by human intuition alone.

---

## 14. Documentation Rules

When user-visible or operations-visible behavior changes, update relevant documentation: README, CHANGELOG, docs, `.env.example`, active plan notes, screenshots, or manual verification notes.

Documentation must not claim unimplemented capabilities. Deferred capabilities should be clearly recorded as limitations.

Documentation directory boundaries:

- `docs-plan/`: source planning documents, including the overall roadmap, each Plan, execution step tables, and acceptance criteria. Must be committed and must not be added to `.gitignore`.
- `docs/`: formal project documentation, including implemented or currently scoped architecture, APIs, startup instructions, acceptance screenshots, and retrospective material. Must be committed and must not be added to `.gitignore`.
- `docs-local/`: local drafts, unsanitized material, temporary reviews, debugging notes, private screenshots, and sensitive context. Must be added to `.gitignore` and must not be committed.

If content from `docs-local/` should become a project asset, sanitize and organize it first, then move it to the appropriate place under `docs/` or `docs-plan/`.

---

## 15. Commit Rules

Prepare commits by verified batch, not by small scattered edits. The user creates commits manually unless explicitly asking Codex to commit.

Before suggesting a commit, check: whether the diff only covers the current Step batch, whether tests passed, whether secrets were accidentally included, whether docs were updated, and whether unrelated files were modified.

Example commit messages:

- `feat(chat): add streaming message persistence`
- `fix(provider): normalize timeout errors`
- `test(rag): cover chunk metadata filtering`
- `docs(plan1): record v0.1.0 setup flow`
- `chore(release): tag v0.1.0`

---

## 16. Subdirectory AGENTS.md Strategy

Second-level `AGENTS.md` files are recommended for: `backend/`, `frontend/`, `docs/`, `desktop/`, `backend/app/providers/`, `backend/app/tools/`, `backend/app/rag/`, `backend/app/observability/`, `backend/app/memory/`, `backend/app/context_engine/`, `backend/app/agents/`, `backend/app/mcp/`, `backend/app/voice/`, `backend/app/multimodal/`.

Third-level files should be used only for high-risk modules: `backend/app/agents/runtime/`, `backend/app/agents/approval/`, `backend/app/rag/strategies/`, `backend/app/providers/*/`, `backend/app/desktop/`.

Do not write fourth-level `AGENTS.md` files unless the user explicitly asks for them.

---

## 17. Stop Conditions

Stop first when encountering: conflict between Step and plan, missing decisions, repeated test failures, unclear security boundary, accidental crossing into a later Plan, destructive operations, need for real external credentials, or unrelated changes affecting the current task.

Do not guess your way past security boundaries.

---

## 18. Definition Of Done

A batch is complete only when: the specified Steps are implemented, related tests or verification passed, review issues are handled or classified, required docs are updated, no secrets are leaked, the diff scope is clean, and the work is ready for the user's manual commit.

A Plan is complete only when: all milestone acceptance checks pass, full review is complete, docs and CHANGELOG are updated, the version tag is created, and the bridge check for the next Plan passes.
