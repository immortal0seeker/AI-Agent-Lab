# Plan 1 M2 Model Registry Design

## Scope

This design covers only `P1-M2-S7` through `P1-M2-S8`:

- a JSON-backed Model Registry
- typed model metadata and current-workspace capability labels
- deterministic listing, provider filtering, and provider/model lookup
- strict configuration validation and readable load errors
- M2 Provider and Registry unit-test completion
- `docs/03-llm-provider.md` and M2 status documentation
- the formal M2 Codex review and one consolidated external review checkpoint

Chat services, model APIs, frontend model selection, persistence flows, and all later-plan capabilities are outside this batch.

## Configuration Format

The Registry uses JSON rather than YAML. Python's standard `json` module handles parsing, while Pydantic validates shape and values. This keeps the configuration structured without adding PyYAML or another runtime dependency.

The tracked `models.json` contains one clearly named OpenAI-compatible example entry aligned with `.env.example`. It is configuration scaffolding, not a claim that a real provider or paid model was verified. Users replace the example values in their own deployment configuration as the project gains an API and UI path.

## Model Metadata

`ModelInfo` owns:

- `provider`
- `model`
- `display_name`
- `supports_streaming`
- `supports_tools`
- `supports_json`
- optional `input_price_per_1m`
- optional `output_price_per_1m`

Capability labels represent behavior implemented by this workspace, not every feature supported by the upstream model. The example entry therefore enables streaming, which Batch 5 implements, while Tool Calling and JSON mode remain disabled. Prices default to `null` rather than inaccurate zero values.

All names must be non-empty, prices must be non-negative when present, and unknown fields are rejected so misspelled configuration does not silently disappear.

## Registry Contract

`ModelRegistry` is initialized from validated `ModelInfo` objects or loaded from a JSON path. It provides:

```python
ModelRegistry.from_file(path: Path) -> ModelRegistry
ModelRegistry.list_models(provider: str | None = None) -> list[ModelInfo]
ModelRegistry.get_model(provider: str, model: str) -> ModelInfo | None
load_default_registry() -> ModelRegistry
```

Configuration order is preserved for stable future UI ordering. `(provider, model)` is the unique identity; duplicate identities are rejected with `ModelRegistryError`.

Model metadata is immutable, and the Registry returns a new list from `list_models()` so callers cannot mutate internal state. `get_model()` returns `None` for an unknown identity because absence is a normal lookup result; invalid configuration remains an exception.

## Error Boundary

`ModelRegistryError` wraps unreadable files, invalid JSON, Pydantic validation failures, and duplicate identities in readable messages. The original exception remains chained for debugging. Errors include safe paths and field context but never Provider credentials.

No FastAPI exception handler or `/api/v1/models` route is added. API translation belongs to M3 when the Chat and model-selection flows have a service boundary.

## Test Design

Implementation follows red-green-refactor cycles. Tests cover:

1. The tracked default file lists the example model and its capability labels.
2. Provider filtering preserves configuration order.
3. Exact provider/model lookup returns metadata or `None`.
4. Duplicate identities fail clearly.
5. Invalid JSON, unknown fields, empty names, and negative prices fail clearly.
6. Returned lists cannot mutate Registry state.
7. Existing Provider, database, health, migration, schema, and frontend checks remain green.

Tests use temporary JSON files and no real credentials, network calls, or paid APIs.

## Documentation And M2 Completion

`docs/03-llm-provider.md` documents contracts, configuration, Registry metadata, mock verification, security behavior, and deferred work. README, overview, architecture, and the Plan 1 execution table are updated to mark M2 complete and identify `P1-M3-S1` through `P1-M3-S3` as the next scope.

Because M2 includes database models and Provider abstractions, it receives one consolidated external review after Codex self-review. This replaces per-batch Fable 5 usage and keeps the higher-cost review at the milestone boundary.

## Deferred Work

- `GET /api/v1/models` and frontend model selection
- Conversation Service, Chat Service, and Chat API
- API-level SSE and persistence
- Tool Calling and JSON mode
- detailed Provider error taxonomy, retry policy, cost calculation, and logging
- RAG, Memory, MCP, Voice, Vision, and Desktop
