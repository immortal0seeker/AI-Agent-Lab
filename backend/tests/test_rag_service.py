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
from app.models import (
    Conversation,
    KnowledgeBase,
    LLMCall,
    Message,
    RagQuery,
    RagRetrievalCandidate,
    RagRetrievalRun,
    TraceRun,
    TraceStep,
)
from app.observability.trace_types import (
    TraceRunType,
    TraceStatus,
    TraceStepType,
)
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
from app.services.rag_service import RagQueryService, RagService


KNOWLEDGE_BASE_ID = UUID("11111111-1111-1111-1111-111111111111")
DOCUMENT_ID = UUID("22222222-2222-2222-2222-222222222222")
CHUNK_ID = UUID("33333333-3333-3333-3333-333333333333")
SECOND_DOCUMENT_ID = UUID("44444444-4444-4444-4444-444444444444")
SECOND_CHUNK_ID = UUID("55555555-5555-5555-5555-555555555555")


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
    document_id: UUID = DOCUMENT_ID,
    chunk_id: UUID = CHUNK_ID,
    chunk_index: int = 0,
    score: float = 0.92,
) -> VectorSearchResult:
    return VectorSearchResult(
        point_id=chunk_id,
        score=score,
        payload=ChunkVectorPayload(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            document_id=document_id,
            chunk_id=chunk_id,
            embedding_provider="recording",
            embedding_model="synthetic-embedding",
            filename="guide.md",
            chunk_index=chunk_index,
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
            embedding_provider="recording",
            embedding_model="synthetic-embedding",
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
    assert stored.retrieved_chunks_json[0]["embedding_provider"] == "recording"
    assert stored.retrieved_chunks_json[0]["embedding_model"] == (
        "synthetic-embedding"
    )
    assert stored.retrieved_chunks_json[0]["content"] == (
        "The workspace uses layered services."
    )
    trace_run = session.scalar(select(TraceRun))
    trace_step = session.scalar(select(TraceStep))
    retrieval_run = session.scalar(select(RagRetrievalRun))
    candidate = session.scalar(select(RagRetrievalCandidate))
    assert trace_run is not None
    assert trace_run.run_type == TraceRunType.RAG_QUERY.value
    assert trace_run.status == TraceStatus.COMPLETED.value
    assert trace_run.output_text is None
    assert trace_step is not None
    assert trace_step.step_type == TraceStepType.RAG_RETRIEVE.value
    assert trace_step.status == TraceStatus.COMPLETED.value
    assert retrieval_run is not None
    assert retrieval_run.trace_run_id == trace_run.id
    assert retrieval_run.candidate_count == 1
    assert retrieval_run.metadata_filter_json["embedding_model"] == (
        "synthetic-embedding"
    )
    assert candidate is not None
    assert candidate.retrieval_run_id == retrieval_run.id
    assert candidate.chunk_id == CHUNK_ID
    assert candidate.rank == 1
    assert candidate.final_rank == 1
    assert candidate.dense_score == 0.92

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
    trace_run = session.scalar(select(TraceRun))
    retrieval_run = session.scalar(select(RagRetrievalRun))
    assert trace_run is not None
    assert trace_run.run_type == TraceRunType.RAG_QUERY.value
    assert trace_run.status == TraceStatus.COMPLETED.value
    assert retrieval_run is not None
    assert retrieval_run.top_k == 9
    assert retrieval_run.candidate_count == 0
    assert retrieval_run.selected_count == 0
    assert retrieval_run.metadata_filter_json["embedding_provider"] == (
        "recording"
    )
    assert retrieval_run.metadata_filter_json["embedding_model"] == (
        "synthetic-embedding"
    )
    assert session.scalar(
        select(func.count()).select_from(RagRetrievalCandidate)
    ) == 0

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
    assert session.scalar(select(func.count()).select_from(TraceRun)) == 0

    session.close()
    engine.dispose()


def test_rag_query_persists_safe_failed_trace_when_retrieval_fails(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    session.add(KnowledgeBase(id=KNOWLEDGE_BASE_ID, name="Project docs"))
    session.commit()
    error = EmbeddingProviderResponseError(
        "private embedding diagnostic synthetic-secret"
    )
    service = make_service(
        session,
        embedding_provider=RecordingEmbeddingProvider(fail_with=error),
        vector_store=RecordingVectorStore(),
        llm_provider=RecordingLLMProvider(),
    )

    request = RagRetrievalRequest(
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        query="Failed retrieval question",
    )
    with pytest.raises(EmbeddingProviderResponseError) as raised:
        asyncio.run(
            service.query(request)
        )

    assert raised.value is error
    assert session.scalar(select(func.count()).select_from(RagQuery)) == 0
    assert session.scalar(
        select(func.count()).select_from(RagRetrievalRun)
    ) == 0
    assert session.scalar(
        select(func.count()).select_from(RagRetrievalCandidate)
    ) == 0
    trace_run = session.scalar(select(TraceRun))
    trace_step = session.scalar(select(TraceStep))
    assert trace_run is not None
    assert trace_run.run_type == TraceRunType.RAG_QUERY.value
    assert trace_run.status == TraceStatus.FAILED.value
    assert trace_run.input_text == request.query
    assert trace_run.error_message == "EmbeddingProviderResponseError"
    assert trace_step is not None
    assert trace_step.step_type == TraceStepType.RAG_RETRIEVE.value
    assert trace_step.status == TraceStatus.FAILED.value
    assert trace_step.error_message == "EmbeddingProviderResponseError"
    assert "private embedding diagnostic" not in repr(trace_run.__dict__)
    assert "synthetic-secret" not in repr(trace_step.__dict__)

    session.close()
    engine.dispose()


def test_untraced_rag_query_success_keeps_legacy_tool_audit_only(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    session.add(KnowledgeBase(id=KNOWLEDGE_BASE_ID, name="Project docs"))
    session.commit()
    service = RagQueryService(
        session,
        retriever=Retriever(
            embedding_provider=RecordingEmbeddingProvider(),
            vector_store=RecordingVectorStore(results=(make_search_result(),)),
        ),
        trace_enabled=False,
    )

    result = asyncio.run(
        service.query(
            RagRetrievalRequest(
                knowledge_base_id=KNOWLEDGE_BASE_ID,
                query="Tool retrieval",
            )
        )
    )

    assert result.rag_query is session.scalar(select(RagQuery))
    assert session.scalar(select(func.count()).select_from(TraceRun)) == 0
    assert session.scalar(
        select(func.count()).select_from(RagRetrievalRun)
    ) == 0

    session.close()
    engine.dispose()


def test_untraced_rag_query_failure_does_not_own_caller_transaction(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    session.add(KnowledgeBase(id=KNOWLEDGE_BASE_ID, name="Project docs"))
    session.commit()
    provisional = Conversation(title="Agent-owned transaction")
    session.add(provisional)
    session.flush()
    error = EmbeddingProviderResponseError("synthetic failure")
    service = RagQueryService(
        session,
        retriever=Retriever(
            embedding_provider=RecordingEmbeddingProvider(fail_with=error),
            vector_store=RecordingVectorStore(),
        ),
        trace_enabled=False,
    )

    with pytest.raises(EmbeddingProviderResponseError):
        asyncio.run(
            service.query(
                RagRetrievalRequest(
                    knowledge_base_id=KNOWLEDGE_BASE_ID,
                    query="Failed Tool retrieval",
                )
            )
        )

    assert session.get(Conversation, provisional.id) is provisional
    assert session.scalar(select(func.count()).select_from(TraceRun)) == 0

    session.rollback()
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
    trace_runs = session.scalars(select(TraceRun)).all()
    trace_steps = session.scalars(select(TraceStep)).all()
    assert len(trace_runs) == 1
    assert len(trace_steps) == 4
    trace_run = trace_runs[0]
    retrieval_step, prompt_step, llm_step, final_step = trace_steps
    assert trace_run.run_type == TraceRunType.RAG_CHAT.value
    assert trace_run.status == TraceStatus.COMPLETED.value
    assert trace_run.conversation_id == conversation_id
    assert trace_run.user_message_id == result.user_message.id
    assert trace_run.metadata_json == {
        "prompt_version": "naive-rag-v1",
        "stream": False,
    }
    assert trace_run.provider == "openai_compatible"
    assert trace_run.model == "resolved-model"
    assert trace_run.total_tokens == 13
    assert trace_run.estimated_cost == Decimal("0.00001050")
    assert retrieval_step.trace_run_id == trace_run.id
    assert retrieval_step.step_type == TraceStepType.RAG_RETRIEVE.value
    assert retrieval_step.status == TraceStatus.COMPLETED.value
    assert prompt_step.step_type == TraceStepType.BUILD_PROMPT.value
    assert prompt_step.status == TraceStatus.COMPLETED.value
    assert llm_step.trace_run_id == trace_run.id
    assert llm_step.step_type == TraceStepType.LLM_CALL.value
    assert llm_step.status == TraceStatus.COMPLETED.value
    assert llm_step.input_json["message_count"] == len(
        llm_provider.requests[0].messages
    )
    assert llm_step.input_json["prompt_version"] == "naive-rag-v1"
    assert llm_step.output_json is not None
    assert llm_step.output_json["usage"]["total_tokens"] == 13
    retrieval_run = session.scalar(select(RagRetrievalRun))
    candidate = session.scalar(select(RagRetrievalCandidate))
    assert retrieval_run is not None
    assert retrieval_run.trace_run_id == trace_run.id
    assert candidate is not None
    assert candidate.chunk_id == CHUNK_ID
    assert prompt_step.input_json == {
        "prompt_version": "naive-rag-v1",
        "retrieval_run_id": str(retrieval_run.id),
        "candidate_count": 1,
    }
    assert prompt_step.output_json is not None
    assert prompt_step.output_json["prompt_version"] == "naive-rag-v1"
    assert prompt_step.output_json["used_source_count"] == 1
    assert prompt_step.output_json["sources"] == [
        {
            "source_index": 1,
            "candidate_id": str(candidate.id),
            "document_id": str(DOCUMENT_ID),
            "chunk_id": str(CHUNK_ID),
            "included_characters": len(result.sources[0].content),
            "truncated": False,
        }
    ]
    assert final_step.step_type == TraceStepType.FINAL_ANSWER.value
    assert final_step.status == TraceStatus.COMPLETED.value
    assert final_step.input_json == {
        "prompt_version": "naive-rag-v1",
        "retrieval_run_id": str(retrieval_run.id),
        "used_source_count": 1,
    }
    assert final_step.output_json == {
        "rag_query_id": str(result.rag_query.id),
        "answer_message_id": str(result.assistant_message.id),
        "llm_call_id": str(result.llm_call.id),
        "source_count": 1,
        "answer_characters": len(result.answer),
    }

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
    retrieval_run = session.scalar(select(RagRetrievalRun))
    assert retrieval_run is not None
    assert retrieval_run.candidate_count == 0
    assert session.scalar(
        select(func.count()).select_from(RagRetrievalCandidate)
    ) == 0
    trace_steps = session.scalars(
        select(TraceStep).order_by(TraceStep.step_index)
    ).all()
    assert [step.step_type for step in trace_steps] == [
        TraceStepType.RAG_RETRIEVE.value,
        TraceStepType.BUILD_PROMPT.value,
        TraceStepType.LLM_CALL.value,
        TraceStepType.FINAL_ANSWER.value,
    ]
    assert trace_steps[1].output_json is not None
    assert trace_steps[1].output_json["sources"] == []
    assert trace_steps[3].output_json is not None
    assert trace_steps[3].output_json["source_count"] == 0

    session.close()
    engine.dispose()


def test_rag_chat_trace_maps_prompt_subset_under_context_budget(
    tmp_path: Path,
) -> None:
    session, engine = create_test_session(tmp_path)
    conversation = seed_knowledge_and_conversation(session)
    service = make_service(
        session,
        embedding_provider=RecordingEmbeddingProvider(),
        vector_store=RecordingVectorStore(
            results=(
                make_search_result(content="A" * 400),
                make_search_result(
                    content="B" * 40,
                    document_id=SECOND_DOCUMENT_ID,
                    chunk_id=SECOND_CHUNK_ID,
                    chunk_index=1,
                    score=0.81,
                ),
            )
        ),
        llm_provider=RecordingLLMProvider(),
        max_context_characters=128,
    )

    result = asyncio.run(
        service.chat(
            RagChatRequest(
                conversation_id=conversation.id,
                knowledge_base_id=KNOWLEDGE_BASE_ID,
                provider="openai_compatible",
                model="example-model",
                query="Budgeted question",
            )
        )
    )

    candidates = session.scalars(
        select(RagRetrievalCandidate).order_by(RagRetrievalCandidate.rank)
    ).all()
    prompt_step = session.scalar(
        select(TraceStep).where(
            TraceStep.step_type == TraceStepType.BUILD_PROMPT.value
        )
    )
    assert len(candidates) == 2
    assert len(result.sources) == 1
    assert prompt_step is not None
    assert prompt_step.output_json is not None
    assert prompt_step.output_json["used_source_count"] == 1
    assert prompt_step.output_json["sources"] == [
        {
            "source_index": 1,
            "candidate_id": str(candidates[0].id),
            "document_id": str(DOCUMENT_ID),
            "chunk_id": str(CHUNK_ID),
            "included_characters": len(result.sources[0].content),
            "truncated": True,
        }
    ]
    assert "A" * 40 not in repr(prompt_step.output_json)
    assert "B" * 20 not in repr(prompt_step.output_json)

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
    trace_run = session.scalar(select(TraceRun))
    trace_step = session.scalar(select(TraceStep))
    assert trace_run is not None
    assert trace_run.run_type == TraceRunType.RAG_CHAT.value
    assert trace_run.status == TraceStatus.FAILED.value
    assert trace_run.conversation_id == conversation.id
    assert trace_run.user_message_id is None
    assert trace_run.error_message == "EmbeddingProviderResponseError"
    assert trace_step is not None
    assert trace_step.step_type == TraceStepType.RAG_RETRIEVE.value
    assert trace_step.status == TraceStatus.FAILED.value
    assert trace_step.error_message == "EmbeddingProviderResponseError"
    assert session.scalar(
        select(func.count()).select_from(RagRetrievalRun)
    ) == 0
    assert session.scalar(
        select(func.count()).select_from(RagRetrievalCandidate)
    ) == 0

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
    trace_runs = session.scalars(select(TraceRun)).all()
    trace_steps = session.scalars(
        select(TraceStep).order_by(TraceStep.step_index)
    ).all()
    assert len(trace_runs) == 1
    assert len(trace_steps) == 3
    trace_run = trace_runs[0]
    retrieval_step, prompt_step, llm_step = trace_steps
    expected_error = (
        "ProviderRequestError"
        if isinstance(llm_provider, FailingLLMProvider)
        else "ProviderResponseError"
    )
    assert trace_run.run_type == TraceRunType.RAG_CHAT.value
    assert trace_run.status == TraceStatus.FAILED.value
    assert trace_run.conversation_id == conversation.id
    assert trace_run.user_message_id is None
    assert trace_run.error_message == expected_error
    assert retrieval_step.step_type == TraceStepType.RAG_RETRIEVE.value
    assert retrieval_step.status == TraceStatus.COMPLETED.value
    assert prompt_step.step_type == TraceStepType.BUILD_PROMPT.value
    assert prompt_step.status == TraceStatus.COMPLETED.value
    assert llm_step.step_type == TraceStepType.LLM_CALL.value
    assert llm_step.status == TraceStatus.FAILED.value
    assert llm_step.error_message == expected_error
    assert llm_step.output_json is None
    retrieval_run = session.scalar(select(RagRetrievalRun))
    candidate = session.scalar(select(RagRetrievalCandidate))
    assert retrieval_run is not None
    assert retrieval_run.trace_run_id == trace_run.id
    assert retrieval_run.candidate_count == 1
    assert candidate is not None
    assert candidate.retrieval_run_id == retrieval_run.id
    assert candidate.chunk_id == CHUNK_ID
    assert prompt_step.output_json is not None
    assert prompt_step.output_json["sources"][0]["candidate_id"] == str(
        candidate.id
    )
    assert trace_run.output_text is None
    assert "synthetic provider failure" not in repr(
        (
            trace_run.metadata_json,
            trace_run.error_message,
            [step.input_json for step in trace_steps],
            [step.output_json for step in trace_steps],
            [step.error_message for step in trace_steps],
            candidate.metadata_json,
        )
    )

    session.close()
    engine.dispose()
