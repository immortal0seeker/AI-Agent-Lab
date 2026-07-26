from pathlib import Path
from uuid import UUID

import pytest

from app.rag.parsers import (
    DocumentParseError,
    DocumentParseLimitationError,
    parse_pdf,
)


DOCUMENT_ID = UUID("33333333-3333-4333-8333-333333333333")


def _pdf_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf(page_texts: list[str | None]) -> bytes:
    page_object_numbers = [
        4 + page_index * 2 for page_index in range(len(page_texts))
    ]
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            "<< /Type /Pages /Count "
            f"{len(page_texts)} /Kids "
            f"[{' '.join(f'{number} 0 R' for number in page_object_numbers)}]"
            " >>"
        ).encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for page_index, page_text in enumerate(page_texts):
        page_number = page_object_numbers[page_index]
        content_number = page_number + 1
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R "
                "/MediaBox [0 0 612 792] "
                "/Resources << /Font << /F1 3 0 R >> >> "
                f"/Contents {content_number} 0 R >>"
            ).encode()
        )
        if page_text is None:
            stream = b"q Q"
        else:
            stream = (
                "BT /F1 12 Tf 72 720 Td "
                f"({_pdf_string(page_text)}) Tj ET"
            ).encode()
        objects.append(
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )

    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{object_number} 0 obj\n".encode())
        document.extend(body)
        document.extend(b"\nendobj\n")

    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode())
    document.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        ).encode()
    )
    return bytes(document)


def test_pdf_parser_extracts_ordered_pages(tmp_path: Path) -> None:
    path = tmp_path / "manual.pdf"
    path.write_bytes(_build_pdf(["First page", "Second page"]))

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
    path.write_bytes(_build_pdf(["Text page", None]))

    parsed = parse_pdf(path, document_id=DOCUMENT_ID)

    assert parsed.pages is not None
    assert parsed.pages[0].text.strip() == "Text page"
    assert parsed.pages[1].text == ""


def test_pdf_parser_reports_scanned_pdf_limitation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "private-scanned.pdf"
    path.write_bytes(_build_pdf([None]))

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
