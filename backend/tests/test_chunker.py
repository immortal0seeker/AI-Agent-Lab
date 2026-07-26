from uuid import UUID

import pytest

from app.rag import (
    DocumentContentEmptyError,
    chunk_document,
)
from app.rag.parsers import ParsedDocument, ParsedPage


DOCUMENT_ID = UUID("22222222-2222-4222-8222-222222222222")


def parsed_txt(text: str) -> ParsedDocument:
    return ParsedDocument(
        document_id=DOCUMENT_ID,
        text=text,
        metadata={"format": "txt", "encoding": "utf-8"},
    )


def test_chunker_returns_one_ordered_draft_for_short_text() -> None:
    chunks = chunk_document(
        parsed_txt("Short content"),
        chunk_size=100,
        chunk_overlap=10,
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].content == "Short content"
    assert chunks[0].char_count == len("Short content")
    assert chunks[0].token_count == 4
    assert chunks[0].heading is None
    assert chunks[0].page_number is None
    assert chunks[0].metadata == {
        "source_format": "txt",
        "start_char": 0,
        "end_char": 13,
    }


def test_chunker_prefers_paragraph_boundary_and_overlaps() -> None:
    text = ("A" * 60) + "\n\n" + ("B" * 45) + ("C" * 30)

    chunks = chunk_document(
        parsed_txt(text),
        chunk_size=100,
        chunk_overlap=10,
    )

    assert chunks[0].content.endswith("\n\n")
    assert chunks[1].content.startswith(chunks[0].content[-10:])
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_chunker_uses_hard_boundary_with_monotonic_overlap() -> None:
    chunks = chunk_document(
        parsed_txt("x" * 250),
        chunk_size=100,
        chunk_overlap=20,
    )

    assert [chunk.metadata["start_char"] for chunk in chunks] == [0, 80, 160]
    assert [chunk.metadata["end_char"] for chunk in chunks] == [100, 180, 250]
    assert [len(chunk.content) for chunk in chunks] == [100, 100, 90]
    assert chunks[1].content[:20] == chunks[0].content[-20:]


def test_chunker_supports_zero_overlap() -> None:
    chunks = chunk_document(
        parsed_txt("x" * 220),
        chunk_size=100,
        chunk_overlap=0,
    )

    assert [chunk.metadata["start_char"] for chunk in chunks] == [0, 100, 200]


def test_chunker_preserves_markdown_heading() -> None:
    document = ParsedDocument(
        document_id=DOCUMENT_ID,
        text="# First\nBody\n\n## Second\nMore",
        metadata={
            "format": "markdown",
            "headings": [
                {"level": 1, "text": "First", "line_number": 1},
                {"level": 2, "text": "Second", "line_number": 4},
            ],
        },
    )

    chunks = chunk_document(document, chunk_size=12, chunk_overlap=2)

    assert chunks[0].heading == "First"
    assert any(chunk.heading == "Second" for chunk in chunks)
    assert any(
        chunk.metadata.get("heading_level") == 2 for chunk in chunks
    )


def test_chunker_keeps_pdf_pages_separate() -> None:
    document = ParsedDocument(
        document_id=DOCUMENT_ID,
        text="Page one\n\nPage two",
        metadata={"format": "pdf", "page_count": 2},
        pages=(
            ParsedPage(page_number=1, text="Page one"),
            ParsedPage(page_number=2, text="Page two"),
        ),
    )

    chunks = chunk_document(document, chunk_size=100, chunk_overlap=10)

    assert [chunk.page_number for chunk in chunks] == [1, 2]
    assert [chunk.content for chunk in chunks] == ["Page one", "Page two"]
    assert [chunk.metadata["start_char"] for chunk in chunks] == [0, 0]
    assert [chunk.metadata["end_char"] for chunk in chunks] == [8, 8]


def test_chunker_skips_blank_pdf_page() -> None:
    document = ParsedDocument(
        document_id=DOCUMENT_ID,
        text="\n\nUsable",
        metadata={"format": "pdf", "page_count": 2},
        pages=(
            ParsedPage(page_number=1, text=""),
            ParsedPage(page_number=2, text="Usable"),
        ),
    )

    chunks = chunk_document(document, chunk_size=100, chunk_overlap=10)

    assert len(chunks) == 1
    assert chunks[0].page_number == 2
    assert chunks[0].chunk_index == 0


def test_chunker_estimates_unicode_tokens_from_utf8_bytes() -> None:
    chunks = chunk_document(
        parsed_txt("中文"),
        chunk_size=100,
        chunk_overlap=10,
    )

    assert chunks[0].token_count == 2


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [(0, 0), (-1, 0), (10, -1), (10, 10), (10, 11)],
)
def test_chunker_rejects_invalid_window(
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    with pytest.raises(ValueError):
        chunk_document(
            parsed_txt("content"),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )


def test_chunker_rejects_document_without_usable_text() -> None:
    with pytest.raises(
        DocumentContentEmptyError,
        match="Document contains no usable text",
    ):
        chunk_document(
            parsed_txt(" \n\t"),
            chunk_size=100,
            chunk_overlap=10,
        )
