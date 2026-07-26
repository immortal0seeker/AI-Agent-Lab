from uuid import UUID

from app.rag import clean_parsed_document
from app.rag.parsers import ParsedDocument, ParsedPage


DOCUMENT_ID = UUID("11111111-1111-4111-8111-111111111111")


def test_cleaner_normalizes_controls_and_blank_lines() -> None:
    original = ParsedDocument(
        document_id=DOCUMENT_ID,
        text=(
            "\r\nAlpha\x00\u200b\r\n \t\r\n\r\n"
            "Beta\tvalue\ufeff\x7f\x85\r"
        ),
        metadata={"format": "txt", "encoding": "utf-8"},
    )

    cleaned = clean_parsed_document(original)

    assert cleaned.text == "Alpha\n\nBeta\tvalue"
    assert cleaned.metadata == original.metadata
    assert cleaned.metadata is not original.metadata
    assert cleaned.pages is None
    assert original.text.startswith("\r\n")


def test_cleaner_preserves_markdown_and_updates_heading_lines() -> None:
    original = ParsedDocument(
        document_id=DOCUMENT_ID,
        text="\n\n# Title\n\n\n```py\n  value = 1\n```\n\n## Next",
        metadata={
            "format": "markdown",
            "headings": [
                {"level": 1, "text": "Title", "line_number": 3},
                {"level": 2, "text": "Next", "line_number": 10},
            ],
            "code_blocks": [
                {
                    "language": "py",
                    "content": "  value = 1",
                    "start_line": 6,
                    "end_line": 8,
                }
            ],
        },
    )

    cleaned = clean_parsed_document(original)

    assert cleaned.text == (
        "# Title\n\n```py\n  value = 1\n```\n\n## Next"
    )
    assert cleaned.metadata["headings"] == [
        {"level": 1, "text": "Title", "line_number": 1},
        {"level": 2, "text": "Next", "line_number": 7},
    ]
    assert cleaned.metadata["code_blocks"] == original.metadata["code_blocks"]
    assert cleaned.metadata["code_blocks"] is not original.metadata["code_blocks"]
    assert original.metadata["headings"][0]["line_number"] == 3


def test_cleaner_cleans_pdf_pages_independently() -> None:
    original = ParsedDocument(
        document_id=DOCUMENT_ID,
        text=" stale aggregate ",
        metadata={"format": "pdf", "page_count": 2},
        pages=(
            ParsedPage(page_number=1, text="\r\nPage one\r\n"),
            ParsedPage(page_number=2, text="\x00\r\n\r\nPage two"),
        ),
    )

    cleaned = clean_parsed_document(original)

    assert cleaned.pages == (
        ParsedPage(page_number=1, text="Page one"),
        ParsedPage(page_number=2, text="Page two"),
    )
    assert cleaned.text == "Page one\n\nPage two"
    assert original.pages[0].text.startswith("\r\n")


def test_cleaner_preserves_tab_and_meaningful_joiners() -> None:
    original = ParsedDocument(
        document_id=DOCUMENT_ID,
        text="family:\t👩\u200d💻\ufe0f",
        metadata={"format": "txt"},
    )

    cleaned = clean_parsed_document(original)

    assert cleaned.text == "family:\t👩\u200d💻\ufe0f"
