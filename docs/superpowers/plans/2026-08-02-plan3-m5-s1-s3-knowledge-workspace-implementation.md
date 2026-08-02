# Plan 3 M5 S1～S3 Knowledge Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This repository explicitly forbids subagents, branches, worktrees, staging, commits, pushes, and tags for this batch.

**Goal:** Add a typed, tested Knowledge workspace where a user can list/create Knowledge Bases, upload one supported document, and inspect the returned parse/chunk/embedding lifecycle.

**Architecture:** `KnowledgeBasePage` owns feature-local async state and composes small list/create/upload/status components. A dedicated API module mirrors the existing backend contracts. The existing workspace navigation gains a third `knowledge` view without introducing the S4～S6 RAG store or chat.

**Tech Stack:** React 19, TypeScript 5.9, Vite 7, Vitest 4, jsdom, existing FastAPI JSON/multipart contracts.

## Global Constraints

- Implement only `P3-M5-S1～S3`; do not begin S4～S6, M6, Plan 4+, RAG Chat, source cards, Advanced RAG, Rerank, Evaluation, Memory, OCR, or multimodal work.
- Do not add backend Document list/detail/chunk/retry/delete endpoints.
- Never read, migrate, delete, or recreate `backend/ai_agent_lab.db`.
- Use only mocked frontend API responses and repository test fixtures; never call a paid Provider or read a real secret.
- Keep the UI quiet, dense, responsive, and explicit about loading, empty, error, and success states.
- Do not create/switch branches or worktrees and do not stage, commit, push, or tag.

---

### Task 1: Add Knowledge Types And API Contract

**Files:**
- Create: `frontend/src/types/knowledge.ts`
- Create: `frontend/src/api/knowledge.ts`
- Create: `frontend/src/api/knowledge.test.ts`

**Interfaces:**
- `fetchKnowledgeBases(): Promise<KnowledgeBase[]>`
- `createKnowledgeBase(request: KnowledgeBaseCreate): Promise<KnowledgeBase>`
- `uploadKnowledgeDocument(knowledgeBaseId: string, file: File): Promise<KnowledgeDocument>`

- [x] **Step 1: Write API RED tests**

Cover plural list/create URLs, exact JSON creation body, encoded nested upload
URL, one `FormData` file part, no manually supplied multipart header, structured
backend errors, transport failure, and invalid successful JSON.

- [x] **Step 2: Run RED**

```powershell
npm test -- src/api/knowledge.test.ts
```

Expected: import failure because the Knowledge API module does not exist.

- [x] **Step 3: Implement minimal types and API wrapper**

Mirror the backend schemas and use a private request helper built on
`API_BASE_URL`, `createApiUrl`, and `readResponseError`.

- [x] **Step 4: Run GREEN and typecheck**

```powershell
npm test -- src/api/knowledge.test.ts
npm run typecheck
```

---

### Task 2: Add Knowledge Workspace Navigation, List, And Create

**Files:**
- Modify: `frontend/src/utils/agentUrl.ts`
- Modify: `frontend/src/utils/agentUrl.test.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/components/WorkspaceSidebar.tsx`
- Create: `frontend/src/components/knowledge/KnowledgeBaseList.tsx`
- Create: `frontend/src/components/knowledge/KnowledgeBaseCreateForm.tsx`
- Create: `frontend/src/pages/KnowledgeBasePage.tsx`
- Create: `frontend/src/pages/KnowledgeBasePage.test.tsx`

**Behavior:**
- `?workspace=knowledge` restores the third workspace;
- list loading/error/empty/ready states are explicit;
- the first loaded Knowledge Base is selected;
- creating a trimmed name/optional description selects the returned row;
- duplicate submissions are disabled and failures preserve form input.

- [x] **Step 1: Write navigation and page RED tests**

Add URL/App static tests plus mounted jsdom tests for initial list, empty/error
and retry, create request, selected result, and safe create failure.

- [x] **Step 2: Run RED**

