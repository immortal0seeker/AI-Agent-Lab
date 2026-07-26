from collections.abc import Callable

from sqlalchemy.orm import Session

from app.knowledge import DocumentStorage
from app.models import Document, DocumentChunk
from app.rag import (
    DocumentContentEmptyError,
    clean_parsed_document,
    chunk_document,
)
from app.rag.parsers import (
    DocumentParseError,
    ParsedDocument,
    parse_markdown,
    parse_pdf,
    parse_txt,
)

Parser = Callable[..., ParsedDocument]

_PARSERS: dict[str, Parser] = {
    "md": parse_markdown,
    "txt": parse_txt,
    "pdf": parse_pdf,
}


class DocumentIngestionService:
    def __init__(
        self,
        session: Session,
        *,
        storage: DocumentStorage,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        self._session = session
        self._storage = storage
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def process_document(self, document: Document) -> Document:
        document.parse_status = "parsing"
        document.chunk_status = "pending"
        document.error_message = None
        path = self._storage.resolve_stored(
            document.file_path,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            file_type=document.file_type,  # type: ignore[arg-type]
        )
        try:
            parsed = _PARSERS[document.file_type](
                path,
                document_id=document.id,
            )
        except DocumentParseError as error:
            return self._mark_parse_failed(document, error)
        document.parse_status = "parsed"
        cleaned = clean_parsed_document(parsed)
        document.metadata_json = dict(cleaned.metadata)
        document.chunk_status = "chunking"
        try:
            drafts = chunk_document(
                cleaned,
                chunk_size=self._chunk_size,
                chunk_overlap=self._chunk_overlap,
            )
        except DocumentContentEmptyError as error:
            return self._mark_chunk_failed(document, error)
        for draft in drafts:
            self._session.add(
                DocumentChunk(
                    document_id=document.id,
                    knowledge_base_id=document.knowledge_base_id,
                    chunk_index=draft.chunk_index,
                    content=draft.content,
                    token_count=draft.token_count,
                    char_count=draft.char_count,
                    heading=draft.heading,
                    page_number=draft.page_number,
                    metadata_json=dict(draft.metadata),
                )
            )
        document.chunk_status = "chunked"
        self._session.flush()
        return document

    def _mark_parse_failed(
        self,
        document: Document,
        error: DocumentParseError,
    ) -> Document:
        document.parse_status = "failed"
        document.chunk_status = "failed"
        document.error_message = str(error)
        self._session.flush()
        return document

    def _mark_chunk_failed(
        self,
        document: Document,
        error: DocumentContentEmptyError,
    ) -> Document:
        document.parse_status = "parsed"
        document.chunk_status = "failed"
        document.error_message = str(error)
        self._session.flush()
        return document
