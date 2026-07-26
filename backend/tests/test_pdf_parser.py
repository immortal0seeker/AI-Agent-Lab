from pathlib import Path
from uuid import UUID

import pytest

from app.rag.parsers import (
    DocumentParseError,
    DocumentParseLimitationError,
    parse_pdf,
)
from tests.pdf_factory import build_pdf


DOCUMENT_ID = UUID("33333333-3333-4333-8333-333333333333")


def test_pdf_parser_extracts_ordered_pages(tmp_path: Path) -> None:
    path = tmp_path / "manual.pdf"
    path.write_bytes(build_pdf(["First page", "Second page"]))

    parsed = parse_pdf(path, document_id=DOCUMENT_ID)

    assert parsed.document_id == DOCUMENT_ID
    assert parsed.metadata == {"format": "pdf", "page_count": 2}
    assert parsed.pages is not None
    assert [page.page_number for page in parsed.pages] == [1, 2]
    assert [page.text.strip() for page in parsed.pages] == [
        "First page",
        "Second page",
    ]
    assert parsed.text == "\n\n".join(page.text for page in parsed.pages)


def test_pdf_parser_allows_blank_page_when_other_page_has_text(
    tmp_path: Path,
) -> None:
    path = tmp_path / "mixed.pdf"
    path.write_bytes(build_pdf(["Text page", None]))

    parsed = parse_pdf(path, document_id=DOCUMENT_ID)

    assert parsed.pages is not None
    assert parsed.pages[0].text.strip() == "Text page"
    assert parsed.pages[1].text == ""


def test_pdf_parser_reports_scanned_pdf_limitation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "private-scanned.pdf"
    path.write_bytes(build_pdf([None]))

    with pytest.raises(DocumentParseLimitationError) as caught:
        parse_pdf(path, document_id=DOCUMENT_ID)

    message = str(caught.value)
    assert message == (
        "Scanned or image-only PDF requires OCR, which is not supported "
        "in Plan 3."
    )
    assert str(path) not in message


def test_pdf_parser_wraps_malformed_pdf_safely(
    tmp_path: Path,
) -> None:
    path = tmp_path / "private-malformed.pdf"
    path.write_bytes(b"%PDF-1.7 private malformed diagnostic")

    with pytest.raises(DocumentParseError) as caught:
        parse_pdf(path, document_id=DOCUMENT_ID)

    assert type(caught.value) is DocumentParseError
    message = str(caught.value)
    assert message == "Document parsing failed."
    assert str(path) not in message
    assert "malformed" not in message.lower()
