# Plan 3 M4 S1～S3 Naive Vector Retriever Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Repository policy forbids subagents for this batch. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现可替换 EmbeddingProvider/VectorStore 之上的基础 Top-K Retriever，返回稳定、完整且可序列化的 Chunk 来源结构。

**Architecture:** `app.schemas.rag.RetrievalResult` 冻结来源契约；`app.rag.retriever.Retriever` 只编排 query embedding、维度检查、Knowledge Base 隔离搜索和结果映射。Retriever 不读取 Settings/SQLite、不管理 client、不创建 API，Provider/VectorStore 错误保持原边界。

**Tech Stack:** Python 3.11、Pydantic 2、异步 EmbeddingProvider、异步 VectorStore/Qdrant、pytest。

## Global Constraints

- 只实现 `P3-M4-S1～S3`；不创建 RAG Prompt/API、rag_queries runtime、Tool、前端或 S4+。
- 不实现 metadata filter、Hybrid Search、Parent-Child、Rerank、Evaluation、Trace、Memory、OCR、multimodal 或 Plan 4+ runtime。
- 不读取真实 `.env`、secret/API key 或 `backend/ai_agent_lab.db`；不调用真实付费 Provider 或网络 Tool。
- 测试使用完整 Mock/Recording Provider 与 VectorStore；可选真实 Qdrant smoke 只能使用随机临时 collection 和确定性 Mock Embedding。
- 不创建/切换分支，不使用 worktree，不 stage、commit、push 或 tag；用户手动提交。
- 不使用子代理或外部 review；Codex self-review 是唯一 gate。

---

### Task 1: RetrievalResult schema RED/GREEN

**Files:**

- Create: `backend/tests/test_retrieval_result.py`
- Modify: `backend/app/schemas/rag.py`
- Modify: `backend/app/schemas/__init__.py`

**Interfaces:**

- Produces: `RetrievalResult` with UUID ownership, filename/index/content/score, heading/page and JSON metadata.
- Consumed by: `Retriever.retrieve()` and later Plan 3 RAG response schemas.

- [x] **Step 1: Write the failing schema tests**

Create tests that import `RetrievalResult` from `app.schemas`, construct one complete source, assert `model_dump(mode="json")` emits canonical UUID strings, and reject bool score/index/page, blank content/filename, non-finite score and extra fields.

```python
def test_retrieval_result_serializes_complete_source() -> None:
    result = RetrievalResult(
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        document_id=DOCUMENT_ID,
        chunk_id=CHUNK_ID,
        filename="guide.md",
        chunk_index=0,
        content="Retriever overview",
        score=0.91,
        heading="Overview",
        page_number=None,
        metadata={"source_format": "md", "line_range": [1, 2]},
    )
    assert result.model_dump(mode="json")["chunk_id"] == str(CHUNK_ID)
```

- [x] **Step 2: Verify RED**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_retrieval_result.py -q
```

Expected: collection fails because `RetrievalResult` is not exported.

- [x] **Step 3: Implement the minimal strict schema**

Add to `app.schemas.rag`:

```python
class RetrievalResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    knowledge_base_id: UUID
    document_id: UUID
    chunk_id: UUID
    filename: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
    ]
    chunk_index: StrictInt = Field(ge=0)
    content: str
    score: FiniteFloat
    heading: Annotated[str, StringConstraints(max_length=512)] | None = None
    page_number: StrictInt | None = Field(default=None, gt=0)
    metadata: dict[str, JsonValue]
```

Add before-validators that reject bool/non-number score and blank content without copying content into errors. Export the schema from `app.schemas`.

- [x] **Step 4: Verify GREEN and adjacent schemas**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_retrieval_result.py tests/test_knowledge_schemas.py -q
```

Expected: all tests pass.

### Task 2: Retriever happy path RED/GREEN

**Files:**

- Create: `backend/tests/test_retriever.py`
- Create: `backend/app/rag/retriever.py`

**Interfaces:**

- Consumes: `EmbeddingProvider.embed_query(str) -> EmbeddingResult` and `VectorStore.search(VectorSearchQuery) -> tuple[VectorSearchResult, ...]`.
- Produces: `Retriever.retrieve(...)->tuple[RetrievalResult, ...]`.

- [x] **Step 1: Add complete recording boundary doubles**

The test file defines concrete `RecordingEmbeddingProvider` and `RecordingVectorStore` implementations. They record query/search calls and return configurable real `EmbeddingResult` / `VectorSearchResult` contracts; unused abstract operations raise `AssertionError`.

```python
class RecordingVectorStore(VectorStore):
    def __init__(self, results: tuple[VectorSearchResult, ...] = ()) -> None:
        self.results = results
        self.search_queries: list[VectorSearchQuery] = []

    async def search(self, query: VectorSearchQuery) -> tuple[VectorSearchResult, ...]:
        self.search_queries.append(query)
        return self.results
```

- [x] **Step 2: Write the failing happy-path tests**

Cover default Top-5, custom Top-K/threshold, order-preserving mapping of two results, complete source fields, and zero-hit empty tuple. Assert one `embed_query()` call and exact `VectorSearchQuery` contents.

