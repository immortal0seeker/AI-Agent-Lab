import asyncio
import hashlib
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.knowledge import (
    DocumentDuplicateError,
    DocumentStorage,
    DocumentStorageError,
    KnowledgeBaseDocumentLimitReachedError,
)
from app.models import Document, DocumentChunk
from app.rag import DocumentProcessingLimits
from app.schemas import KnowledgeBaseCreate
from app.services import (
    DocumentService,
    KnowledgeBaseNotFoundError,
    KnowledgeBaseService,
)


class TrackingStream:
    def __init__(self, content: bytes) -> None:
        self._content = content
        self._offset = 0
        self.read_calls = 0

    async def read(self, size: int = -1) -> bytes:
        self.read_calls += 1
        if self._offset >= len(self._content):
            return b""
        end = len(self._content) if size < 0 else self._offset + size
        chunk = self._content[self._offset : end]
        self._offset += len(chunk)
        return chunk


@pytest.fixture
def db(tmp_path: Path) -> Iterator[tuple[Session, Engine]]:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(
        f"sqlite:///{tmp_path / 'document-service.db'}"
    )
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    try:
        yield session, engine
    finally:
        session.close()
        engine.dispose()


def _create_knowledge_base(session: Session, name: str) -> UUID:
    knowledge_base = KnowledgeBaseService(session).create_knowledge_base(
        KnowledgeBaseCreate(name=name)
    )
    session.commit()
    return knowledge_base.id


def _document_count(session: Session) -> int:
    return session.scalar(select(func.count(Document.id))) or 0


def _chunk_count(session: Session) -> int:
    return session.scalar(select(func.count(DocumentChunk.id))) or 0


def _stored_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix != ".part"
    ]


