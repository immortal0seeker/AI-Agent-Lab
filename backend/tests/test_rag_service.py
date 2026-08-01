import asyncio
from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.models import Conversation, KnowledgeBase, LLMCall, Message, RagQuery
from app.providers.embedding import (
    EmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingProviderResponseError,
    EmbeddingResult,
    EmbeddingUsage,
)
from app.providers.llm.base import (
    BaseLLMProvider,
    ChatChunk,
    ChatRequest,
    LLMResponse,
    LLMToolCall,
    ProviderRequestError,
    ProviderResponseError,
    TokenUsage,
)
from app.providers.llm.registry import ModelInfo, ModelRegistry
from app.rag.rag_prompt import RagPromptBuilder
from app.rag.retriever import Retriever
from app.rag.vectorstores import (
    ChunkVectorPayload,
    VectorCollectionStatus,
    VectorPoint,
    VectorSearchQuery,
    VectorSearchResult,
    VectorStore,
    VectorStoreError,
)
from app.schemas.conversation import ConversationCreate
from app.schemas.message import MessageCreate
from app.schemas.rag import (
    RagChatRequest,
    RagRetrievalMetadata,
    RagRetrievalRequest,
)
from app.services.conversation_service import ConversationService
from app.services.errors import (
    ChatModelNotFoundError,
    ChatProviderUnavailableError,
    ConversationNotFoundError,
    KnowledgeBaseNotFoundError,
)
from app.services.rag_service import RagService


KNOWLEDGE_BASE_ID = UUID("11111111-1111-1111-1111-111111111111")
DOCUMENT_ID = UUID("22222222-2222-2222-2222-222222222222")
CHUNK_ID = UUID("33333333-3333-3333-3333-333333333333")


class RecordingEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        *,
        fail_with: EmbeddingProviderError | None = None,
    ) -> None:
        super().__init__(name="recording")
        self.fail_with = fail_with
        self.queries: list[str] = []

    async def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        raise AssertionError("Retriever must use embed_query")

    async def embed_query(self, query: str) -> EmbeddingResult:
        self.queries.append(query)
        if self.fail_with is not None:
            raise self.fail_with
        return EmbeddingResult(
            model="synthetic-embedding",
            vectors=((0.1, 0.2, 0.3),),
            usage=EmbeddingUsage(input_tokens=2, total_tokens=2),
        )


class RecordingVectorStore(VectorStore):
    def __init__(
        self,
        *,
        results: tuple[VectorSearchResult, ...] = (),
        fail_with: VectorStoreError | None = None,
    ) -> None:
        self.results = results
        self.fail_with = fail_with
        self.search_queries: list[VectorSearchQuery] = []

    @property
    def collection_name(self) -> str:
        return "recording_chunks"

    @property
    def dimension(self) -> int:
        return 3

    async def ensure_collection(self) -> VectorCollectionStatus:
        raise AssertionError("Retriever must not ensure collections")

    async def upsert(self, points: list[VectorPoint]) -> tuple[UUID, ...]:
        raise AssertionError("Retriever must not upsert vectors")

    async def search(
        self,
        query: VectorSearchQuery,
    ) -> tuple[VectorSearchResult, ...]:
        self.search_queries.append(query)
        if self.fail_with is not None:
            raise self.fail_with
        return self.results

    async def delete_document_vectors(
        self,
        *,
        knowledge_base_id: UUID,
        document_id: UUID,
    ) -> None:
        raise AssertionError("Retriever must not delete vectors")

    async def close(self) -> None:
        raise AssertionError("Retriever does not own store lifecycle")


class RecordingLLMProvider(BaseLLMProvider):
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            id="rag-response",
            model="resolved-model",
            content="Grounded answer [1]",
            finish_reason="stop",
            usage=TokenUsage(input_tokens=9, output_tokens=4, total_tokens=13),
        )

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        if False:
            yield ChatChunk()
        raise AssertionError("RAG Chat is non-streaming")


class FailingLLMProvider(RecordingLLMProvider):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self.error = error

    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        raise self.error


