# Plan 3 M1 S1～S3 Foundation Design

## Scope

This batch starts Plan 3 from the published `v0.2.1` patch baseline and covers
only:

1. revalidating the Plan 2 release and Plan 3 bridge facts;
2. adding local Qdrant service configuration and backend environment settings;
3. creating the current RAG and Knowledge package boundaries.

It does not create Knowledge Base ORM models, schemas, migrations, services,
APIs, parsers, chunkers, Embedding or Vector Store adapters, RAG Tools, or
frontend RAG code. Those remain `P3-M1-S4` or later.

## Baseline

The read-only Git gate on 2026-07-26 established:

- branch: `main`;
- `HEAD == origin/main == 872310b4dc1b78e2a2487303699d68ec8b22f88b`;
- annotated `v0.2.1^{}` resolves to the current HEAD;
- annotated `v0.2.0^{}` remains at
  `0e3f3a66e1322c565f2056696f7e482cedbb5f6c`;
- worktree and staged paths are empty;
- `git diff --check` has no finding.

The published `v0.2.0` release remains historical and immutable. Plan 3 starts
from the newer published `v0.2.1` patch and must not downgrade release truth to
`v0.2.0`.

## Acceptance Matrix

| Step | Acceptance requirement | Current evidence | Gap | Minimal delivery and verification |
|---|---|---|---|---|
| `P3-M1-S1` | Plan 2 foundation and bridge are stable; current release facts are accurate | Plan 2 final review records 503 backend tests, 90 frontend tests, Alembic head `20260720_0004`, and all five bridge contracts; current Git targets match the handoff | Current-stage docs still describe `v0.2.1` as an uncommitted candidate, and Plan 3 source docs still use `v0.2.0` as the active baseline | Correct only current/release/Plan 3 handoff facts, retain historical evidence, then rerun focused bridge tests and full regression |
| `P3-M1-S2` | Qdrant has reproducible local service and backend environment configuration | SQLite-first Settings and service-specific `.env.example` patterns already exist | No Compose file, no `QDRANT_URL`, no local container runtime, no listener on 6333 | Add a pinned Qdrant service, named volume, port 6333, `QDRANT_URL`, focused configuration tests, and startup/health instructions; report runtime health as blocked rather than fabricate it |
| `P3-M1-S3` | Current RAG and Knowledge module ownership is explicit | The Plan 3 execution table names `backend/app/rag/` and `backend/app/knowledge/` as the S3 boundary | Neither package exists | Add only package markers with boundary docstrings and an import/boundary regression; do not add later-Step modules |

## Considered Approaches

### 1. Minimal tracked foundation — selected

Add one root Compose file containing only Qdrant, add one backend setting and
environment example, create only `app.rag` and `app.knowledge`, and protect the
configuration/package boundary with focused tests. This matches S1～S3 and
keeps SQLite as the business and audit database.

### 2. Compose the complete application stack — rejected

Adding backend/frontend services, networks, build files, and application
container settings would exceed the Qdrant-only S2 requirement and change
deployment behavior before a dedicated Step approves it.

### 3. Add Qdrant client and application health integration — rejected

Installing the client, constructing a Vector Store, or adding a backend health
dependency belongs to the later Embedding/Vector Store work. It would also
misrepresent runtime health before a container runtime is available.

## Configuration Design

The root `docker-compose.yml` owns one `qdrant` service:

- image `qdrant/qdrant:v1.15.4`;
- host/container mapping `6333:6333`;
- named volume `qdrant_data:/qdrant/storage`;
- environment override `QDRANT__TELEMETRY_DISABLED=true`;
- restart policy `unless-stopped`.

The backend remains host-run and therefore defaults
`QDRANT_URL=http://localhost:6333`. No credential is required or introduced.
Qdrant stores only Plan 3 vector data; SQLite remains the primary database for
business and audit records. The telemetry override preserves the workspace's
local-first boundary without adding a custom Qdrant configuration file.

The runtime acceptance command is:

```powershell
docker compose up -d qdrant
Invoke-RestMethod http://localhost:6333/healthz
```

The initial handoff recorded this command as conditional. After Docker Desktop
became available on 2026-07-26, the pinned container was started and the
endpoint returned HTTP 200 with `healthz check passed`.

## Package Boundary Design

`app.knowledge` owns future structured knowledge metadata and orchestration
boundaries. `app.rag` owns future document-processing and Naive RAG pipeline
components. In this batch both packages contain only `__init__.py`; no
implementation surface is exported.

## Test Strategy

The RED test first requires:

- default and overridden `QDRANT_URL`;
- a Compose file with the pinned image, required port, storage mount, named
  volume, and telemetry disabled;
- importable `app.knowledge` and `app.rag` packages with explicit ownership.

The test must fail because these settings/files/packages do not yet exist.
Minimal GREEN then adds only the specified configuration and package markers.
The diff/Plan-boundary gate, rather than a brittle permanent file-count test,
proves that no later-Step module was added. Plan 2 focused bridge tests run
next, followed by the complete backend and frontend regression gates.

## Self-Review

- Placeholder scan: no placeholder or unspecified delivery remains.
- Consistency: the active base is `v0.2.1`; `v0.2.0` is preserved only as the
  original Plan 2 release.
- Scope: all code/config changes belong to S2 or S3; S1 changes release and
  bridge documentation only.
- Security: no `.env`, key, token, Provider call, user database read, or real
  network Tool is required.
