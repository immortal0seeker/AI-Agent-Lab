from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import (
    get_db_session,
    get_embedding_provider,
    get_llm_providers,
    get_model_registry,
    get_vector_store,
)
from app.db.base import Base
from app.db.session import create_db_engine
from app.main import app
from app.models import Conversation, KnowledgeBase, LLMCall, Message, RagQuery
from app.providers.embedding import (
    EmbeddingProvider,
    EmbeddingResult,
    EmbeddingUsage,
)
from app.providers.llm.base import (
    BaseLLMProvider,
    ChatChunk,
    ChatRequest,
    LLMResponse,
    ProviderRequestError,
    TokenUsage,
)
from app.providers.llm.registry import ModelInfo, ModelRegistry
from app.rag.vectorstores import (
    ChunkVectorPayload,
    VectorCollectionStatus,
    VectorPoint,
    VectorSearchQuery,
    VectorSearchResult,
    VectorStore,
)


KNOWLEDGE_BASE_ID = UUID("11111111-1111-1111-1111-111111111111")
OTHER_KNOWLEDGE_BASE_ID = UUID("99999999-9999-9999-9999-999999999999")
DOCUMENT_ID = UUID("22222222-2222-2222-2222-222222222222")
CHUNK_ID = UUID("33333333-3333-3333-3333-333333333333")


class ApiEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        super().__init__(name="api-recording")
        self.queries: list[str] = []

    async def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        raise AssertionError("RAG API retrieval must use embed_query")

    async def embed_query(self, query: str) -> EmbeddingResult:
        self.queries.append(query)
        return EmbeddingResult(
            model="synthetic-embedding",
            vectors=((0.1, 0.2, 0.3),),
            usage=EmbeddingUsage(input_tokens=2, total_tokens=2),
        )


class ApiVectorStore(VectorStore):
    def __init__(self) -> None:
        self.results = (make_search_result(),)
        self.search_queries: list[VectorSearchQuery] = []

    @property
    def collection_name(self) -> str:
        return "api_recording_chunks"

    @property
    def dimension(self) -> int:
        return 3

    async def ensure_collection(self) -> VectorCollectionStatus:
        raise AssertionError("RAG API retrieval must not ensure collections")

    async def upsert(self, points: list[VectorPoint]) -> tuple[UUID, ...]:
        raise AssertionError("RAG API retrieval must not upsert")

    async def search(
        self,
        query: VectorSearchQuery,
    ) -> tuple[VectorSearchResult, ...]:
        self.search_queries.append(query)
        return self.results

    async def delete_document_vectors(
        self,
        *,
        knowledge_base_id: UUID,
        document_id: UUID,
    ) -> None:
        raise AssertionError("RAG API retrieval must not delete")

    async def close(self) -> None:
        return None


class ApiLLMProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []
        self.fail_with: Exception | None = None

    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        if self.fail_with is not None:
            raise self.fail_with
        return LLMResponse(
            id="api-rag-response",
            model="resolved-model",
            content="API grounded answer [1]",
            finish_reason="stop",
            usage=TokenUsage(input_tokens=8, output_tokens=4, total_tokens=12),
        )

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        if False:
            yield ChatChunk()
        raise AssertionError("RAG Chat API is non-streaming")


def make_search_result(
    *,
    knowledge_base_id: UUID = KNOWLEDGE_BASE_ID,
) -> VectorSearchResult:
    return VectorSearchResult(
        point_id=CHUNK_ID,
        score=0.93,
        payload=ChunkVectorPayload(
            knowledge_base_id=knowledge_base_id,
            document_id=DOCUMENT_ID,
            chunk_id=CHUNK_ID,
            embedding_provider="api-recording",
            embedding_model="synthetic-embedding",
            filename="guide.md",
            chunk_index=0,
            content="The workspace uses layered services.",
            heading="Architecture",
            page_number=None,
            metadata={"source_format": "md", "line_range": [1, 2]},
        ),
    )


def make_registry() -> ModelRegistry:
    return ModelRegistry(
        [
            ModelInfo(
                provider="openai_compatible",
                model="example-model",
                display_name="Example Model",
                input_price_per_1m=Decimal("0.50"),
                output_price_per_1m=Decimal("1.50"),
            )
        ]
    )


