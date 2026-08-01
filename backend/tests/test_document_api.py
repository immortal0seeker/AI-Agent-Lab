import hashlib
from collections.abc import AsyncIterator, Iterator
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import (
    get_db_session,
    get_embedding_provider,
    get_vector_store,
)
from app.api.errors import error_spec_for_exception
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import create_db_engine
from app.db.session_callbacks import (
    discard_async_rollback_callbacks,
    run_async_rollback_callbacks,
    run_async_session_finalizers,
)
from app.knowledge import (
    DocumentDuplicateError,
    DocumentFileInvalidError,
    DocumentStorageError,
    DocumentTooLargeError,
    DocumentTypeUnsupportedError,
    KnowledgeBaseDocumentLimitReachedError,
)
from app.providers.embedding import EmbeddingProviderConfigurationError
from app.rag.vectorstores import VectorStoreConfigurationError
from app.main import app
from app.models import Document, DocumentChunk
from tests.pdf_factory import build_pdf
from tests.ingestion_fakes import (
    DeterministicEmbeddingProvider,
    InMemoryVectorStore,
)


@pytest.fixture
def api_context(
    tmp_path: Path,
) -> Iterator[
    tuple[
        TestClient,
        sessionmaker[Session],
        Settings,
        Path,
        InMemoryVectorStore,
    ]
]:
    from app import models as _models  # noqa: F401

    engine = create_db_engine(
        f"sqlite:///{tmp_path / 'document-api.db'}"
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    storage_root = tmp_path / "uploads"
    settings = Settings(
        _env_file=None,
        DOCUMENT_STORAGE_ROOT=storage_root,
        DOCUMENT_MAX_UPLOAD_BYTES=1024,
        DOCUMENT_MAX_FILES_PER_KNOWLEDGE_BASE=50,
    )
    embedding_provider = DeterministicEmbeddingProvider()
    vector_store = InMemoryVectorStore()

    async def override_db_session() -> AsyncIterator[Session]:
        session = factory()
        try:
            yield session
            session.commit()
            discard_async_rollback_callbacks(session)
        except Exception:
            session.rollback()
            await run_async_rollback_callbacks(session)
            raise
        finally:
            await run_async_session_finalizers(session)
            session.close()

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_embedding_provider] = (
        lambda: embedding_provider
    )
    app.dependency_overrides[get_vector_store] = lambda: vector_store
    with TestClient(app) as client:
        yield client, factory, settings, storage_root, vector_store
    app.dependency_overrides.clear()
    engine.dispose()


