# Plan 1 M2 Database Foundation Design

## Scope

This design covers only `P1-M2-S1` through `P1-M2-S3`:

- SQLAlchemy engine, session, declarative base, and Alembic configuration
- `Conversation`, `Message`, and `LLMCall` ORM models
- conversation, message, and LLM call Pydantic schemas
- focused database, migration, ORM, relationship, and schema tests

Provider implementations, services, API routes, Chat, Streaming, and frontend work are outside this batch.

## Architecture

The database layer follows these ownership boundaries:

- `app/db/base.py` owns the SQLAlchemy declarative base and schema-object naming convention.
- `app/db/session.py` owns engine and session creation from `DATABASE_URL`.
- `app/models/` owns persistence models and relationships.
- `app/schemas/` owns validated create and read contracts.
- `alembic/` owns schema migrations and imports model metadata at its boundary.

The dependency direction is:

```text
Settings -> DB engine/session
Base -> ORM models -> Alembic metadata
ORM instances -> Pydantic read schemas
```

The application will not create tables automatically during startup. Schema changes are applied through Alembic.

## Database Configuration

`DATABASE_URL` is added to backend settings and the backend environment example. SQLite is the default and long-term supported primary database for this local-first, primarily single-user workspace; it is not a temporary Plan 1 database.

PostgreSQL remains optional compatibility only. SQLAlchemy and Alembic preserve reasonable portability, but migration is not a roadmap requirement and should be reconsidered only if deployment or concurrency requirements materially change.

SQLite engines receive `check_same_thread=False`. Every SQLite connection enables `PRAGMA foreign_keys=ON` so database-level cascade and nullification rules are enforced consistently.

SQLAlchemy metadata defines stable names for primary keys, foreign keys, indexes, unique constraints, and check constraints. Foreign-key columns used for conversation/message lookup and cascade checks are indexed in both ORM metadata and the initial migration.

SQLAlchemy `Uuid(as_uuid=True)` stores identifiers while Python and Pydantic expose `uuid.UUID`. This keeps the model strongly typed and preserves inexpensive portability without making PostgreSQL migration an architectural goal.

Timestamps are stored as timezone-naive SQL datetimes with an explicit UTC convention. This avoids inconsistent timezone round-trips in SQLite. API-layer timezone formatting can be standardized when the related endpoints are introduced.

## ORM Models

### Conversation

- `id`: UUID primary key generated with UUID v4
- `title`: required string, default `New conversation`
- `default_provider`: optional string
- `default_model`: optional string
- `created_at`: UTC creation timestamp
- `updated_at`: UTC timestamp updated when the ORM row changes
- relationships: many messages and many LLM calls

### Message

- `id`: UUID primary key generated with UUID v4
- `conversation_id`: required foreign key to `conversations.id`
- `role`: required string
- `content`: required text
- `provider`: optional string
- `model`: optional string
- `created_at`: UTC creation timestamp
- relationship: belongs to one conversation

`provider` and `model` remain optional because user messages are not produced by a model.

### LLMCall

- `id`: UUID primary key generated with UUID v4
- `conversation_id`: required foreign key to `conversations.id`
- `message_id`: optional foreign key to `messages.id`
- `provider`: required string
- `model`: required string
- `input_tokens`: optional integer
- `output_tokens`: optional integer
- `total_tokens`: optional integer
- `estimated_cost`: optional decimal
- `latency_ms`: optional integer
- `status`: required string, default `pending`
- `error_message`: optional text
- `created_at`: UTC creation timestamp
- relationships: belongs to one conversation and optionally one message

Usage, cost, and latency columns are established now because they are part of the planned model. Their calculation and application behavior remain in `P1-M4-S1`.

## Relationship And Delete Rules

- Deleting a conversation cascades to its messages and LLM calls in both ORM and database behavior.
- Deleting an individual message preserves its LLM call audit records and sets their `message_id` to `NULL`.
- A failed model call may have no assistant message, so `LLMCall.message_id` is nullable.
- `messages.conversation_id`, `llm_calls.conversation_id`, and `llm_calls.message_id` are indexed.

These rules preserve useful call history while keeping conversation deletion complete and predictable.

## Pydantic Schemas

Each entity receives focused create and read schemas:

- Create schemas contain caller-controlled fields and sensible defaults.
- Read schemas include generated IDs and timestamps.
- Read schemas enable attribute-based validation for ORM instances.
- UUID fields use `uuid.UUID` rather than plain strings.

Update schemas are deferred until a service or API requires them.

## Error Boundaries

This batch does not add HTTP error handlers. Configuration and database errors remain explicit exceptions during startup, migration, or tests. Provider and API error translation belong to later steps.

Constraints prevent invalid relationships at the database boundary. Pydantic validates input shape before future service code receives it.

## Test Design

Implementation follows red-green-refactor cycles. Focused tests cover:

1. Alembic `upgrade head` creates `conversations`, `messages`, and `llm_calls` in a temporary SQLite database.
2. A SQLAlchemy session can create and query each model.
3. IDs are UUID values and relationships load correctly.
4. Conversation deletion cascades to messages and LLM calls.
5. Message deletion sets `LLMCall.message_id` to `NULL` without deleting the call.
6. Alembic downgrade to base removes the three domain tables and can be upgraded again.
7. Create and read schemas validate defaults, required fields, ORM objects, and malformed UUID values.
8. Existing health tests continue to pass.

Tests use temporary SQLite databases and do not read local `.env` files or require real provider credentials.

## Documentation And Dependency Updates

SQLAlchemy and Alembic dependencies are added to both `backend/pyproject.toml` and the root `requirements.txt`. `backend/.env.example`, README startup/migration instructions, architecture documentation, and the Plan 1 execution table are updated only where Batch 4 changes operational behavior or status.

## Deferred Work

The following remains outside this batch:

- conversation and chat services
- database-backed API endpoints
- LLM Provider abstractions or adapters
- model registry
- token and cost calculation logic
- Streaming, Chat UI, and conversation history UI