def test_service_uploads_document_with_initial_states(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    knowledge_base_id = _create_knowledge_base(session, "Docs")
    content = b"# Synthetic guide"
    storage = DocumentStorage(
        tmp_path / "uploads",
        max_upload_bytes=1024,
    )
    service = DocumentService(
        session,
        storage=storage,
        max_files_per_knowledge_base=50,
    )

    document = asyncio.run(
        service.upload_document(
            knowledge_base_id,
            original_filename="guide.md",
            stream=TrackingStream(content),
        )
    )

    assert document.knowledge_base_id == knowledge_base_id
    assert document.filename == f"{document.id}.md"
    assert document.file_path == f"{knowledge_base_id}/{document.id}.md"
    assert document.original_filename == "guide.md"
    assert document.file_type == "md"
    assert document.file_size == len(content)
    assert document.file_hash == hashlib.sha256(content).hexdigest()
    assert document.parse_status == "parsed"
    assert document.chunk_status == "chunked"
    assert document.embedding_status == "pending"
    assert document.error_message is None
    assert document.metadata_json["format"] == "markdown"
    assert _chunk_count(session) == 1
    assert (storage.root / Path(document.file_path)).read_bytes() == content

    session.commit()

    assert (storage.root / Path(document.file_path)).exists()


def test_service_retains_document_when_content_processing_fails(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    knowledge_base_id = _create_knowledge_base(session, "Failed content")
    storage = DocumentStorage(
        tmp_path / "uploads",
        max_upload_bytes=1024,
    )
    service = DocumentService(
        session,
        storage=storage,
        max_files_per_knowledge_base=50,
    )

    document = asyncio.run(
        service.upload_document(
            knowledge_base_id,
            original_filename="invalid.txt",
            stream=TrackingStream(b"\x80private"),
        )
    )

    assert document.parse_status == "failed"
    assert document.chunk_status == "failed"
    assert document.error_message == "Document parsing failed."
    assert _document_count(session) == 1
    assert _chunk_count(session) == 0
    assert (storage.root / Path(document.file_path)).exists()


def test_service_passes_processing_limits_to_ingestion(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    knowledge_base_id = _create_knowledge_base(session, "Limited processing")
    storage = DocumentStorage(
        tmp_path / "uploads",
        max_upload_bytes=1024,
    )
    limits = DocumentProcessingLimits(
        max_pdf_pages=10,
        max_extracted_characters=5,
        max_markdown_structures=10,
        max_chunks=10,
    )
    service = DocumentService(
        session,
        storage=storage,
        max_files_per_knowledge_base=50,
        processing_limits=limits,
    )

    document = asyncio.run(
        service.upload_document(
            knowledge_base_id,
            original_filename="private.txt",
            stream=TrackingStream(b"private content"),
        )
    )

    assert document.parse_status == "failed"
    assert document.chunk_status == "failed"
    assert document.error_message == "Document exceeds the processing limit."
    assert _document_count(session) == 1
    assert _chunk_count(session) == 0


def test_service_checks_knowledge_base_before_reading_stream(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    storage = DocumentStorage(
        tmp_path / "uploads",
        max_upload_bytes=1024,
    )
    service = DocumentService(
        session,
        storage=storage,
        max_files_per_knowledge_base=50,
    )
    stream = TrackingStream(b"synthetic")

    with pytest.raises(KnowledgeBaseNotFoundError):
        asyncio.run(
            service.upload_document(
                uuid4(),
                original_filename="missing.md",
                stream=stream,
            )
        )

    assert stream.read_calls == 0
    assert not storage.root.exists()


def test_service_rejects_document_limit_before_reading_stream(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    knowledge_base_id = _create_knowledge_base(session, "Limited")
    session.add(
        Document(
            knowledge_base_id=knowledge_base_id,
            filename="existing.md",
            original_filename="existing.md",
            file_type="md",
            file_path=f"{knowledge_base_id}/{uuid4()}.md",
            file_size=1,
            file_hash="a" * 64,
        )
    )
    session.commit()
    storage = DocumentStorage(
        tmp_path / "uploads",
        max_upload_bytes=1024,
    )
    service = DocumentService(
        session,
        storage=storage,
        max_files_per_knowledge_base=1,
    )
    stream = TrackingStream(b"unique")

    with pytest.raises(KnowledgeBaseDocumentLimitReachedError):
        asyncio.run(
            service.upload_document(
                knowledge_base_id,
                original_filename="second.md",
                stream=stream,
            )
        )

    assert stream.read_calls == 0
    assert not storage.root.exists()


def test_service_rejects_same_knowledge_base_duplicate(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    knowledge_base_id = _create_knowledge_base(session, "Duplicates")
    content = b"same content"
    storage = DocumentStorage(
        tmp_path / "uploads",
        max_upload_bytes=1024,
    )
    service = DocumentService(
        session,
        storage=storage,
        max_files_per_knowledge_base=50,
    )
    asyncio.run(
        service.upload_document(
            knowledge_base_id,
            original_filename="first.md",
            stream=TrackingStream(content),
        )
    )
    session.commit()

    with pytest.raises(DocumentDuplicateError):
        asyncio.run(
            service.upload_document(
                knowledge_base_id,
                original_filename="second.txt",
                stream=TrackingStream(content),
            )
        )

    assert _document_count(session) == 1
    assert len(_stored_files(storage.root)) == 1
    assert not any(storage.staging_directory.iterdir())


def test_service_normalizes_unique_race_and_cleans_promoted_file(
    db: tuple[Session, Engine],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, _ = db
    knowledge_base_id = _create_knowledge_base(session, "Race")
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)
    service = DocumentService(
        session,
        storage=storage,
        max_files_per_knowledge_base=50,
    )
    content = b"same race content"
    asyncio.run(
        service.upload_document(
            knowledge_base_id,
            original_filename="first.txt",
            stream=TrackingStream(content),
        )
    )
    session.commit()
    real_scalar = session.scalar
    document_scalar_calls = 0

    def scalar_without_duplicate_precheck(statement, *args, **kwargs):
        nonlocal document_scalar_calls
        if "FROM documents" in str(statement):
            document_scalar_calls += 1
            if document_scalar_calls == 2:
                return None
        return real_scalar(statement, *args, **kwargs)

    monkeypatch.setattr(session, "scalar", scalar_without_duplicate_precheck)

    with pytest.raises(DocumentDuplicateError):
        asyncio.run(
            service.upload_document(
                knowledge_base_id,
                original_filename="second.txt",
                stream=TrackingStream(content),
            )
        )
    session.rollback()

    assert _document_count(session) == 1
    assert len(_stored_files(storage.root)) == 1


def test_service_allows_same_hash_in_different_knowledge_bases(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    first_knowledge_base_id = _create_knowledge_base(session, "First")
    second_knowledge_base_id = _create_knowledge_base(session, "Second")
    content = b"shared content"
    storage = DocumentStorage(
        tmp_path / "uploads",
        max_upload_bytes=1024,
    )
    service = DocumentService(
        session,
        storage=storage,
        max_files_per_knowledge_base=50,
    )

    first = asyncio.run(
        service.upload_document(
            first_knowledge_base_id,
            original_filename="shared.md",
            stream=TrackingStream(content),
        )
    )
    second = asyncio.run(
        service.upload_document(
            second_knowledge_base_id,
            original_filename="shared.md",
            stream=TrackingStream(content),
        )
    )

    assert first.file_hash == second.file_hash
    assert first.file_path != second.file_path
    assert _document_count(session) == 2
    assert len(_stored_files(storage.root)) == 2


def test_service_rolls_back_promoted_file(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    knowledge_base_id = _create_knowledge_base(session, "Rollback")
    storage = DocumentStorage(
        tmp_path / "uploads",
        max_upload_bytes=1024,
    )
    service = DocumentService(
        session,
        storage=storage,
        max_files_per_knowledge_base=50,
    )
    document = asyncio.run(
        service.upload_document(
            knowledge_base_id,
            original_filename="rollback.txt",
            stream=TrackingStream(b"rollback"),
        )
    )
    final_path = storage.root / Path(document.file_path)
    assert final_path.exists()

    session.rollback()

    assert not final_path.exists()
    assert _document_count(session) == 0


def test_service_commit_retains_promoted_file(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    knowledge_base_id = _create_knowledge_base(session, "Commit")
    storage = DocumentStorage(
        tmp_path / "uploads",
        max_upload_bytes=1024,
    )
    service = DocumentService(
        session,
        storage=storage,
        max_files_per_knowledge_base=50,
    )
    document = asyncio.run(
        service.upload_document(
            knowledge_base_id,
            original_filename="commit.txt",
            stream=TrackingStream(b"commit"),
        )
    )
    final_path = storage.root / Path(document.file_path)

    session.commit()
    session.rollback()

    assert final_path.exists()
    assert _document_count(session) == 1


def test_service_storage_failure_leaves_no_document(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    knowledge_base_id = _create_knowledge_base(session, "Failure")
    storage_root = tmp_path / "not-a-directory"
    storage_root.write_text("synthetic", encoding="utf-8")
    service = DocumentService(
        session,
        storage=DocumentStorage(storage_root, max_upload_bytes=1024),
        max_files_per_knowledge_base=50,
    )

    with pytest.raises(DocumentStorageError):
        asyncio.run(
            service.upload_document(
                knowledge_base_id,
                original_filename="failure.md",
                stream=TrackingStream(b"failure"),
            )
        )

    assert _document_count(session) == 0