def _create_knowledge_base(client: TestClient, name: str = "Docs") -> str:
    response = client.post(
        "/api/v1/knowledge-bases",
        json={"name": name},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _document_count(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        return session.scalar(select(func.count(Document.id))) or 0


def _chunk_count(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        return session.scalar(select(func.count(DocumentChunk.id))) or 0


def _stored_files(storage_root: Path) -> list[Path]:
    if not storage_root.exists() or not storage_root.is_dir():
        return []
    return [
        path
        for path in storage_root.rglob("*")
        if path.is_file() and path.suffix != ".part"
    ]


def _assert_safe_error(
    response: Any,
    *,
    status_code: int,
    error_code: str,
    storage_root: Path,
    content: bytes = b"",
    internal_message: str = "",
) -> None:
    assert response.status_code == status_code
    assert response.json()["error"]["code"] == error_code
    response_text = response.text
    assert str(storage_root) not in response_text
    if content:
        assert hashlib.sha256(content).hexdigest() not in response_text
        assert content.decode("utf-8", errors="ignore") not in response_text
    if internal_message:
        assert internal_message not in response_text


def test_openapi_exposes_only_nested_document_upload(
    api_context: Any,
) -> None:
    client, _, _, _, _ = api_context
    document = client.get("/openapi.json").json()
    paths = document["paths"]
    upload_path = (
        "/api/v1/knowledge-bases/{knowledge_base_id}/documents"
    )

    assert set(paths[upload_path]) == {"post"}
    assert "/api/v1/documents" not in paths
    assert (
        "/api/v1/knowledge-bases/{knowledge_base_id}/documents/{document_id}"
        not in paths
    )
    operation = paths[upload_path]["post"]
    request_body = operation["requestBody"]
    assert request_body["required"] is True
    schema = request_body["content"]["multipart/form-data"]["schema"]
    if "$ref" in schema:
        schema = document["components"]["schemas"][
            schema["$ref"].rsplit("/", 1)[-1]
        ]
    assert schema["required"] == ["file"]
    file_schema = schema["properties"]["file"]
    assert file_schema["type"] == "string"
    assert file_schema["contentMediaType"] == "application/octet-stream"


@pytest.mark.parametrize(
    (
        "filename",
        "content",
        "content_type",
        "expected_type",
        "expected_format",
    ),
    [
        (
            "guide.md",
            b"# Synthetic",
            "text/markdown",
            "md",
            "markdown",
        ),
        (
            "notes.txt",
            b"Synthetic text",
            "text/plain",
            "txt",
            "txt",
        ),
        (
            "manual.pdf",
            build_pdf(["Synthetic PDF"]),
            "application/pdf",
            "pdf",
            "pdf",
        ),
    ],
)
def test_document_upload_accepts_supported_types(
    api_context: Any,
    filename: str,
    content: bytes,
    content_type: str,
    expected_type: str,
    expected_format: str,
) -> None:
    client, factory, _, storage_root, vector_store = api_context
    knowledge_base_id = _create_knowledge_base(client)

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": (filename, content, content_type)},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["knowledge_base_id"] == knowledge_base_id
    assert payload["original_filename"] == filename
    assert payload["file_type"] == expected_type
    assert payload["file_size"] == len(content)
    assert payload["file_hash"] == hashlib.sha256(content).hexdigest()
    assert payload["parse_status"] == "parsed"
    assert payload["chunk_status"] == "chunked"
    assert payload["embedding_status"] == "ready"
    assert payload["error_message"] is None
    assert payload["metadata"]["format"] == expected_format
    assert not Path(payload["file_path"]).is_absolute()
    assert PurePosixPath(payload["file_path"]).parts[0] == knowledge_base_id
    stored_path = storage_root.joinpath(
        *PurePosixPath(payload["file_path"]).parts
    )
    assert stored_path.read_bytes() == content
    with factory() as session:
        document = session.get(Document, UUID(payload["id"]))
        assert document is not None
        assert document.file_hash == payload["file_hash"]
        chunks = list(
            session.scalars(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == document.id)
                .order_by(DocumentChunk.chunk_index)
            )
        )
        assert chunks
        assert [chunk.chunk_index for chunk in chunks] == list(
            range(len(chunks))
        )
        assert all(chunk.vector_id == str(chunk.id) for chunk in chunks)
        assert set(vector_store.points) == {chunk.id for chunk in chunks}
        assert all(
            point.payload.document_id == document.id
            and point.payload.knowledge_base_id == document.knowledge_base_id
            for point in vector_store.points.values()
        )


@pytest.mark.parametrize(
    (
        "filename",
        "content",
        "content_type",
        "parse_status",
        "error_message",
    ),
    [
        (
            "invalid.txt",
            b"\x80private invalid text",
            "text/plain",
            "failed",
            "Document parsing failed.",
        ),
        (
            "scanned.pdf",
            build_pdf([None]),
            "application/pdf",
            "failed",
            (
                "Scanned or image-only PDF requires OCR, which is not "
                "supported in Plan 3."
            ),
        ),
        (
            "blank.txt",
            b" \r\n\t\r\n",
            "text/plain",
            "parsed",
            "Document contains no usable text.",
        ),
    ],
)
def test_document_upload_persists_content_processing_failure(
    api_context: Any,
    filename: str,
    content: bytes,
    content_type: str,
    parse_status: str,
    error_message: str,
) -> None:
    client, factory, _, storage_root, _ = api_context
    knowledge_base_id = _create_knowledge_base(client)

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": (filename, content, content_type)},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["parse_status"] == parse_status
    assert payload["chunk_status"] == "failed"
    assert payload["embedding_status"] == "failed"
    assert payload["error_message"] == error_message
    assert str(storage_root) not in response.text
    assert _document_count(factory) == 1
    assert _chunk_count(factory) == 0


def test_document_upload_sanitizes_client_path(
    api_context: Any,
) -> None:
    client, _, _, _, _ = api_context
    knowledge_base_id = _create_knowledge_base(client)

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        files={
            "file": (
                r"C:\fakepath\guide.md",
                b"synthetic",
                "text/markdown",
            )
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["original_filename"] == "guide.md"
    assert payload["filename"] == f"{payload['id']}.md"
    assert payload["file_path"] == (
        f"{knowledge_base_id}/{payload['id']}.md"
    )


def test_document_upload_requires_multipart_file(
    api_context: Any,
) -> None:
    client, factory, _, storage_root, _ = api_context
    knowledge_base_id = _create_knowledge_base(client)

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents"
    )

    _assert_safe_error(
        response,
        status_code=422,
        error_code="validation_error",
        storage_root=storage_root,
    )
    assert _document_count(factory) == 0


@pytest.mark.parametrize(
    ("filename", "content", "status_code", "error_code"),
    [
        ("empty.md", b"", 400, "document_file_invalid"),
        (
            "unsupported.csv",
            b"synthetic csv",
            415,
            "document_type_unsupported",
        ),
    ],
)
def test_document_upload_rejects_invalid_file(
    api_context: Any,
    filename: str,
    content: bytes,
    status_code: int,
    error_code: str,
) -> None:
    client, factory, _, storage_root, _ = api_context
    knowledge_base_id = _create_knowledge_base(client)

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": (filename, content, "application/octet-stream")},
    )

    _assert_safe_error(
        response,
        status_code=status_code,
        error_code=error_code,
        storage_root=storage_root,
        content=content,
    )
    assert _document_count(factory) == 0
    assert _chunk_count(factory) == 0
    assert _stored_files(storage_root) == []
    assert _chunk_count(factory) == 0


def test_document_upload_rejects_oversized_file(
    api_context: Any,
) -> None:
    client, factory, settings, storage_root, _ = api_context
    settings.document_max_upload_bytes = 8
    knowledge_base_id = _create_knowledge_base(client)
    content = b"123456789"

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": ("large.txt", content, "text/plain")},
    )

    _assert_safe_error(
        response,
        status_code=413,
        error_code="document_too_large",
        storage_root=storage_root,
        content=content,
    )
    assert _document_count(factory) == 0
    assert _stored_files(storage_root) == []


