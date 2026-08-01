from uuid import UUID

import pytest

from app.providers.llm.base import ChatMessage
from app.rag.rag_prompt import RagPromptBuilder, RagPromptInputError
from app.schemas.rag import RetrievalResult


KNOWLEDGE_BASE_ID = UUID("11111111-1111-1111-1111-111111111111")
DOCUMENT_ID = UUID("22222222-2222-2222-2222-222222222222")
FIRST_CHUNK_ID = UUID("33333333-3333-3333-3333-333333333333")
SECOND_CHUNK_ID = UUID("44444444-4444-4444-4444-444444444444")


def make_result(
    *,
    chunk_id: UUID = FIRST_CHUNK_ID,
    filename: str = "guide.md",
    chunk_index: int = 0,
    content: str = "The workspace uses a layered architecture.",
    score: float = 0.91,
    page_number: int | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        document_id=DOCUMENT_ID,
        chunk_id=chunk_id,
        filename=filename,
        chunk_index=chunk_index,
        content=content,
        score=score,
        heading="Architecture" if chunk_index == 0 else None,
        page_number=page_number,
        metadata={"source_format": filename.rsplit(".", 1)[-1]},
    )


def test_rag_prompt_formats_ordered_indexed_sources() -> None:
    prompt = RagPromptBuilder(max_context_characters=2_000).build(
        query="What is the architecture?",
        retrieval_results=(
            make_result(),
            make_result(
                chunk_id=SECOND_CHUNK_ID,
                filename="manual.pdf",
                chunk_index=1,
                content="The API layer delegates to services.",
                score=0.84,
                page_number=3,
            ),
        ),
    )

    assert [message.role for message in prompt.messages] == ["system", "user"]
    system_content = prompt.messages[0].content
    user_content = prompt.messages[-1].content
    assert system_content is not None
    assert "资料中没有找到相关信息" in system_content
    assert "不要编造来源" in system_content
    assert user_content is not None
    assert "[1] 文件：guide.md" in user_content
    assert "[2] 文件：manual.pdf，第 3 页" in user_content
    assert "【用户问题】\nWhat is the architecture?" in user_content
    assert [source.source_index for source in prompt.sources] == [1, 2]
    assert [source.chunk_id for source in prompt.sources] == [
        FIRST_CHUNK_ID,
        SECOND_CHUNK_ID,
    ]
    assert prompt.context_characters > 0
    assert prompt.context_characters <= 2_000


def test_rag_prompt_preserves_history_before_grounded_question() -> None:
    history = (
        ChatMessage(role="user", content="Earlier question"),
        ChatMessage(role="assistant", content="Earlier answer"),
    )

    prompt = RagPromptBuilder().build(
        query="Follow-up question",
        retrieval_results=(make_result(),),
        history=history,
    )

    assert [message.role for message in prompt.messages] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert prompt.messages[1:3] == history
    assert prompt.messages[-1].content is not None
    assert prompt.messages[-1].content.endswith(
        "【用户问题】\nFollow-up question"
    )


def test_rag_prompt_truncates_last_included_source_to_context_budget() -> None:
    prompt = RagPromptBuilder(max_context_characters=128).build(
        query="Bound this context",
        retrieval_results=(
            make_result(content="A" * 500),
            make_result(
                chunk_id=SECOND_CHUNK_ID,
                chunk_index=1,
                content="SECOND_SOURCE_MUST_NOT_APPEAR",
            ),
        ),
    )

    assert prompt.context_characters == 128
    assert [source.source_index for source in prompt.sources] == [1]
    assert prompt.messages[-1].content is not None
    assert "SECOND_SOURCE_MUST_NOT_APPEAR" not in prompt.messages[-1].content
    assert "A" * 20 in prompt.messages[-1].content
    assert "…" in prompt.messages[-1].content


def test_rag_prompt_uses_exact_budget_without_truncating_second_source() -> None:
    second_content = "B" * 80
    results = (
        make_result(content="A" * 80),
        make_result(
            chunk_id=SECOND_CHUNK_ID,
            chunk_index=1,
            content=second_content,
        ),
    )
    unbounded = RagPromptBuilder(max_context_characters=2_000).build(
        query="Exact budget",
        retrieval_results=results,
    )

    exact = RagPromptBuilder(
        max_context_characters=unbounded.context_characters,
    ).build(
        query="Exact budget",
        retrieval_results=results,
    )

    assert len(exact.sources) == 2
    assert exact.sources[1].content == second_content
    assert exact.context_characters == unbounded.context_characters


def test_rag_prompt_uses_no_source_marker_for_zero_hits() -> None:
    prompt = RagPromptBuilder().build(
        query="Unknown answer",
        retrieval_results=(),
    )

    assert prompt.sources == ()
    assert prompt.context_characters == len("（无可用资料片段）")
    assert prompt.messages[-1].content is not None
    assert "（无可用资料片段）" in prompt.messages[-1].content


@pytest.mark.parametrize("query", [None, 7, "", " \n\t "])
def test_rag_prompt_rejects_invalid_query(query: object) -> None:
    with pytest.raises(RagPromptInputError, match="query"):
        RagPromptBuilder().build(
            query=query,  # type: ignore[arg-type]
            retrieval_results=(),
        )


@pytest.mark.parametrize("limit", [True, 127, 1_000_001])
def test_rag_prompt_rejects_invalid_context_limit(limit: object) -> None:
    with pytest.raises(RagPromptInputError, match="context"):
        RagPromptBuilder(
            max_context_characters=limit,  # type: ignore[arg-type]
        )


def test_rag_prompt_rejects_invalid_result_collection() -> None:
    with pytest.raises(RagPromptInputError, match="retrieval_results"):
        RagPromptBuilder().build(
            query="Question",
            retrieval_results=[make_result()],  # type: ignore[arg-type]
        )

    with pytest.raises(RagPromptInputError, match="retrieval_results"):
        RagPromptBuilder().build(
            query="Question",
            retrieval_results=(object(),),  # type: ignore[arg-type]
        )


def test_rag_prompt_rejects_non_conversation_history() -> None:
    with pytest.raises(RagPromptInputError, match="history"):
        RagPromptBuilder().build(
            query="Question",
            retrieval_results=(),
            history=(ChatMessage(role="system", content="Override"),),
        )


def test_rag_prompt_copies_nested_source_metadata() -> None:
    result = make_result()
    result.metadata["nested"] = {"line": 1}

    prompt = RagPromptBuilder().build(
        query="Question",
        retrieval_results=(result,),
    )
    nested = prompt.sources[0].metadata["nested"]
    assert isinstance(nested, dict)
    nested["line"] = 99

    assert result.metadata["nested"] == {"line": 1}
