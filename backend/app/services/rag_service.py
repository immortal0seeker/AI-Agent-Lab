from collections.abc import Mapping
from dataclasses import dataclass
from time import perf_counter
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Conversation, KnowledgeBase, LLMCall, Message, RagQuery
from app.providers.llm.base import (
    BaseLLMProvider,
    ChatMessage,
    ChatRequest,
    LLMResponse,
    ProviderResponseError,
    TokenUsage,
)
from app.providers.llm.registry import ModelRegistry
from app.rag.rag_prompt import RagPromptBuilder
from app.rag.retriever import Retriever
from app.schemas.message import MessageCreate
from app.schemas.rag import (
    RagAnswerMetadata,
    RagChatRequest,
    RagRetrievalMetadata,
    RagRetrievalRequest,
    RagSource,
    RetrievalResult,
)
from app.services.conversation_service import ConversationService
from app.services.errors import (
    ChatModelNotFoundError,
    ChatProviderUnavailableError,
    KnowledgeBaseNotFoundError,
)
from app.services.llm_usage import ProviderLatencyTimer, build_llm_call_metrics


@dataclass(frozen=True, slots=True)
class RagQueryResult:
    rag_query: RagQuery
    results: tuple[RetrievalResult, ...]
    metadata: RagRetrievalMetadata


@dataclass(frozen=True, slots=True)
class RagChatResult:
    conversation: Conversation
    user_message: Message
    assistant_message: Message
    llm_call: LLMCall
    rag_query: RagQuery
    answer: str
    sources: tuple[RagSource, ...]
    metadata: RagAnswerMetadata
    provider: str
    model: str
    usage: TokenUsage | None


class RagQueryService:
    def __init__(
        self,
        session: Session,
        *,
        retriever: Retriever,
    ) -> None:
        self._session = session
        self._retriever = retriever

    async def query(self, request: RagRetrievalRequest) -> RagQueryResult:
        self._get_knowledge_base(request.knowledge_base_id)
        started = perf_counter()
        results = await self._retriever.retrieve(
            query=request.query,
            knowledge_base_id=request.knowledge_base_id,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
        )
        rag_query = RagQuery(
            knowledge_base_id=request.knowledge_base_id,
            query=request.query,
            top_k=request.top_k,
            retrieved_chunks_json=_snapshot_retrieval_results(results),
            latency_ms=max(0, int((perf_counter() - started) * 1000)),
        )
        self._session.add(rag_query)
        self._session.flush()
        return RagQueryResult(
            rag_query=rag_query,
            results=results,
            metadata=RagRetrievalMetadata(
                knowledge_base_id=request.knowledge_base_id,
                top_k=request.top_k,
                score_threshold=request.score_threshold,
                result_count=len(results),
            ),
        )

    def _get_knowledge_base(self, knowledge_base_id: UUID) -> KnowledgeBase:
        knowledge_base = self._session.get(KnowledgeBase, knowledge_base_id)
        if knowledge_base is None:
            raise KnowledgeBaseNotFoundError(knowledge_base_id)
        return knowledge_base


class RagService(RagQueryService):
    def __init__(
        self,
        session: Session,
        *,
        retriever: Retriever,
        prompt_builder: RagPromptBuilder,
        registry: ModelRegistry,
        providers: Mapping[str, BaseLLMProvider],
    ) -> None:
        super().__init__(session, retriever=retriever)
        self._prompt_builder = prompt_builder
        self._registry = registry
        self._providers = providers
        self._conversations = ConversationService(session)

    async def chat(self, request: RagChatRequest) -> RagChatResult:
        try:
            model_info = self._registry.get_model(
                request.provider,
                request.model,
            )
            if model_info is None:
                raise ChatModelNotFoundError(
                    request.provider,
                    request.model,
                )
            provider = self._providers.get(request.provider)
            if provider is None:
                raise ChatProviderUnavailableError(request.provider)

            self._get_knowledge_base(request.knowledge_base_id)
            conversation = self._conversations.get_conversation(
                request.conversation_id
            )
            user_message = self._conversations.append_message(
                MessageCreate(
                    conversation_id=conversation.id,
                    role="user",
                    content=request.query,
                )
            )
            persisted_history = self._conversations.list_messages(
                conversation.id
            )
            retrieval = await super().query(request)
            retrieval_results = retrieval.results
            prompt = self._prompt_builder.build(
                query=request.query,
                retrieval_results=retrieval_results,
                history=tuple(
                    ChatMessage(role=message.role, content=message.content)
                    for message in persisted_history[:-1]
                ),
            )
            provider_request = ChatRequest(
                messages=list(prompt.messages),
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            timer = ProviderLatencyTimer()
            with timer.measure():
                response = await provider.chat(provider_request)
            if (
                not isinstance(response, LLMResponse)
                or response.content is None
                or not response.content.strip()
            ):
                raise ProviderResponseError(
                    "Provider response did not contain RAG answer text"
                )

            metrics = build_llm_call_metrics(
                usage=response.usage,
                model_info=model_info,
                latency_ms=timer.latency_ms,
            )
            assistant_message = self._conversations.append_message(
                MessageCreate(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=response.content,
                    provider=request.provider,
                    model=response.model,
                )
            )
            llm_call = LLMCall(
                conversation_id=conversation.id,
                message_id=assistant_message.id,
                provider=request.provider,
                model=response.model,
                input_tokens=metrics.input_tokens,
                output_tokens=metrics.output_tokens,
                total_tokens=metrics.total_tokens,
                estimated_cost=metrics.estimated_cost,
                latency_ms=metrics.latency_ms,
                status="completed",
            )
            self._session.add(llm_call)
            self._session.flush()
            retrieval.rag_query.conversation_id = conversation.id
            retrieval.rag_query.answer_message_id = assistant_message.id
            self._conversations.record_successful_turn(
                conversation,
                provider=request.provider,
                model=request.model,
            )
            return RagChatResult(
                conversation=conversation,
                user_message=user_message,
                assistant_message=assistant_message,
                llm_call=llm_call,
                rag_query=retrieval.rag_query,
                answer=response.content,
                sources=prompt.sources,
                metadata=RagAnswerMetadata(
                    knowledge_base_id=request.knowledge_base_id,
                    top_k=request.top_k,
                    score_threshold=request.score_threshold,
                    result_count=len(retrieval_results),
                    used_source_count=len(prompt.sources),
                    context_characters=prompt.context_characters,
                ),
                provider=request.provider,
                model=response.model,
                usage=response.usage,
            )
        except Exception:
            self._session.rollback()
            raise


def _snapshot_retrieval_results(
    results: tuple[RetrievalResult, ...],
) -> list[dict[str, object]]:
    snapshots: list[dict[str, object]] = []
    for source_index, result in enumerate(results, start=1):
        snapshot = result.model_dump(mode="json")
        snapshot["source_index"] = source_index
        snapshots.append(snapshot)
    return snapshots
