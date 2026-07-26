import logging
from uuid import UUID, uuid4

from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.core.logging import safe_stack_locations
from app.knowledge import (
    AsyncReadable,
    DocumentDuplicateError,
    DocumentStorage,
    KnowledgeBaseDocumentLimitReachedError,
    StagedDocument,
)
from app.models import Document
from app.services.knowledge_base_service import KnowledgeBaseService

logger = logging.getLogger(__name__)

_PENDING_DOCUMENT_FILES = "pending_document_files"
_DOCUMENT_FILE_LISTENERS = "document_file_listeners_registered"


def _register_file_transaction_listeners(session: Session) -> None:
    if session.info.get(_DOCUMENT_FILE_LISTENERS):
        return

    def clear_committed_files(committed_session: Session) -> None:
        committed_session.info.pop(_PENDING_DOCUMENT_FILES, None)

    def discard_rolled_back_files(rolled_back_session: Session) -> None:
        pending_files = rolled_back_session.info.pop(
            _PENDING_DOCUMENT_FILES,
            [],
        )
        for storage, relative_path in pending_files:
            try:
                storage.discard_stored(relative_path)
            except Exception as exc:
                logger.error(
                    "document_rollback_cleanup_failed",
                    extra={
                        "stack_locations": safe_stack_locations(exc),
                    },
                )

    event.listen(session, "after_commit", clear_committed_files)
    event.listen(session, "after_rollback", discard_rolled_back_files)
    session.info[_DOCUMENT_FILE_LISTENERS] = True


class DocumentService:
    def __init__(
        self,
        session: Session,
        *,
        storage: DocumentStorage,
        max_files_per_knowledge_base: int,
    ) -> None:
        self._session = session
        self._storage = storage
        self._max_files_per_knowledge_base = max_files_per_knowledge_base
        _register_file_transaction_listeners(session)

    async def upload_document(
        self,
        knowledge_base_id: UUID,
        *,
        original_filename: str | None,
        stream: AsyncReadable,
    ) -> Document:
        KnowledgeBaseService(self._session).get_knowledge_base(
            knowledge_base_id
        )
        document_count = self._session.scalar(
            select(func.count(Document.id)).where(
                Document.knowledge_base_id == knowledge_base_id
            )
        )
        if (document_count or 0) >= self._max_files_per_knowledge_base:
            raise KnowledgeBaseDocumentLimitReachedError()

        staged: StagedDocument | None = None
        try:
            staged = await self._storage.stage(
                stream,
                original_filename=original_filename,
            )
            duplicate_id = self._session.scalar(
                select(Document.id).where(
                    Document.knowledge_base_id == knowledge_base_id,
                    Document.file_hash == staged.file_hash,
                )
            )
            if duplicate_id is not None:
                self._storage.discard_staged(staged)
                staged = None
                raise DocumentDuplicateError()

            staged_document = staged
            document_id = uuid4()
            stored = self._storage.promote(
                staged_document,
                knowledge_base_id=knowledge_base_id,
                document_id=document_id,
            )
            staged = None
            pending_files = self._session.info.setdefault(
                _PENDING_DOCUMENT_FILES,
                [],
            )
            pending_files.append((self._storage, stored.relative_path))
            document = Document(
                id=document_id,
                knowledge_base_id=knowledge_base_id,
                filename=stored.filename,
                original_filename=staged_document.original_filename,
                file_type=staged_document.file_type,
                file_path=stored.relative_path,
                file_size=staged_document.file_size,
                file_hash=staged_document.file_hash,
                metadata_json={},
            )
            self._session.add(document)
            self._session.flush()
            return document
        finally:
            if staged is not None:
                self._storage.discard_staged(staged)
