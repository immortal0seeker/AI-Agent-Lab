import asyncio
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import create_db_engine
from app.knowledge import DocumentStorage, DocumentStorageError
from app.models import Document, DocumentChunk, KnowledgeBase
from app.services import DocumentIngestionService
from tests.pdf_factory import build_pdf


class SyntheticStream:
    def __init__(self, content: bytes) -> None:
        self._content = content
        self._offset = 0

    async def read(self, size: int = -1) -> bytes:
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
        f"sqlite:///{tmp_path / 'document-ingestion.db'}"
    )
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    try:
        yield session, engine
    finally:
        session.close()
        engine.dispose()


def create_stored_document(
    session: Session,
    storage: DocumentStorage,
    *,
    filename: str,
    content: bytes,
) -> Document:
    knowledge_base = KnowledgeBase(name=f"KB {uuid4()}")
    session.add(knowledge_base)
    session.flush()
    staged = asyncio.run(
        storage.stage(
            SyntheticStream(content),
            original_filename=filename,
        )
    )
    document_id = uuid4()
    stored = storage.promote(
        staged,
        knowledge_base_id=knowledge_base.id,
        document_id=document_id,
    )
    document = Document(
        id=document_id,
        knowledge_base_id=knowledge_base.id,
        filename=stored.filename,
        original_filename=staged.original_filename,
        file_type=staged.file_type,
        file_path=stored.relative_path,
        file_size=staged.file_size,
        file_hash=staged.file_hash,
        metadata_json={},
    )
    session.add(document)
    session.flush()
    return document


def stored_chunks(
    session: Session,
    document: Document,
) -> list[DocumentChunk]:
    return list(
        session.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.chunk_index)
        )
    )


def ingestion_service(
    session: Session,
    storage: DocumentStorage,
) -> DocumentIngestionService:
    return DocumentIngestionService(
        session,
        storage=storage,
        chunk_size=100,
        chunk_overlap=10,
    )


def test_ingestion_processes_markdown_and_persists_heading(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=4096)
    document = create_stored_document(
        session,
        storage,
        filename="guide.md",
        content=b"\r\n# Title\r\n\r\n\r\nSynthetic body",
    )

    processed = ingestion_service(session, storage).process_document(document)

    assert processed.parse_status == "parsed"
    assert processed.chunk_status == "chunked"
    assert processed.embedding_status == "pending"
    assert processed.error_message is None
    assert processed.metadata_json["format"] == "markdown"
    chunks = stored_chunks(session, document)
    assert chunks
    assert chunks[0].knowledge_base_id == document.knowledge_base_id
    assert chunks[0].heading == "Title"
    assert chunks[0].content == "# Title\n\nSynthetic body"


def test_ingestion_dispatches_txt_parser(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=4096)
    document = create_stored_document(
        session,
        storage,
        filename="notes.txt",
        content=b"Plain synthetic text",
    )

    processed = ingestion_service(session, storage).process_document(document)

    assert processed.metadata_json == {
        "format": "txt",
        "encoding": "utf-8",
    }
    chunks = stored_chunks(session, document)
    assert [chunk.content for chunk in chunks] == ["Plain synthetic text"]
    assert chunks[0].page_number is None


def test_ingestion_dispatches_pdf_and_persists_page_numbers(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=4096)
    document = create_stored_document(
        session,
        storage,
        filename="manual.pdf",
        content=build_pdf(["First page", "Second page"]),
    )

    processed = ingestion_service(session, storage).process_document(document)

    assert processed.metadata_json == {"format": "pdf", "page_count": 2}
    chunks = stored_chunks(session, document)
    assert [chunk.page_number for chunk in chunks] == [1, 2]
    assert [chunk.content.strip() for chunk in chunks] == [
        "First page",
        "Second page",
    ]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]


def test_ingestion_persists_safe_parser_failure(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=4096)
    content = b"\x80private invalid text"
    document = create_stored_document(
        session,
        storage,
        filename="invalid.txt",
        content=content,
    )

    processed = ingestion_service(session, storage).process_document(document)

    assert processed.parse_status == "failed"
    assert processed.chunk_status == "failed"
    assert processed.embedding_status == "pending"
    assert processed.error_message == "Document parsing failed."
    assert processed.metadata_json == {}
    assert stored_chunks(session, document) == []
    assert str(storage.root) not in processed.error_message
    assert content.decode("utf-8", errors="ignore") not in processed.error_message


def test_ingestion_persists_scanned_pdf_limitation(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=4096)
    document = create_stored_document(
        session,
        storage,
        filename="scanned.pdf",
        content=build_pdf([None]),
    )

    processed = ingestion_service(session, storage).process_document(document)

    assert processed.parse_status == "failed"
    assert processed.chunk_status == "failed"
    assert processed.error_message == (
        "Scanned or image-only PDF requires OCR, which is not supported "
        "in Plan 3."
    )
    assert stored_chunks(session, document) == []


def test_ingestion_persists_cleaned_empty_failure(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=4096)
    document = create_stored_document(
        session,
        storage,
        filename="blank.txt",
        content=b" \r\n\t\r\n",
    )

    processed = ingestion_service(session, storage).process_document(document)

    assert processed.parse_status == "parsed"
    assert processed.chunk_status == "failed"
    assert processed.embedding_status == "pending"
    assert processed.error_message == "Document contains no usable text."
    assert processed.metadata_json == {
        "format": "txt",
        "encoding": "utf-8",
    }
    assert stored_chunks(session, document) == []


def test_ingestion_does_not_convert_storage_error_to_content_failure(
    db: tuple[Session, Engine],
    tmp_path: Path,
) -> None:
    session, _ = db
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=4096)
    document = create_stored_document(
        session,
        storage,
        filename="notes.txt",
        content=b"Synthetic text",
    )
    document.file_path = (
        f"{document.knowledge_base_id}/{uuid4()}.txt"
    )

    with pytest.raises(DocumentStorageError):
        ingestion_service(session, storage).process_document(document)

    assert document.parse_status == "parsing"
    assert document.chunk_status == "pending"
    assert document.error_message is None
    assert stored_chunks(session, document) == []