@pytest.fixture
def rag_api_context(tmp_path: Path) -> Any:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(f"sqlite:///{tmp_path / 'rag-api.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as seed_session:
        knowledge_base = KnowledgeBase(
            id=KNOWLEDGE_BASE_ID,
            name="Project docs",
        )
        conversation = Conversation(title="RAG conversation")
        seed_session.add_all([knowledge_base, conversation])
        seed_session.commit()
        conversation_id = conversation.id

    embedding_provider = ApiEmbeddingProvider()
    vector_store = ApiVectorStore()
    llm_provider = ApiLLMProvider()

    async def override_db_session() -> AsyncIterator[Session]:
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_embedding_provider] = lambda: embedding_provider
    app.dependency_overrides[get_vector_store] = lambda: vector_store
    app.dependency_overrides[get_llm_providers] = lambda: {
        "openai_compatible": llm_provider
    }
    app.dependency_overrides[get_model_registry] = make_registry

    with TestClient(app) as client:
        yield (
            client,
            session_factory,
            conversation_id,
            embedding_provider,
            vector_store,
            llm_provider,
        )

    app.dependency_overrides.clear()
    engine.dispose()


def test_openapi_exposes_rag_query_and_chat_routes(
    rag_api_context: Any,
) -> None:
    client, _, _, _, _, _ = rag_api_context

    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/rag/query" in paths
    assert "/api/v1/rag/chat" in paths


def test_rag_query_api_returns_results_metadata_and_audit_id(
    rag_api_context: Any,
) -> None:
    client, session_factory, _, embedding_provider, vector_store, llm_provider = (
        rag_api_context
    )

    response = client.post(
        "/api/v1/rag/query",
        json={
            "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
            "query": "What is the architecture?",
            "top_k": 3,
            "score_threshold": 0.5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    rag_query_id = UUID(payload.pop("rag_query_id"))
    assert payload == {
        "results": [
            {
                    "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
                    "document_id": str(DOCUMENT_ID),
                    "chunk_id": str(CHUNK_ID),
                    "embedding_provider": "api-recording",
                    "embedding_model": "synthetic-embedding",
                "filename": "guide.md",
                "chunk_index": 0,
                "content": "The workspace uses layered services.",
                "score": 0.93,
                "heading": "Architecture",
                "page_number": None,
                "metadata": {
                    "source_format": "md",
                    "line_range": [1, 2],
                },
            }
        ],
        "metadata": {
            "strategy": "naive_vector",
            "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
            "top_k": 3,
            "score_threshold": 0.5,
            "result_count": 1,
        },
    }
    assert embedding_provider.queries == ["What is the architecture?"]
    assert vector_store.search_queries[0].limit == 3
    assert llm_provider.requests == []
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Message)) == 0
        assert session.scalar(select(func.count()).select_from(LLMCall)) == 0
        stored = session.get(RagQuery, rag_query_id)
        assert stored is not None
        assert stored.query == "What is the architecture?"
        assert stored.top_k == 3
        assert stored.conversation_id is None
        assert stored.answer_message_id is None
        assert stored.latency_ms is not None
        assert stored.retrieved_chunks_json[0]["chunk_id"] == str(CHUNK_ID)


def test_rag_query_api_does_not_resolve_llm_dependencies(
    rag_api_context: Any,
) -> None:
    client, _, _, _, _, _ = rag_api_context

    def fail_if_resolved() -> None:
        raise AssertionError("retrieval-only API must not resolve LLM dependencies")

    app.dependency_overrides[get_model_registry] = fail_if_resolved
    app.dependency_overrides[get_llm_providers] = fail_if_resolved

    response = client.post(
        "/api/v1/rag/query",
        json={
            "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
            "query": "Retrieval only",
        },
    )

    assert response.status_code == 200


