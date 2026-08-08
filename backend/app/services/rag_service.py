from collections.abc import Mapping
from dataclasses import dataclass
from time import perf_counter
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Conversation, KnowledgeBase, LLMCall, Message, RagQuery
from app.observability.llm_trace import LLMTraceCall, LLMTraceRecorder
from app.observability.prompt_version import NAIVE_RAG_PROMPT_VERSION
from app.observability.trace_types import TraceRunType
from app.providers.llm.base import (
    BaseLLMProvider,
    ChatMessage,
    ChatRequest,
    LLMProviderError,
    LLMResponse,
    ProviderResponseError,
    TokenUsage,
)
from app.providers.llm.registry import ModelRegistry
from app.rag.rag_prompt import RagPromptBuilder
from app.rag.retrieval_recorder import (
    RAGRecordedRetrieval,
    RAGTraceRecorder,
    RAGTraceRun,
)
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
    retrieval_audit: RAGRecordedRetrieval | None = None


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
        trace_enabled: bool = True,
    ) -> None:
        self._session = session
        self._retriever = retriever
        self._trace_enabled = trace_enabled
        self._rag_traces = RAGTraceRecorder(session)

    async def query(self, request: RagRetrievalRequest) -> RagQueryResult:
        self._get_knowledge_base(request.knowledge_base_id)
        if not self._trace_enabled:
            return await self._execute_query(request, trace_run=None)
        trace_run = self._rag_traces.start_query_run(request)
        result = await self._execute_query(request, trace_run=trace_run)
        self._rag_traces.finish_query(trace_run)
        return result

    async def _execute_query(
        self,
        request: RagRetrievalRequest,
        *,
        trace_run: RAGTraceRun | None,
    ) -> RagQueryResult:
        started = perf_counter()
        retrieval_trace = (
            None
            if trace_run is None
            else self._rag_traces.start_retrieval(trace_run, request)
        )
        try:
            batch = await self._retriever.retrieve_batch(
                query=request.query,
                knowledge_base_id=request.knowledge_base_id,
                top_k=request.top_k,
                score_threshold=request.score_threshold,
            )
        except Exception as exc:
            if retrieval_trace is not None:
                self._rag_traces.persist_retrieval_failure(
                    retrieval_trace,
                    error=exc,
                )
            raise
        latency_ms = max(0, int((perf_counter() - started) * 1000))
        results = batch.results
        retrieval_audit = (
            None
            if retrieval_trace is None
            else self._rag_traces.complete_retrieval(
                retrieval_trace,
                batch=batch,
                latency_ms=latency_ms,
            )
        )
        rag_query = RagQuery(
            knowledge_base_id=request.knowledge_base_id,
            query=request.query,
            top_k=request.top_k,
            retrieved_chunks_json=_snapshot_retrieval_results(results),
            latency_ms=latency_ms,
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
            retrieval_audit=retrieval_audit,
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
        self._llm_traces = LLMTraceRecorder(session)

    async def chat(self, request: RagChatRequest) -> RagChatResult:
        trace_call: LLMTraceCall | None = None
        recorded_prompt = None
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
            trace_run = self._llm_traces.start_run(
                run_type=TraceRunType.RAG_CHAT,
                input_text=request.query,
                provider=request.provider,
                requested_model=request.model,
                prompt_version=NAIVE_RAG_PROMPT_VERSION,
                stream=False,
                conversation_id=conversation.id,
                user_message_id=user_message.id,
            )
            persisted_history = self._conversations.list_messages(
                conversation.id
            )
            rag_trace_run = self._rag_traces.attach_run(trace_run.record)
            retrieval = await self._execute_query(
                request,
                trace_run=rag_trace_run,
            )
            retrieval_results = retrieval.results
            if retrieval.retrieval_audit is None:
                raise RuntimeError("RAG Chat retrieval audit was not recorded")
            prompt_trace = self._rag_traces.start_prompt(
                retrieval.retrieval_audit,
                prompt_version=NAIVE_RAG_PROMPT_VERSION,
            )
            prompt = self._prompt_builder.build(
                query=request.query,
                retrieval_results=retrieval_results,
                history=tuple(
                    ChatMessage(role=message.role, content=message.content)
                    for message in persisted_history[:-1]
                ),
            )
            recorded_prompt = self._rag_traces.complete_prompt(
                prompt_trace,
                prompt=prompt,
            )
            provider_request = ChatRequest(
                messages=list(prompt.messages),
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            trace_call = self._llm_traces.start_call(
                trace_run,
                message_count=len(provider_request.messages),
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
            self._llm_traces.complete_call(
                trace_call,
                response_model=response.model,
                metrics=metrics,
                output_text=response.content,
                finish_run=False,
            )
            final_trace = self._rag_traces.start_final_answer(recorded_prompt)
            self._rag_traces.complete_final_answer(
                final_trace,
                rag_query_id=retrieval.rag_query.id,
                answer_message_id=assistant_message.id,
                llm_call_id=llm_call.id,
                answer_text=response.content,
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
        except Exception as exc:
            if isinstance(exc, LLMProviderError) and trace_call is not None:
                before_failed_call = (
                    None
                    if recorded_prompt is None
                    else lambda failed_run: (
                        self._rag_traces.replay_completed_before_llm(
                            failed_run.record,
                            recorded_prompt,
                        )
                    )
                )
                self._llm_traces.persist_failure(
                    trace_call,
                    error=exc,
                    conversation_id=request.conversation_id,
                    before_failed_call=before_failed_call,
                )
            else:
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