```powershell
npm test -- src/utils/agentUrl.test.ts src/App.test.tsx src/pages/KnowledgeBasePage.test.tsx
```

Expected: missing `knowledge` workspace/page/components and failing behavior.

- [x] **Step 3: Implement minimal navigation and list/create UI**

Keep initial effects unmount-safe. Use feature-local discriminated states and
small presentational components; do not add a store or update/delete actions.

- [x] **Step 4: Run GREEN**

Run the Task 2 command again. Expected: selected tests pass.

---

### Task 3: Add Document Upload And Lifecycle Status

**Files:**
- Create: `frontend/src/components/knowledge/FileUploadPanel.tsx`
- Create: `frontend/src/components/knowledge/DocumentStatusCard.tsx`
- Modify: `frontend/src/pages/KnowledgeBasePage.tsx`
- Modify: `frontend/src/pages/KnowledgeBasePage.test.tsx`

**Behavior:**
- accept `.md`, `.txt`, and `.pdf` filenames case-insensitively;
- submit exactly one File to the selected Knowledge Base;
- show upload busy/error state;
- treat HTTP 201 processing failures as returned resources;
- display exact parse/chunk/embedding states without paths or hashes;
- clear the returned Document when selecting another Knowledge Base.

- [x] **Step 1: Write upload/status RED tests**

Cover missing/unsupported input, supported multipart call, disabled conflict
controls, all three returned lifecycle fields, safe errors, processing-failure
resource rendering, and selected-owner reset.

- [x] **Step 2: Run RED**

```powershell
npm test -- src/pages/KnowledgeBasePage.test.tsx
```

Expected: upload controls and lifecycle status are absent.

- [x] **Step 3: Implement minimal upload/status GREEN**

Use `FileUploadPanel` and `DocumentStatusCard`. Do not poll or expose backend
file paths, hashes, raw metadata, or internal diagnostics.

- [x] **Step 4: Run GREEN**

Run the Task 3 command again. Expected: all page tests pass.

---

### Task 4: Add Responsive Styling And Accessibility Regression

**Files:**
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/pages/KnowledgeBasePage.test.tsx`

- [x] **Step 1: Add failing semantic assertions**

Assert labelled navigation/forms, selected list item, status announcements,
alerts, and disabled controls. Preserve mobile navigation labels.

- [x] **Step 2: Implement layout and semantic GREEN**

Add the three-column desktop navigation, two-column Knowledge content, status
badges, clear focus states for inputs, and a single-column mobile layout.

- [x] **Step 3: Run focused frontend GREEN**

```powershell
npm test -- src/api/knowledge.test.ts src/utils/agentUrl.test.ts src/App.test.tsx src/pages/KnowledgeBasePage.test.tsx
npm run typecheck
```

---

### Task 5: Synchronize Documentation And Acceptance Evidence

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/20-knowledge-base-design.md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify: this plan after every completed TDD checkpoint

- [x] **Step 1: Update current behavior and limitation text**

Document the Knowledge workspace, exact list/create/upload/status behavior, and
the absence of persistent Document list/detail/Chunk preview/retry/delete APIs.
Keep RAG Chat/source UI explicitly deferred to S4～S6.

- [x] **Step 2: Run complete verification**

```powershell
npm test
npm run typecheck
npm run build
```

Run the full backend pytest suite from `backend/`, dependency integrity, docs
link checks, `git diff --check`, staged-path/status checks, secret scan, artifact
scan, and Plan-boundary scan. Use only temporary fixtures and never the protected
user database.

- [x] **Step 3: Run local mocked browser smoke**

Verify desktop and narrow viewport flows with intercepted local API responses:
open Knowledge, observe list, create a Knowledge Base, upload a supported file,
and inspect the returned lifecycle. Do not use a real Provider or user DB.

- [x] **Step 4: Codex self-review and final evidence refresh**

Classify findings as must-fix, later batch, recorded limitation, or not
applicable. Re-run affected checks after every must-fix. Confirm the diff stays
within S1～S3 and remains ready for the user's manual commit.
