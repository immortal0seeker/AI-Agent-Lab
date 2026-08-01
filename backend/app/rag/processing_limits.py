from dataclasses import dataclass


class DocumentProcessingLimitError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Document exceeds the processing limit.")


@dataclass(frozen=True)
class DocumentProcessingLimits:
    max_pdf_pages: int = 500
    max_extracted_characters: int = 10_000_000
    max_markdown_structures: int = 20_000
    max_chunks: int = 10_000

    def __post_init__(self) -> None:
        for value in (
            self.max_pdf_pages,
            self.max_extracted_characters,
            self.max_markdown_structures,
            self.max_chunks,
        ):
            if value <= 0:
                raise ValueError("document processing limits must be positive")


DEFAULT_DOCUMENT_PROCESSING_LIMITS = DocumentProcessingLimits()