def test_document_upload_returns_safe_missing_knowledge_base(
    api_context: Any,
) -> None:
    client, factory, _, storage_root, _ = api_context
    content = b"private missing content"
    missing_id = uuid4()

    response = client.post(
        f"/api/v1/knowledge-bases/{missing_id}/documents",
        files={"file": ("missing.md", content, "text/markdown")},
    )

    _assert_safe_error(
        response,
        status_code=404,
        error_code="knowledge_base_not_found",
        storage_root=storage_root,
        content=content,
    )
    assert str(missing_id) not in response.text
    assert _document_count(factory) == 0
    assert not storage_root.exists()


def test_document_upload_rejects_same_knowledge_base_duplicate(
    api_context: Any,
) -> None:
    client, factory, _, storage_root, _ = api_context
    knowledge_base_id = _create_knowledge_base(client)
    content = b"duplicate content"
    first = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": ("first.md", content, "text/markdown")},
    )
    assert first.status_code == 201

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": ("second.txt", content, "text/plain")},
    )

    _assert_safe_error(
        response,
        status_code=409,
        error_code="document_duplicate",
        storage_root=storage_root,
        content=content,
    )
    assert _document_count(factory) == 1
    assert len(_stored_files(storage_root)) == 1


def test_document_upload_rejects_knowledge_base_document_limit(
    api_context: Any,
) -> None:
    client, factory, settings, storage_root, _ = api_context
    settings.document_max_files_per_knowledge_base = 1
    knowledge_base_id = _create_knowledge_base(client)
    first = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": ("first.md", b"first", "text/markdown")},
    )
    assert first.status_code == 201
    content = b"unique second"

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": ("second.txt", content, "text/plain")},
    )

    _assert_safe_error(
        response,
        status_code=409,
        error_code="knowledge_base_document_limit_reached",
        storage_root=storage_root,
        content=content,
    )
    assert _document_count(factory) == 1
    assert len(_stored_files(storage_root)) == 1


def test_document_upload_returns_safe_storage_error(
    api_context: Any,
) -> None:
    client, factory, settings, storage_root, _ = api_context
    knowledge_base_id = _create_knowledge_base(client)
    storage_root.write_text(
        "private-storage-diagnostic",
        encoding="utf-8",
    )
    settings.document_storage_root = storage_root
    content = b"private upload content"

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": ("failure.md", content, "text/markdown")},
    )

    _assert_safe_error(
        response,
        status_code=503,
        error_code="document_storage_error",
        storage_root=storage_root,
        content=content,
        internal_message="private-storage-diagnostic",
    )
    assert _document_count(factory) == 0