- [x] **Step 3: Verify RED**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_retriever.py -q
```

Expected: collection fails because `app.rag.retriever` does not exist.

- [x] **Step 4: Implement the minimal Retriever path**

Create:

```python
class Retriever:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

    async def retrieve(
        self,
        *,
        query: str,
        knowledge_base_id: UUID,
        top_k: int = 5,
        score_threshold: float | None = None,
    ) -> tuple[RetrievalResult, ...]:
        embedding = await self._embedding_provider.embed_query(query)
        vector = embedding.vectors[0]
        results = await self._vector_store.search(
            VectorSearchQuery(
                knowledge_base_id=knowledge_base_id,
                vector=vector,
                limit=top_k,
                score_threshold=score_threshold,
            )
        )
        return tuple(_to_retrieval_result(item) for item in results)
```

Map every stable payload field and deep-copy metadata. Import this module directly; do not add it to `app.rag.__init__`, preserving the lightweight package boundary established by M3.

- [x] **Step 5: Verify GREEN**

Run the new test file and existing Provider/VectorStore contract tests. Expected: all pass.

### Task 3: Strict input validation RED/GREEN

**Files:**

- Modify: `backend/tests/test_retriever.py`
- Modify: `backend/app/rag/retriever.py`

**Interfaces:**

- Produces: `RetrieverError`, `RetrieverInputError`, fixed safe validation messages.

- [x] **Step 1: Write invalid-input tests**

Parameterize non-string/blank query, non-UUID Knowledge Base ID, bool/string/out-of-range Top-K, bool/string/NaN/infinite threshold. For every case assert `RetrieverInputError`, `provider.queries == []`, and `store.search_queries == []`.

```python
@pytest.mark.parametrize("top_k", [True, "5", 0, 101])
def test_retrieve_rejects_invalid_top_k_before_embedding(top_k: object) -> None:
    with pytest.raises(RetrieverInputError, match="top_k"):
        asyncio.run(make_retriever(provider, store).retrieve(
            query="question", knowledge_base_id=KNOWLEDGE_BASE_ID, top_k=top_k,
        ))
    assert provider.queries == []
```

- [x] **Step 2: Verify RED**

Expected: current implementation either calls the Provider or exposes raw validation/type exceptions.

- [x] **Step 3: Implement validation before external calls**

Add `_validate_retrieval_input()` using exact type checks and `math.isfinite()`. Do not trim or rewrite a valid query; error messages name only the invalid field, never its value.

- [x] **Step 4: Verify GREEN**

Run `tests/test_retriever.py`; expected: all tests pass with zero external calls for invalid input.

### Task 4: Untrusted response and boundary error RED/GREEN

**Files:**

- Modify: `backend/tests/test_retriever.py`
- Modify: `backend/app/rag/retriever.py`

**Interfaces:**

- Produces: `RetrieverResponseError` for invalid query-vector count/dimension or cross-KB results.
- Preserves: existing `EmbeddingProviderError` and `VectorStoreError` subclasses.

- [x] **Step 1: Write response/error tests**

Cover an EmbeddingResult with two vectors, one vector of the wrong store dimension, a result whose payload belongs to another Knowledge Base, Provider failure identity, VectorStore failure identity, and nested metadata mutation after return.

```python
def test_retrieve_rejects_result_outside_requested_knowledge_base() -> None:
    store = RecordingVectorStore(results=(make_result(knowledge_base_id=OTHER_KB_ID),))
    with pytest.raises(RetrieverResponseError, match="response is invalid"):
        asyncio.run(make_retriever(provider, store).retrieve(
            query="question", knowledge_base_id=KNOWLEDGE_BASE_ID,
        ))
```

- [x] **Step 2: Verify RED**

Expected: multiple/wrong-dimension embeddings are accepted or leak lower-level exceptions, and cross-KB output is returned.

- [x] **Step 3: Implement fail-closed response checks**

Require an actual `EmbeddingResult` with exactly one vector and exact `vector_store.dimension`; require a tuple of actual `VectorSearchResult` instances and matching `payload.knowledge_base_id`. Raise fixed `RetrieverResponseError` with `from None`. Build result metadata from `deepcopy(payload.metadata)`.

- [x] **Step 4: Verify GREEN and adjacent regression**

Run Retriever, Embedding Provider, VectorStore, Qdrant adapter and schema tests. Expected: all pass.

### Task 5: Matching verification, documentation, and self-review

**Files:**

- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/20-knowledge-base-design.md`
- Modify: `docs/22-document-ingestion-pipeline.md`
- Modify: `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`
- Modify: this spec and plan

- [x] Run Retriever/schema/Provider/VectorStore focused tests and record exact counts.
- [x] Run real local Qdrant with a random `codex_p3_m4_s1_s3_*` collection and deterministic Mock Embedding; assert KB isolation/Top-K/threshold and remove the collection in `finally`.
- [x] Update current scope, standalone Retriever contract, source structure, errors and limitations without claiming RAG Prompt/API/answer/Tool completion.
- [x] Run complete backend pytest and `pip check`.
- [x] Use a newly created system temporary SQLite for Alembic upgrade/current/check/downgrade/re-upgrade; verify deletion and never access the user DB.
- [x] Run frontend typecheck, tests and production build.
- [x] Run Compose/Qdrant health, Markdown link, secret/private-key, later-Plan/network runtime, tracked-artifact and `git diff --check` gates.
- [x] Verify exact diff allowlist, staged 0, `main == origin/main`, unchanged peeled tags and no branch/worktree operations.
- [x] Classify Codex self-review as must fix / fix later / limitation / not applicable; fix all must-fix and rerun affected verification.
- [x] Report whether S1～S3 are complete and whether the workspace can enter S4～S6; suggest `feat(rag): add naive vector retriever` without committing.