def test_rag_chat_api_returns_answer_sources_and_persists_messages(
    rag_api_context: Any,
) -> None:
    client, session_factory, conversation_id, _, _, llm_provider = (
        rag_api_context
    )

    response = client.post(
        "/api/v1/rag/chat",
        json={
            "conversation_id": str(conversation_id),
            "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
            "provider": "openai_compatible",
            "model": "example-model",
            "query": "What is the architecture?",
            "top_k": 3,
            "temperature": 0.1,
            "max_tokens": 256,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"] == str(conversation_id)
    assert payload["answer"] == "API grounded answer [1]"
    assert payload["user_message"]["content"] == "What is the architecture?"
    assert payload["assistant_message"]["content"] == (
        "API grounded answer [1]"
    )
    assert payload["sources"][0]["source_index"] == 1
    assert payload["sources"][0]["chunk_id"] == str(CHUNK_ID)
    assert payload["metadata"]["strategy"] == "naive_vector"
    assert payload["metadata"]["result_count"] == 1
    assert payload["metadata"]["used_source_count"] == 1
    assert payload["metadata"]["context_characters"] > 0
    assert payload["provider"] == "openai_compatible"
    assert payload["model"] == "resolved-model"
    assert payload["usage"] == {
        "input_tokens": 8,
        "output_tokens": 4,
        "total_tokens": 12,
    }
    UUID(payload["llm_call_id"])
    rag_query_id = UUID(payload["rag_query_id"])
    assert len(llm_provider.requests) == 1
    assert llm_provider.requests[0].messages[0].role == "system"
    assert llm_provider.requests[0].messages[-1].content is not None
    assert "[1] 文件：guide.md" in (
        llm_provider.requests[0].messages[-1].content
    )

    messages_response = client.get(
        f"/api/v1/conversations/{conversation_id}/messages"
    )
    assert messages_response.status_code == 200
    assert [item["content"] for item in messages_response.json()] == [
        "What is the architecture?",
        "API grounded answer [1]",
    ]
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Message)) == 2
        assert session.scalar(select(func.count()).select_from(LLMCall)) == 1
        stored = session.get(RagQuery, rag_query_id)
        assert stored is not None
        assert stored.conversation_id == conversation_id
        assert stored.answer_message_id == UUID(
            payload["assistant_message"]["id"]
        )
        assert stored.top_k == 3
        assert stored.retrieved_chunks_json[0]["chunk_id"] == str(CHUNK_ID)


@pytest.mark.parametrize(
    "payload",
    [
        {
            "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
            "query": "   ",
        },
        {
            "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
            "query": "Question",
            "top_k": True,
        },
        {
            "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
            "query": "Question",
            "unexpected": "value",
        },
    ],
)
def test_rag_query_api_rejects_invalid_payload(
    rag_api_context: Any,
    payload: dict[str, object],
) -> None:
    client, _, _, _, _, _ = rag_api_context

    response = client.post("/api/v1/rag/query", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_rag_query_api_returns_safe_missing_knowledge_base_error(
    rag_api_context: Any,
) -> None:
    client, _, _, _, _, _ = rag_api_context

    response = client.post(
        "/api/v1/rag/query",
        json={
            "knowledge_base_id": str(OTHER_KNOWLEDGE_BASE_ID),
            "query": "private missing KB question",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "knowledge_base_not_found",
            "message": "Knowledge base not found",
            "request_id": response.headers["x-request-id"],
        }
    }
    assert "private missing KB question" not in response.text


def test_rag_query_api_maps_untrusted_retrieval_response_to_safe_502(
    rag_api_context: Any,
) -> None:
    client, _, _, _, vector_store, _ = rag_api_context
    vector_store.results = (
        make_search_result(knowledge_base_id=OTHER_KNOWLEDGE_BASE_ID),
    )

    response = client.post(
        "/api/v1/rag/query",
        json={
            "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
            "query": "private cross-KB question",
        },
    )

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "rag_retrieval_response_invalid",
            "message": "The retrieval backend returned an invalid response",
            "request_id": response.headers["x-request-id"],
        }
    }
    assert "private cross-KB question" not in response.text


def test_rag_chat_api_rolls_back_messages_when_provider_fails(
    rag_api_context: Any,
) -> None:
    client, session_factory, conversation_id, _, _, llm_provider = (
        rag_api_context
    )
    llm_provider.fail_with = ProviderRequestError(
        "private provider diagnostic",
        status_code=503,
    )

    response = client.post(
        "/api/v1/rag/chat",
        json={
            "conversation_id": str(conversation_id),
            "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
            "provider": "openai_compatible",
            "model": "example-model",
            "query": "private failed question",
        },
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "provider_unknown_error"
    assert "private provider diagnostic" not in response.text
    assert "private failed question" not in response.text
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Message)) == 0
        assert session.scalar(select(func.count()).select_from(LLMCall)) == 0
        assert session.scalar(select(func.count()).select_from(RagQuery)) == 0


def test_rag_chat_api_returns_safe_missing_conversation_error(
    rag_api_context: Any,
) -> None:
    client, _, _, _, _, _ = rag_api_context

    response = client.post(
        "/api/v1/rag/chat",
        json={
            "conversation_id": str(UUID(int=99)),
            "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
            "provider": "openai_compatible",
            "model": "example-model",
            "query": "Question",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "conversation_not_found"
