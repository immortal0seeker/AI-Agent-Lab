from dataclasses import FrozenInstanceError
from pathlib import Path
from uuid import UUID

import pytest

from app.rag import DocumentProcessingLimitError, DocumentProcessingLimits
from app.rag.parsers import DocumentParseError, parse_markdown


DOCUMENT_ID = UUID("11111111-1111-4111-8111-111111111111")
LIMITS = DocumentProcessingLimits(
    max_pdf_pages=1,
    max_extracted_characters=20,
    max_markdown_structures=1,
    max_chunks=10,
)


def test_markdown_parser_preserves_text_and_extracts_structure(
    tmp_path: Path,
) -> None:
    source = (
        "# Guide\n"
        "\n"
        "Overview\n"
        "--------\n"
        "```python\n"
        "# not a heading\n"
        'print("hello")\n'
        "```\n"
        "\n"
        "~~~ text\n"
        "sample\n"
        "~~~\n"
    )
    path = tmp_path / "guide.md"
    path.write_text(source, encoding="utf-8", newline="")

    parsed = parse_markdown(path, document_id=DOCUMENT_ID)

    assert parsed.document_id == DOCUMENT_ID
    assert parsed.text == source
    assert parsed.pages is None
    assert parsed.metadata == {
        "format": "markdown",
        "encoding": "utf-8",
        "headings": [
            {"level": 1, "text": "Guide", "line_number": 1},
            {"level": 2, "text": "Overview", "line_number": 3},
        ],
        "code_blocks": [
            {
                "language": "python",
                "start_line": 5,
                "end_line": 8,
            },
            {
                "language": "text",
                "start_line": 10,
                "end_line": 12,
            },
        ],
    }
    with pytest.raises(FrozenInstanceError):
        parsed.text = "changed"  # type: ignore[misc]


def test_markdown_parser_accepts_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "bom.md"
    path.write_bytes(b"\xef\xbb\xbf# Title\nBody")

    parsed = parse_markdown(path, document_id=DOCUMENT_ID)

    assert parsed.text == "# Title\nBody"
    assert parsed.metadata["encoding"] == "utf-8-sig"
    assert parsed.metadata["headings"] == [
        {"level": 1, "text": "Title", "line_number": 1}
    ]


def test_markdown_parser_keeps_unclosed_fence_to_end_of_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "unclosed.md"
    path.write_text(
        "## Before\n```py\n# code heading\nvalue = 1",
        encoding="utf-8",
    )

    parsed = parse_markdown(path, document_id=DOCUMENT_ID)

    assert parsed.metadata["headings"] == [
        {"level": 2, "text": "Before", "line_number": 1}
    ]
    assert parsed.metadata["code_blocks"] == [
        {
            "language": "py",
            "start_line": 2,
            "end_line": 4,
        }
    ]


def test_markdown_parser_rejects_structure_limit(tmp_path: Path) -> None:
    path = tmp_path / "many.md"
    path.write_text("# One\n# Two", encoding="utf-8")

    with pytest.raises(DocumentProcessingLimitError):
        parse_markdown(path, document_id=DOCUMENT_ID, limits=LIMITS)


def test_markdown_parser_rejects_extracted_character_limit(
    tmp_path: Path,
) -> None:
    path = tmp_path / "large.md"
    path.write_text("x" * 21, encoding="utf-8")

    with pytest.raises(DocumentProcessingLimitError):
        parse_markdown(path, document_id=DOCUMENT_ID, limits=LIMITS)


def test_markdown_parser_wraps_invalid_utf8_safely(
    tmp_path: Path,
) -> None:
    path = tmp_path / "private-invalid.md"
    path.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(DocumentParseError) as caught:
        parse_markdown(path, document_id=DOCUMENT_ID)

    message = str(caught.value)
    assert message == "Document parsing failed."
    assert str(path) not in message
    assert "codec" not in message.lower()
