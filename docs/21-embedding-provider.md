# Embedding Provider

## Scope

Plan 3 M3 S1～S6 provides a vendor-neutral asynchronous Embedding contract,
an ordered runtime Registry, and one OpenAI-compatible HTTP adapter. The
adapter can turn a non-empty batch of strings, or one query string, into
validated vectors without leaking vendor response shapes into RAG services.

Qdrant collection management is implemented separately by the VectorStore
boundary introduced in P3-M3-S7～S9. The completed document vector-ingestion
composition is described in [Document Ingestion Pipeline](22-document-ingestion-pipeline.md).

## Runtime Boundary

```text
caller
  -> EmbeddingProviderRegistry.get_provider(configured name)
  -> OpenAICompatibleEmbeddingProvider
  -> POST {base_url}/embeddings
  -> EmbeddingResult(model, ordered vectors, usage)
```

`EmbeddingProvider` owns two asynchronous operations:

- `embed_texts(texts)` sends one batch request and returns one vector per input;
- `embed_query(query)` uses the same batch path with one input.

`EmbeddingResult` is immutable. It rejects empty vectors, non-finite or
non-numeric components, inconsistent dimensions, blank model names, invalid
token counts, and a total token count smaller than the input token count.

The OpenAI-compatible adapter follows the public Embeddings request/response
shape: array input, `data[].index`, float `embedding`, response `model`, and
`usage.prompt_tokens` / `usage.total_tokens`. See the
[OpenAI Embeddings API reference](https://developers.openai.com/api/reference/resources/embeddings/methods/create)
for the reference protocol. A compatible service may impose different model,
batch, token, or dimensions support, so its own documentation remains the
operational source of truth.

## Configuration

Copy public defaults from `backend/.env.example` into a local untracked
`backend/.env` or process environment, then add the real key locally. Never put
a real key in tracked files, frontend `VITE_*` variables, logs, screenshots, or
test fixtures.

```text
EMBEDDING_PROVIDER=openai_compatible
OPENAI_COMPATIBLE_EMBEDDING_BASE_URL=https://api.example.com/v1
OPENAI_COMPATIBLE_EMBEDDING_API_KEY=
OPENAI_COMPATIBLE_EMBEDDING_MODEL=example-embedding-model
OPENAI_COMPATIBLE_EMBEDDING_DIMENSION=1536
OPENAI_COMPATIBLE_EMBEDDING_TIMEOUT_SECONDS=30
```

| Setting | Required at Provider initialization | Contract |
|---|---|---|
| `EMBEDDING_PROVIDER` | Yes for Registry selection | Exact Provider name; current adapter registers as `openai_compatible` |
| `OPENAI_COMPATIBLE_EMBEDDING_BASE_URL` | Yes | Base URL ending before `/embeddings`; a trailing slash is safe |
| `OPENAI_COMPATIBLE_EMBEDDING_API_KEY` | Yes | Stored as `SecretStr`; blank or whitespace-only values fail safely |
| `OPENAI_COMPATIBLE_EMBEDDING_MODEL` | Yes | Provider-specific embedding model identifier |
| `OPENAI_COMPATIBLE_EMBEDDING_DIMENSION` | Yes | Integer from 1 through 65,536; sent as `dimensions` and checked again locally |
| `OPENAI_COMPATIBLE_EMBEDDING_TIMEOUT_SECONDS` | No | Finite value greater than 0 and at most 3,600; default 30 |

Settings are lazy: the backend can start without an Embedding key, model, URL,
or dimension. `create_openai_compatible_embedding_provider()` checks required
values only when the concrete adapter is initialized. The caller can then
register that instance and select it using `settings.embedding_provider`.

## Model And Dimension Invariants

Model and dimension form a storage contract. Every collection that will store
the returned vectors must use the same dimension, and existing vectors cannot
be mixed silently with another model or dimension.

The configured dimension has two roles:

1. it is sent in the OpenAI-compatible request together with
   `encoding_format="float"`;
2. it is compared with the actual length of every parsed vector.

If a compatible service ignores or does not support `dimensions`, it may reject
the request or return its model default. A returned mismatch raises
`EmbeddingDimensionMismatchError` with only expected and received sizes. It
does not include input text, vector values, credentials, or the remote body.

The result records the model name returned by the service. This can differ from
the configured alias and is the identity that later ingestion/audit work should
preserve.

## Batch Behavior

The adapter sends the complete `texts` list in one HTTP request. It restores
result order from `data[].index` and rejects:

- an empty request or blank item;
- missing, duplicate, negative, out-of-range, or incomplete indexes;
- a response count different from the input count;
- malformed JSON, object type, model, usage, or vector values;
- inconsistent or unexpected vector dimensions.

Automatic token truncation and batch splitting are intentionally absent. Model
limits vary between compatible services, and silent truncation would change
retrieval meaning. The current ingestion pipeline sends the complete bounded
Document Chunk list in one Provider batch; a later policy may split it without
changing the Provider contract.

## Error Contract

All adapter failures stay below `EmbeddingProviderError`:

| Error | Meaning |
|---|---|
| `EmbeddingProviderConfigurationError` | Required configuration is missing or invalid |
| `EmbeddingProviderInputError` | Local batch/query input is empty or blank |
| `EmbeddingProviderAuthError` | HTTP 401 or 403 |
| `EmbeddingProviderRateLimitError` | HTTP 429 |
| `EmbeddingProviderTimeoutError` | HTTP 408/504 or an HTTP client timeout |
| `EmbeddingProviderBadRequestError` | Other HTTP 4xx response |
| `EmbeddingProviderServerError` | HTTP 5xx response |
| `EmbeddingProviderUnknownError` | Network failure or unclassified status |
| `EmbeddingProviderResponseError` | A success response cannot be parsed safely |
| `EmbeddingDimensionMismatchError` | Parsed vectors do not match configured dimension |

HTTP request errors expose only the normalized category and optional status
code. Remote response bodies are not copied into exceptions.

## Cost, Privacy, And Operations

- Embedding services commonly bill by input volume. Check the selected
  provider's current pricing and model limits before processing a corpus.
- One HTTP batch reduces request overhead but does not imply lower token cost.
- Lower dimensions can reduce future vector storage, transfer, and search
  memory, but may change retrieval quality and may not change API pricing.
- `EmbeddingUsage` preserves returned input/total token counts, but Plan 3 M3
  S4～S6 does not persist embedding calls or calculate currency cost.
- Document text is sent to the configured remote service when this adapter is
  used. Review data handling, retention, residency, and access policy before a
  live ingestion run.
- The repository tests use synthetic credentials and `httpx.MockTransport`.
  They prove protocol mapping and error behavior, not live service
  connectivity, billing, quality, or model availability.

## Current Limitations

- No automatic retry, fallback, caching, rate-limit backoff, batch splitting,
  or persisted embedding-call audit row.
- The Provider adapter remains storage-independent; the ingestion pipeline
  composes it with the separate Qdrant VectorStore.
- M3 does not persist embedding-call usage/cost or provide automatic retry and
  orphan reconciliation workflows.
- The M4 Retriever remains a separate caller of this Provider boundary. RAG
  answer generation, Advanced RAG, Rerank, Evaluation, Memory, OCR, and
  multimodal behavior are not included here.
