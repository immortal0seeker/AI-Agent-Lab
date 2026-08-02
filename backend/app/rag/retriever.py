from copy import deepcopy
from math import isfinite
from uuid import UUID

from app.providers.embedding import EmbeddingProvider, EmbeddingResult
from app.rag.vectorstores import (
    VectorSearchQuery,
    VectorSearchResult,
    VectorStore,
)
from app.schemas.rag import RetrievalResult


class RetrieverError(RuntimeError):
    """基础 Retriever 边界异常。"""


class RetrieverInputError(RetrieverError):
    """Retriever 输入不满足本地约束。"""


class RetrieverResponseError(RetrieverError):
    """Retriever 收到不可信的组合边界响应。"""


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
        _validate_retrieval_input(
            query=query,
            knowledge_base_id=knowledge_base_id,
            top_k=top_k,
            score_threshold=score_threshold,
        )
        embedding = await self._embedding_provider.embed_query(query)
        if (
            not isinstance(embedding, EmbeddingResult)
            or len(embedding.vectors) != 1
            or embedding.dimension != self._vector_store.dimension
        ):
            raise RetrieverResponseError(
                "Retriever query embedding response is invalid."
            ) from None
        search_results = await self._vector_store.search(
            VectorSearchQuery(
                knowledge_base_id=knowledge_base_id,
                embedding_provider=self._embedding_provider.name,
                embedding_model=embedding.model,
                vector=embedding.vectors[0],
                limit=top_k,
                score_threshold=score_threshold,
            )
        )
        if (
            not isinstance(search_results, tuple)
            or len(search_results) > top_k
            or any(
                not isinstance(result, VectorSearchResult)
                or result.payload.knowledge_base_id != knowledge_base_id
                or result.payload.embedding_provider
                != self._embedding_provider.name
                or result.payload.embedding_model != embedding.model
                or (
                    score_threshold is not None
                    and result.score < score_threshold
                )
                for result in search_results
            )
        ):
            raise RetrieverResponseError(
                "Retriever vector search response is invalid."
            ) from None
        return tuple(
            _to_retrieval_result(result) for result in search_results
        )


def _to_retrieval_result(result: VectorSearchResult) -> RetrievalResult:
    payload = result.payload
    return RetrievalResult(
        knowledge_base_id=payload.knowledge_base_id,
        document_id=payload.document_id,
        chunk_id=payload.chunk_id,
        embedding_provider=payload.embedding_provider,
        embedding_model=payload.embedding_model,
        filename=payload.filename,
        chunk_index=payload.chunk_index,
        content=payload.content,
        score=result.score,
        heading=payload.heading,
        page_number=payload.page_number,
        metadata=deepcopy(payload.metadata),
    )


def _validate_retrieval_input(
    *,
    query: object,
    knowledge_base_id: object,
    top_k: object,
    score_threshold: object,
) -> None:
    if not isinstance(query, str) or not query.strip():
        raise RetrieverInputError(
            "Retriever query must be a non-blank string."
        )
    if not isinstance(knowledge_base_id, UUID):
        raise RetrieverInputError(
            "Retriever Knowledge Base identifier must be a UUID."
        )
    if (
        isinstance(top_k, bool)
        or not isinstance(top_k, int)
        or top_k < 1
        or top_k > 100
    ):
        raise RetrieverInputError(
            "Retriever top_k must be an integer between 1 and 100."
        )
    if score_threshold is not None and not _is_finite_number(
        score_threshold
    ):
        raise RetrieverInputError(
            "Retriever score_threshold must be a finite number."
        )


def _is_finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False
