from datetime import datetime, timezone
from math import inf, nan
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.providers.llm.base import TokenUsage
from app.schemas.message import MessageRead
from app.schemas.rag import (
    RagAnswerMetadata,
    RagChatRequest,
    RagChatResponse,
    RagQueryResponse,
    RagRetrievalMetadata,
    RagRetrievalRequest,
    RagSource,
    RetrievalResult,
)


KNOWLEDGE_BASE_ID = UUID("11111111-1111-1111-1111-111111111111")
CONVERSATION_ID = UUID("22222222-2222-2222-2222-222222222222")
DOCUMENT_ID = UUID("33333333-3333-3333-3333-333333333333")
CHUNK_ID = UUID("44444444-4444-4444-4444-444444444444")
USER_MESSAGE_ID = UUID("55555555-5555-5555-5555-555555555555")
ASSISTANT_MESSAGE_ID = UUID("66666666-6666-6666-6666-666666666666")
LLM_CALL_ID = UUID("77777777-7777-7777-7777-777777777777")


def make_retrieval_result() -> RetrievalResult:
    return RetrievalResult(
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        document_id=DOCUMENT_ID,
        chunk_id=CHUNK_ID,
        filename="guide.md",
        chunk_index=0,
        content="Grounded source",
        score=0.9,
        heading="Overview",
        page_number=None,
        metadata={"source_format": "md"},
    )


def make_message(
    *,
    message_id: UUID,
    role: str,
    content: str,
) -> MessageRead:
    return MessageRead(
        id=message_id,
        conversation_id=CONVERSATION_ID,
        role=role,
        content=content,
        created_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


def test_rag_retrieval_request_defaults_are_strict_and_stable() -> None:
    request = RagRetrievalRequest(
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        query="  What is this project?  ",
    )

    assert request.query == "  What is this project?  "
    assert request.top_k == 5
    assert request.score_threshold is None


def test_rag_chat_request_preserves_generation_parameters() -> None:
    request = RagChatRequest(
        conversation_id=CONVERSATION_ID,
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        provider=" openai_compatible ",
        model=" example-model ",
        query="Question",
        top_k=3,
        score_threshold=0.5,
        temperature=0.2,
        max_tokens=256,
    )

    assert request.provider == "openai_compatible"
    assert request.model == "example-model"
    assert request.temperature == 0.2
    assert request.max_tokens == 256


@pytest.mark.parametrize(
    "payload",
    [
        {"query": ""},
        {"query": " \n\t"},
        {"query": "Question", "top_k": True},
        {"query": "Question", "top_k": 5.0},
        {"query": "Question", "top_k": 0},
        {"query": "Question", "top_k": 101},
        {"query": "Question", "score_threshold": True},
        {"query": "Question", "score_threshold": "0.5"},
        {"query": "Question", "score_threshold": nan},
        {"query": "Question", "score_threshold": inf},
        {"query": "Question", "score_threshold": 10**400},
        {"query": "Question", "unexpected": "value"},
    ],
)
def test_rag_retrieval_request_rejects_invalid_input(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        RagRetrievalRequest(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            **payload,
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"provider": ""},
        {"model": "   "},
        {"provider": "openai_compatible", "temperature": True},
        {"provider": "openai_compatible", "temperature": nan},
        {"provider": "openai_compatible", "temperature": 10**400},
        {"provider": "openai_compatible", "temperature": 2.1},
        {"provider": "openai_compatible", "max_tokens": True},
        {"provider": "openai_compatible", "max_tokens": 0},
    ],
)
def test_rag_chat_request_rejects_invalid_generation_input(
    payload: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "conversation_id": CONVERSATION_ID,
        "knowledge_base_id": KNOWLEDGE_BASE_ID,
        "provider": "openai_compatible",
        "model": "example-model",
        "query": "Question",
    }
    values.update(payload)

    with pytest.raises(ValidationError):
        RagChatRequest.model_validate(values)


def test_rag_query_response_serializes_results_and_metadata() -> None:
    response = RagQueryResponse(
        results=(make_retrieval_result(),),
        metadata=RagRetrievalMetadata(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            top_k=5,
            score_threshold=None,
            result_count=1,
        ),
    )

    payload = response.model_dump(mode="json")
    assert payload["results"][0]["chunk_id"] == str(CHUNK_ID)
    assert payload["metadata"] == {
        "strategy": "naive_vector",
        "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
        "top_k": 5,
        "score_threshold": None,
        "result_count": 1,
    }


def test_rag_chat_response_serializes_answer_sources_and_metadata() -> None:
    source = RagSource(
        **make_retrieval_result().model_dump(),
        source_index=1,
    )
    response = RagChatResponse(
        conversation_id=CONVERSATION_ID,
        user_message=make_message(
            message_id=USER_MESSAGE_ID,
            role="user",
            content="Question",
        ),
        assistant_message=make_message(
            message_id=ASSISTANT_MESSAGE_ID,
            role="assistant",
            content="Answer [1]",
        ),
        answer="Answer [1]",
        sources=(source,),
        metadata=RagAnswerMetadata(
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            top_k=5,
            score_threshold=None,
            result_count=1,
            used_source_count=1,
            context_characters=42,
        ),
        provider="openai_compatible",
        model="resolved-model",
        usage=TokenUsage(input_tokens=10, output_tokens=3, total_tokens=13),
        llm_call_id=LLM_CALL_ID,
    )

    payload = response.model_dump(mode="json")
    assert payload["answer"] == "Answer [1]"
    assert payload["sources"][0]["source_index"] == 1
    assert payload["metadata"]["used_source_count"] == 1
    assert payload["llm_call_id"] == str(LLM_CALL_ID)