def test_document_upload_commit_failure_rolls_back_file(
    api_context: Any,
) -> None:
    client, factory, settings, storage_root, vector_store = api_context
    knowledge_base_id = _create_knowledge_base(client)

    class FailingCommitSession(Session):
        def commit(self) -> None:
            raise SQLAlchemyError(
                "private-document-commit-diagnostic"
            )

    failing_factory = sessionmaker(
        bind=factory.kw["bind"],
        class_=FailingCommitSession,
        expire_on_commit=False,
    )

    async def override_failing_session() -> AsyncIterator[Session]:
        session = failing_factory()
        try:
            yield session
            session.commit()
            discard_async_rollback_callbacks(session)
        except Exception:
            session.rollback()
            await run_async_rollback_callbacks(session)
            raise
        finally:
            await run_async_session_finalizers(session)
            session.close()

    app.dependency_overrides[get_db_session] = override_failing_session
    content = b"private commit content"
    with TestClient(app, raise_server_exceptions=False) as failing_client:
        response = failing_client.post(
            f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
            files={"file": ("commit.md", content, "text/markdown")},
        )

    _assert_safe_error(
        response,
        status_code=503,
        error_code="database_error",
        storage_root=storage_root,
        content=content,
        internal_message="private-document-commit-diagnostic",
    )
    assert _document_count(factory) == 0
    assert _stored_files(storage_root) == []
    assert vector_store.points == {}
    assert len(vector_store.deleted_documents) == 1
    staging = storage_root / ".staging"
    assert not staging.exists() or not any(staging.iterdir())
    app.dependency_overrides[get_settings] = lambda: settings


def test_document_upload_returns_safe_embedding_configuration_error(
    api_context: Any,
) -> None:
    client, factory, _, storage_root, vector_store = api_context
    knowledge_base_id = _create_knowledge_base(client)
    app.dependency_overrides.pop(get_embedding_provider)
    content = b"private provider configuration content"

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": ("provider.txt", content, "text/plain")},
    )

    _assert_safe_error(
        response,
        status_code=503,
        error_code="embedding_provider_unavailable",
        storage_root=storage_root,
        content=content,
    )
    assert _document_count(factory) == 0
    assert _chunk_count(factory) == 0
    assert _stored_files(storage_root) == []
    assert vector_store.points == {}


def test_document_upload_returns_safe_vector_store_configuration_error(
    api_context: Any,
) -> None:
    client, factory, _, storage_root, vector_store = api_context
    knowledge_base_id = _create_knowledge_base(client)
    app.dependency_overrides.pop(get_vector_store)
    content = b"private vector configuration content"

    response = client.post(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
        files={"file": ("vector.txt", content, "text/plain")},
    )

    _assert_safe_error(
        response,
        status_code=503,
        error_code="vector_store_unavailable",
        storage_root=storage_root,
        content=content,
    )
    assert _document_count(factory) == 0
    assert _chunk_count(factory) == 0
    assert _stored_files(storage_root) == []
    assert vector_store.points == {}


@pytest.mark.parametrize(
    ("error", "status_code", "code", "message"),
    [
        (
            DocumentFileInvalidError(),
            400,
            "document_file_invalid",
            "The uploaded document is invalid",
        ),
        (
            DocumentTooLargeError(),
            413,
            "document_too_large",
            "The uploaded document exceeds the size limit",
        ),
        (
            DocumentTypeUnsupportedError(),
            415,
            "document_type_unsupported",
            "The uploaded document type is not supported",
        ),
        (
            DocumentDuplicateError(),
            409,
            "document_duplicate",
            "The document already exists in this knowledge base",
        ),
        (
            KnowledgeBaseDocumentLimitReachedError(),
            409,
            "knowledge_base_document_limit_reached",
            "The knowledge base document limit was reached",
        ),
        (
            EmbeddingProviderConfigurationError(),
            503,
            "embedding_provider_unavailable",
            "The embedding provider is unavailable",
        ),
        (
            VectorStoreConfigurationError(),
            503,
            "vector_store_unavailable",
            "The vector store is unavailable",
        ),
        (
            DocumentStorageError(),
            503,
            "document_storage_error",
            "The document storage operation failed",
        ),
    ],
)
def test_document_error_mapping_is_stable_and_safe(
    error: Exception,
    status_code: int,
    code: str,
    message: str,
) -> None:
    spec = error_spec_for_exception(error)

    assert spec.status_code == status_code
    assert spec.code == code
    assert spec.message == message
