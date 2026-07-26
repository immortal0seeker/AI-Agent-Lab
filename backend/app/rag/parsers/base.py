from dataclasses import dataclass
from uuid import UUID


class DocumentParseError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Document parsing failed.")


class DocumentParseLimitationError(DocumentParseError):
    def __init__(self) -> None:
        RuntimeError.__init__(
            self,
            "Scanned or image-only PDF requires OCR, which is not supported "
            "in Plan 3.",
        )


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    document_id: UUID
    text: str
    metadata: dict[str, object]
    pages: tuple[ParsedPage, ...] | None = None
