from pathlib import Path
from uuid import UUID

from pypdf import PdfReader

from .base import (
    DocumentParseError,
    DocumentParseLimitationError,
    ParsedDocument,
    ParsedPage,
)


def parse_pdf(path: Path, *, document_id: UUID) -> ParsedDocument:
    try:
        with Path(path).open("rb") as source:
            reader = PdfReader(source)
            if reader.is_encrypted and not reader.decrypt(""):
                raise DocumentParseError()
            pages = tuple(
                ParsedPage(
                    page_number=page_number,
                    text=page.extract_text() or "",
                )
                for page_number, page in enumerate(reader.pages, start=1)
            )
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError() from exc

    if not any(page.text.strip() for page in pages):
        raise DocumentParseLimitationError()

    return ParsedDocument(
        document_id=document_id,
        text="\n\n".join(page.text for page in pages),
        metadata={
            "format": "pdf",
            "page_count": len(pages),
        },
        pages=pages,
    )
