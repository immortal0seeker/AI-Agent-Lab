from pathlib import Path
from uuid import UUID

import pytest

from app.rag.parsers import DocumentParseError, parse_txt


DOCUMENT_ID = UUID("22222222-2222-4222-8222-222222222222")


@pytest.mark.parametrize(
    ("content", "expected_text", "expected_encoding"),
    [
        ("Plain 中文".encode(), "Plain 中文", "utf-8"),
        (b"\xef\xbb\xbfWith BOM", "With BOM", "utf-8-sig"),
        (
            b"\xff\xfe" + "Little 中文".encode("utf-16-le"),
            "Little 中文",
            "utf-16-le",
        ),
        (
            b"\xfe\xff" + "Big 中文".encode("utf-16-be"),
            "Big 中文",
            "utf-16-be",
        ),
    ],
)
def test_txt_parser_decodes_supported_encodings(
    tmp_path: Path,
    content: bytes,
    expected_text: str,
    expected_encoding: str,
) -> None:
    path = tmp_path / "notes.txt"
    path.write_bytes(content)

    parsed = parse_txt(path, document_id=DOCUMENT_ID)

    assert parsed.document_id == DOCUMENT_ID
    assert parsed.text == expected_text
    assert parsed.pages is None
    assert parsed.metadata == {
        "format": "txt",
        "encoding": expected_encoding,
    }


def test_txt_parser_preserves_whitespace_only_text(tmp_path: Path) -> None:
    path = tmp_path / "whitespace.txt"
    path.write_bytes(b" \r\n\t")

    parsed = parse_txt(path, document_id=DOCUMENT_ID)

    assert parsed.text == " \r\n\t"


def test_txt_parser_wraps_invalid_encoding_safely(
    tmp_path: Path,
) -> None:
    path = tmp_path / "private-invalid.txt"
    path.write_bytes(b"\x80private")

    with pytest.raises(DocumentParseError) as caught:
        parse_txt(path, document_id=DOCUMENT_ID)

    message = str(caught.value)
    assert message == "Document parsing failed."
    assert str(path) not in message
    assert "position" not in message.lower()


@pytest.mark.parametrize(
    "content",
    [
        b"\xff\xfe\x00\x00" + "Unsupported".encode("utf-32-le"),
        b"\x00\x00\xfe\xff" + "Unsupported".encode("utf-32-be"),
    ],
)
def test_txt_parser_rejects_unsupported_utf32(
    tmp_path: Path,
    content: bytes,
) -> None:
    path = tmp_path / "unsupported-utf32.txt"
    path.write_bytes(content)

    with pytest.raises(DocumentParseError):
        parse_txt(path, document_id=DOCUMENT_ID)
