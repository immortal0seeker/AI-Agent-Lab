from pathlib import Path
from uuid import UUID

from pypdf import PdfReader

from app.rag.processing_limits import (
    DEFAULT_DOCUMENT_PROCESSING_LIMITS,
    DocumentProcessingLimitError,
    DocumentProcessingLimits,
)

from .base import (
    DocumentParseError,
    DocumentParseLimitationError,
    ParsedDocument,
    ParsedPage,
)


def parse_pdf(
    path: Path,
    *,
    document_id: UUID,
    limits: DocumentProcessingLimits = DEFAULT_DOCUMENT_PROCESSING_LIMITS,
) -> ParsedDocument:
    try:
        with Path(path).open("rb") as source:
            reader = PdfReader(source)
            if reader.is_encrypted and not reader.decrypt(""):
                raise DocumentParseError()
            if len(reader.pages) > limits.max_pdf_pages:
                raise DocumentProcessingLimitError()
            pages_list: list[ParsedPage] = []
            extracted_characters = 0
            for page_number, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                extracted_characters += len(page_text)
                if extracted_characters > limits.max_extracted_characters:
                    raise DocumentProcessingLimitError()
                pages_list.append(
                    ParsedPage(
                        page_number=page_number,
                        text=page_text,
                    )
                )
            pages = tuple(pages_list)
    except DocumentProcessingLimitError:
        raise
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