class ToolOnlyLLMProvider(RecordingLLMProvider):
    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            model="resolved-model",
            content=None,
            tool_calls=(
                LLMToolCall(
                    tool_call_id="call-1",
                    tool_name="read_file",
                    arguments={"path": "README.md"},
                ),
            ),
        )


class BlankLLMProvider(RecordingLLMProvider):
    async def chat(self, request: ChatRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            model="resolved-model",
            content="   ",
        )


def make_search_result(
    *,
    content: str = "The workspace uses layered services.",
) -> VectorSearchResult:
    return VectorSearchResult(
        point_id=CHUNK_ID,
        score=0.92,
        payload=ChunkVectorPayload(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            document_id=DOCUMENT_ID,
            chunk_id=CHUNK_ID,
            filename="guide.md",
            chunk_index=0,
            content=content,
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


def create_test_session(tmp_path: Path) -> tuple[Session, Engine]:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(f"sqlite:///{tmp_path / 'rag-service.db'}")
    Base.metadata.create_all(engine)
    return Session(engine), engine


def seed_knowledge_and_conversation(
    session: Session,
    *,
    with_history: bool = False,
) -> Conversation:
    session.add(KnowledgeBase(id=KNOWLEDGE_BASE_ID, name="Project docs"))
    conversations = ConversationService(session)
    conversation = conversations.create_conversation(ConversationCreate())
    if with_history:
        conversations.append_message(
            MessageCreate(
                conversation_id=conversation.id,
                role="user",
                content="Earlier question",
            )
        )
        conversations.append_message(
            MessageCreate(
                conversation_id=conversation.id,
                role="assistant",
                content="Earlier answer",
            )
        )
    session.commit()
    return conversation


def make_service(
    session: Session,
    *,
    embedding_provider: RecordingEmbeddingProvider,
    vector_store: RecordingVectorStore,
    llm_provider: RecordingLLMProvider,
    max_context_characters: int = 12_000,
) -> RagService:
    return RagService(
        session,
        retriever=Retriever(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
        ),
        prompt_builder=RagPromptBuilder(
            max_context_characters=max_context_characters
        ),
        registry=make_registry(),
        providers={"openai_compatible": llm_provider},
    )


def test_rag_query_persists_audit_without_llm_or_message_writes(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    session.add(KnowledgeBase(id=KNOWLEDGE_BASE_ID, name="Project docs"))
    session.commit()
    embedding_provider = RecordingEmbeddingProvider()
    vector_store = RecordingVectorStore(results=(make_search_result(),))
    llm_provider = RecordingLLMProvider()
    service = make_service(
        session,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        llm_provider=llm_provider,
    )

    result = asyncio.run(
        service.query(
            RagRetrievalRequest(
                knowledge_base_id=KNOWLEDGE_BASE_ID,
                query="What is the architecture?",
                top_k=3,
                score_threshold=0.5,
            )
        )
    )

    assert [item.chunk_id for item in result.results] == [CHUNK_ID]
    assert result.metadata == RagRetrievalMetadata(
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        top_k=3,
        score_threshold=0.5,
        result_count=1,
    )
    assert embedding_provider.queries == ["What is the architecture?"]
    assert vector_store.search_queries == [
        VectorSearchQuery(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            vector=(0.1, 0.2, 0.3),
            limit=3,
            score_threshold=0.5,
        )
    ]
    assert llm_provider.requests == []
    assert session.scalar(select(func.count()).select_from(Message)) == 0
    assert session.scalar(select(func.count()).select_from(LLMCall)) == 0
    stored = session.scalar(select(RagQuery))
    assert stored is result.rag_query
    assert stored.knowledge_base_id == KNOWLEDGE_BASE_ID
    assert stored.query == "What is the architecture?"
    assert stored.top_k == 3
    assert stored.conversation_id is None
    assert stored.answer_message_id is None
    assert stored.latency_ms is not None and stored.latency_ms >= 0
    assert stored.retrieved_chunks_json[0]["source_index"] == 1
    assert stored.retrieved_chunks_json[0]["chunk_id"] == str(CHUNK_ID)
    assert stored.retrieved_chunks_json[0]["document_id"] == str(DOCUMENT_ID)
    assert stored.retrieved_chunks_json[0]["content"] == (
        "The workspace uses layered services."
    )

    session.close()
    engine.dispose()


def test_rag_query_persists_top_k_for_zero_hits(tmp_path: Path) -> None:
    session, engine = create_test_session(tmp_path)
    session.add(KnowledgeBase(id=KNOWLEDGE_BASE_ID, name="Project docs"))
    session.commit()
    service = make_service(
        session,
        embedding_provider=RecordingEmbeddingProvider(),
        vector_store=RecordingVectorStore(),
        llm_provider=RecordingLLMProvider(),
    )

    result = asyncio.run(
        service.query(
            RagRetrievalRequest(
                knowledge_base_id=KNOWLEDGE_BASE_ID,
                query="Unknown answer",
                top_k=9,
            )
        )
    )

    assert result.results == ()
    assert result.rag_query.top_k == 9
    assert result.rag_query.retrieved_chunks_json == []
    assert session.scalars(select(RagQuery)).all() == [result.rag_query]

    session.close()
    engine.dispose()


def test_rag_query_rejects_missing_knowledge_base_before_embedding(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    embedding_provider = RecordingEmbeddingProvider()
    vector_store = RecordingVectorStore()
    llm_provider = RecordingLLMProvider()
    service = make_service(
        session,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        llm_provider=llm_provider,
    )

    with pytest.raises(KnowledgeBaseNotFoundError):
        asyncio.run(
            service.query(
                RagRetrievalRequest(
                    knowledge_base_id=KNOWLEDGE_BASE_ID,
                    query="Question",
                )
            )
        )

    assert embedding_provider.queries == []
    assert vector_store.search_queries == []
    assert llm_provider.requests == []
    assert session.scalar(select(func.count()).select_from(RagQuery)) == 0

    session.close()
    engine.dispose()


def test_rag_chat_persists_grounded_turn_and_llm_call(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    session.add(KnowledgeBase(id=KNOWLEDGE_BASE_ID, name="Project docs"))
    conversations = ConversationService(session)
    conversation = conversations.create_conversation(
        ConversationCreate(
            title="Existing conversation",
            default_provider="previous-provider",
            default_model="previous-model",
        )
    )
    conversations.append_message(
        MessageCreate(
            conversation_id=conversation.id,
            role="user",
            content="Earlier question",
        )
    )
    conversations.append_message(
        MessageCreate(
            conversation_id=conversation.id,
            role="assistant",
            content="Earlier answer",
        )
    )
    session.commit()
    conversation_id = conversation.id
    previous_updated_at = conversation.updated_at
    embedding_provider = RecordingEmbeddingProvider()
    vector_store = RecordingVectorStore(results=(make_search_result(),))
    llm_provider = RecordingLLMProvider()
    service = make_service(
        session,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        llm_provider=llm_provider,
    )

    result = asyncio.run(
        service.chat(
            RagChatRequest(
                conversation_id=conversation_id,
                knowledge_base_id=KNOWLEDGE_BASE_ID,
                provider="openai_compatible",
                model="example-model",
                query="What is the architecture?",
                top_k=3,
                score_threshold=0.5,
                temperature=0.1,
                max_tokens=256,
            )
        )
    )

    assert result.answer == "Grounded answer [1]"
    assert result.sources[0].source_index == 1
    assert result.sources[0].chunk_id == CHUNK_ID
    assert result.metadata.result_count == 1
    assert result.metadata.used_source_count == 1
    assert result.metadata.context_characters > 0
    assert result.provider == "openai_compatible"
    assert result.model == "resolved-model"
    assert result.usage == TokenUsage(
        input_tokens=9,
        output_tokens=4,
        total_tokens=13,
    )
    assert len(llm_provider.requests) == 1
    provider_request = llm_provider.requests[0]
    assert provider_request.model == "example-model"
    assert provider_request.temperature == 0.1
    assert provider_request.max_tokens == 256
    assert [message.role for message in provider_request.messages] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert [
        message.content for message in provider_request.messages[1:3]
    ] == ["Earlier question", "Earlier answer"]
    assert provider_request.messages[-1].content is not None
    assert "[1] 文件：guide.md" in provider_request.messages[-1].content
    assert provider_request.messages[-1].content.endswith(
        "【用户问题】\nWhat is the architecture?"
    )

    messages = session.scalars(
        select(Message).order_by(Message.created_at, Message.id)
    ).all()
    assert [(message.role, message.content) for message in messages] == [
        ("user", "Earlier question"),
        ("assistant", "Earlier answer"),
        ("user", "What is the architecture?"),
        ("assistant", "Grounded answer [1]"),
    ]
    llm_calls = session.scalars(select(LLMCall)).all()
    assert llm_calls == [result.llm_call]
    assert result.llm_call.message_id == result.assistant_message.id
    assert result.llm_call.conversation_id == conversation_id
    assert result.llm_call.input_tokens == 9
    assert result.llm_call.output_tokens == 4
    assert result.llm_call.total_tokens == 13
    assert result.llm_call.estimated_cost == Decimal("0.00001050")
    rag_queries = session.scalars(select(RagQuery)).all()
    assert rag_queries == [result.rag_query]
    assert result.rag_query.conversation_id == conversation_id
    assert result.rag_query.answer_message_id == result.assistant_message.id
    assert result.rag_query.top_k == 3
    assert result.rag_query.retrieved_chunks_json[0]["source_index"] == 1
    assert result.rag_query.retrieved_chunks_json[0]["chunk_id"] == str(
        CHUNK_ID
    )
    assert result.rag_query.latency_ms is not None

    session.refresh(conversation)
    assert conversation.default_provider == "openai_compatible"
    assert conversation.default_model == "example-model"
    assert conversation.updated_at > previous_updated_at
    assert result.conversation.id == conversation_id
    assert result.user_message.content == "What is the architecture?"

    session.close()
    engine.dispose()


def test_rag_chat_calls_llm_with_no_source_marker_for_zero_hits(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    conversation = seed_knowledge_and_conversation(session)
    embedding_provider = RecordingEmbeddingProvider()
    vector_store = RecordingVectorStore()
    llm_provider = RecordingLLMProvider()
    service = make_service(
        session,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        llm_provider=llm_provider,
    )

    result = asyncio.run(
        service.chat(
            RagChatRequest(
                conversation_id=conversation.id,
                knowledge_base_id=KNOWLEDGE_BASE_ID,
                provider="openai_compatible",
                model="example-model",
                query="Unknown answer",
            )
        )
    )

    assert result.sources == ()
    assert result.metadata.result_count == 0
    assert result.metadata.used_source_count == 0
    assert llm_provider.requests[0].messages[-1].content is not None
    assert "（无可用资料片段）" in (
        llm_provider.requests[0].messages[-1].content
    )

    session.close()
    engine.dispose()


def test_rag_chat_rejects_unknown_model_before_writes_or_embedding(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    conversation = seed_knowledge_and_conversation(session)
    embedding_provider = RecordingEmbeddingProvider()
    vector_store = RecordingVectorStore()
    llm_provider = RecordingLLMProvider()
    service = make_service(
        session,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        llm_provider=llm_provider,
    )

    with pytest.raises(ChatModelNotFoundError):
        asyncio.run(
            service.chat(
                RagChatRequest(
                    conversation_id=conversation.id,
                    knowledge_base_id=KNOWLEDGE_BASE_ID,
                    provider="openai_compatible",
                    model="missing-model",
                    query="Question",
                )
            )
        )

    assert embedding_provider.queries == []
    assert llm_provider.requests == []
    assert session.scalar(select(func.count()).select_from(Message)) == 0

    session.close()
    engine.dispose()


def test_rag_chat_rejects_unavailable_provider_before_writes_or_embedding(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    conversation = seed_knowledge_and_conversation(session)
    embedding_provider = RecordingEmbeddingProvider()
    vector_store = RecordingVectorStore()
    service = RagService(
        session,
        retriever=Retriever(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
        ),
        prompt_builder=RagPromptBuilder(),
        registry=make_registry(),
        providers={},
    )

    with pytest.raises(ChatProviderUnavailableError):
        asyncio.run(
            service.chat(
                RagChatRequest(
                    conversation_id=conversation.id,
                    knowledge_base_id=KNOWLEDGE_BASE_ID,
                    provider="openai_compatible",
                    model="example-model",
                    query="Question",
                )
            )
        )

    assert embedding_provider.queries == []
    assert session.scalar(select(func.count()).select_from(Message)) == 0

    session.close()
    engine.dispose()


def test_rag_chat_rejects_missing_conversation_before_embedding(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    session.add(KnowledgeBase(id=KNOWLEDGE_BASE_ID, name="Project docs"))
    session.commit()
    embedding_provider = RecordingEmbeddingProvider()
    vector_store = RecordingVectorStore()
    llm_provider = RecordingLLMProvider()
    service = make_service(
        session,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        llm_provider=llm_provider,
    )

    with pytest.raises(ConversationNotFoundError):
        asyncio.run(
            service.chat(
                RagChatRequest(
                    conversation_id=UUID(int=99),
                    knowledge_base_id=KNOWLEDGE_BASE_ID,
                    provider="openai_compatible",
                    model="example-model",
                    query="Question",
                )
            )
        )

    assert embedding_provider.queries == []
    assert llm_provider.requests == []

    session.close()
    engine.dispose()


def test_rag_chat_rolls_back_new_user_message_when_retrieval_fails(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    conversation = seed_knowledge_and_conversation(session, with_history=True)
    error = EmbeddingProviderResponseError("synthetic embedding failure")
    embedding_provider = RecordingEmbeddingProvider(fail_with=error)
    vector_store = RecordingVectorStore()
    llm_provider = RecordingLLMProvider()
    service = make_service(
        session,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        llm_provider=llm_provider,
    )

    with pytest.raises(EmbeddingProviderResponseError) as raised:
        asyncio.run(
            service.chat(
                RagChatRequest(
                    conversation_id=conversation.id,
                    knowledge_base_id=KNOWLEDGE_BASE_ID,
                    provider="openai_compatible",
                    model="example-model",
                    query="Failed question",
                )
            )
        )

    assert raised.value is error
    assert llm_provider.requests == []
    messages = session.scalars(
        select(Message).order_by(Message.created_at, Message.id)
    ).all()
    assert [message.content for message in messages] == [
        "Earlier question",
        "Earlier answer",
    ]
    assert session.scalar(select(func.count()).select_from(LLMCall)) == 0
    assert session.scalar(select(func.count()).select_from(RagQuery)) == 0

    session.close()
    engine.dispose()


@pytest.mark.parametrize(
    "llm_provider",
    [
        FailingLLMProvider(
            ProviderRequestError("synthetic provider failure", status_code=503)
        ),
        ToolOnlyLLMProvider(),
        BlankLLMProvider(),
    ],
)
def test_rag_chat_rolls_back_new_user_message_for_invalid_llm_completion(
    tmp_path: Path,
    llm_provider: RecordingLLMProvider,
) -> None:
    session, engine = create_test_session(tmp_path)
    conversation = seed_knowledge_and_conversation(session, with_history=True)
    service = make_service(
        session,
        embedding_provider=RecordingEmbeddingProvider(),
        vector_store=RecordingVectorStore(results=(make_search_result(),)),
        llm_provider=llm_provider,
    )

    with pytest.raises((ProviderRequestError, ProviderResponseError)):
        asyncio.run(
            service.chat(
                RagChatRequest(
                    conversation_id=conversation.id,
                    knowledge_base_id=KNOWLEDGE_BASE_ID,
                    provider="openai_compatible",
                    model="example-model",
                    query="Failed question",
                )
            )
        )

    messages = session.scalars(
        select(Message).order_by(Message.created_at, Message.id)
    ).all()
    assert [message.content for message in messages] == [
        "Earlier question",
        "Earlier answer",
    ]
    assert session.scalar(select(func.count()).select_from(LLMCall)) == 0
    assert session.scalar(select(func.count()).select_from(RagQuery)) == 0

    session.close()
    engine.dispose()
