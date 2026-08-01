import asyncio
import hashlib
import os
from pathlib import Path
from uuid import UUID

import pytest

from app.knowledge import (
    DocumentFileInvalidError,
    DocumentStorage,
    DocumentStorageError,
    DocumentTooLargeError,
    DocumentTypeUnsupportedError,
)

KNOWLEDGE_BASE_ID = UUID("11111111-1111-4111-8111-111111111111")
DOCUMENT_ID = UUID("22222222-2222-4222-8222-222222222222")


class ChunkedStream:
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


def promote_synthetic_document(storage: DocumentStorage) -> str:
    staged = asyncio.run(
        storage.stage(
            ChunkedStream(b"synthetic text"),
            original_filename="notes.txt",
        )
    )
    stored = storage.promote(
        staged,
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        document_id=DOCUMENT_ID,
    )
    return stored.relative_path


def test_storage_stages_stream_and_calculates_sha256(
    tmp_path: Path,
) -> None:
    content = b"synthetic document"
    stream = ChunkedStream(content)
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)

    staged = asyncio.run(
        storage.stage(stream, original_filename="Guide.MD")
    )

    assert staged.original_filename == "Guide.MD"
    assert staged.file_type == "md"
    assert staged.file_size == len(content)
    assert staged.file_hash == hashlib.sha256(content).hexdigest()
    assert staged.temporary_path.read_bytes() == content
    assert stream.read_calls >= 2


def test_storage_promotes_to_uuid_owned_relative_path(
    tmp_path: Path,
) -> None:
    content = b"synthetic text"
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)
    staged = asyncio.run(
        storage.stage(
            ChunkedStream(content),
            original_filename="notes.txt",
        )
    )
    knowledge_base_id = UUID("11111111-1111-4111-8111-111111111111")
    document_id = UUID("22222222-2222-4222-8222-222222222222")

    stored = storage.promote(
        staged,
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
    )

    expected = f"{knowledge_base_id}/{document_id}.txt"
    assert stored.filename == f"{document_id}.txt"
    assert stored.relative_path == expected
    assert not staged.temporary_path.exists()
    assert (storage.root / Path(expected)).read_bytes() == content


@pytest.mark.parametrize(
    "client_filename",
    [r"C:\fakepath\notes.txt", "../notes.txt"],
)
def test_storage_keeps_only_basename(
    tmp_path: Path,
    client_filename: str,
) -> None:
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)

    staged = asyncio.run(
        storage.stage(
            ChunkedStream(b"synthetic"),
            original_filename=client_filename,
        )
    )

    assert staged.original_filename == "notes.txt"
    assert staged.temporary_path.is_relative_to(storage.root)


@pytest.mark.parametrize(
    "client_filename",
    [None, "", "   ", "bad\x00.txt", "bad\x1f.txt", f"{'a' * 252}.txt"],
)
def test_storage_rejects_invalid_filename(
    tmp_path: Path,
    client_filename: str | None,
) -> None:
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)

    with pytest.raises(DocumentFileInvalidError):
        asyncio.run(
            storage.stage(
                ChunkedStream(b"synthetic"),
                original_filename=client_filename,
            )
        )

    assert not storage.staging_directory.exists() or not any(
        storage.staging_directory.iterdir()
    )


@pytest.mark.parametrize(
    "client_filename",
    ["data.csv", "document.docx", "README", "manual.pdf.exe"],
)
def test_storage_rejects_unsupported_type(
    tmp_path: Path,
    client_filename: str,
) -> None:
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)

    with pytest.raises(DocumentTypeUnsupportedError):
        asyncio.run(
            storage.stage(
                ChunkedStream(b"synthetic"),
                original_filename=client_filename,
            )
        )

    assert not storage.staging_directory.exists() or not any(
        storage.staging_directory.iterdir()
    )


def test_storage_rejects_empty_file_and_removes_partial(
    tmp_path: Path,
) -> None:
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)

    with pytest.raises(DocumentFileInvalidError):
        asyncio.run(
            storage.stage(
                ChunkedStream(b""),
                original_filename="empty.md",
            )
        )

    assert not any(storage.staging_directory.iterdir())


def test_storage_rejects_oversized_file_and_removes_partial(
    tmp_path: Path,
) -> None:
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=8)

    with pytest.raises(DocumentTooLargeError):
        asyncio.run(
            storage.stage(
                ChunkedStream(b"123456789"),
                original_filename="large.txt",
            )
        )

    assert not any(storage.staging_directory.iterdir())


def test_storage_discard_helpers_are_idempotent(tmp_path: Path) -> None:
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)
    staged = asyncio.run(
        storage.stage(
            ChunkedStream(b"synthetic"),
            original_filename="notes.txt",
        )
    )

    storage.discard_staged(staged)
    storage.discard_staged(staged)

    second_staged = asyncio.run(
        storage.stage(
            ChunkedStream(b"synthetic"),
            original_filename="notes.txt",
        )
    )
    stored = storage.promote(
        second_staged,
        knowledge_base_id=UUID("11111111-1111-4111-8111-111111111111"),
        document_id=UUID("22222222-2222-4222-8222-222222222222"),
    )
    storage.discard_stored(stored.relative_path)
    storage.discard_stored(stored.relative_path)

    assert not staged.temporary_path.exists()
    assert not (storage.root / Path(stored.relative_path)).exists()


def test_storage_rejects_managed_symlink_or_reparse_directory(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "uploads"
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, storage_root, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")
    storage = DocumentStorage(storage_root, max_upload_bytes=1024)

    with pytest.raises(DocumentStorageError):
        asyncio.run(
            storage.stage(
                ChunkedStream(b"synthetic"),
                original_filename="notes.txt",
            )
        )


def test_storage_resolves_existing_uuid_owned_file(
    tmp_path: Path,
) -> None:
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)
    relative_path = promote_synthetic_document(storage)

    resolved = storage.resolve_stored(
        relative_path,
        knowledge_base_id=KNOWLEDGE_BASE_ID,
        document_id=DOCUMENT_ID,
        file_type="txt",
    )

    assert resolved == storage.root / Path(relative_path)
    assert resolved.is_file()


@pytest.mark.parametrize(
    "relative_path",
    [
        "../outside.txt",
        "not-a-uuid/file.txt",
        (
            f"{KNOWLEDGE_BASE_ID}/"
            "not-a-uuid.txt"
        ),
        f"{KNOWLEDGE_BASE_ID}/{DOCUMENT_ID}.exe",
        f"{KNOWLEDGE_BASE_ID}/nested\\{DOCUMENT_ID}.txt",
        f"{KNOWLEDGE_BASE_ID}\\{DOCUMENT_ID}.txt",
        f"{KNOWLEDGE_BASE_ID}/{DOCUMENT_ID}.TXT",
        f"{KNOWLEDGE_BASE_ID}/./{DOCUMENT_ID}.txt",
    ],
)
def test_storage_rejects_invalid_stored_path(
    tmp_path: Path,
    relative_path: str,
) -> None:
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)
    promote_synthetic_document(storage)
    nested = storage.root / str(KNOWLEDGE_BASE_ID) / "nested"
    nested.mkdir()
    (nested / f"{DOCUMENT_ID}.txt").write_text(
        "synthetic nested text",
        encoding="utf-8",
    )

    with pytest.raises(DocumentStorageError):
        storage.resolve_stored(
            relative_path,
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            document_id=DOCUMENT_ID,
            file_type="txt",
        )


@pytest.mark.parametrize("uppercase_part", ["knowledge_base", "document"])
def test_storage_rejects_noncanonical_uuid_case(
    tmp_path: Path,
    uppercase_part: str,
) -> None:
    knowledge_base_id = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    document_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)
    staged = asyncio.run(
        storage.stage(
            ChunkedStream(b"synthetic text"),
            original_filename="notes.txt",
        )
    )
    stored = storage.promote(
        staged,
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
    )
    raw_knowledge_base_id, filename = stored.relative_path.split("/", 1)
    raw_document_id, suffix = filename.rsplit(".", 1)
    if uppercase_part == "knowledge_base":
        raw_knowledge_base_id = raw_knowledge_base_id.upper()
    else:
        raw_document_id = raw_document_id.upper()
    relative_path = f"{raw_knowledge_base_id}/{raw_document_id}.{suffix}"

    with pytest.raises(DocumentStorageError):
        storage.resolve_stored(
            relative_path,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            file_type="txt",
        )


@pytest.mark.parametrize(
    ("knowledge_base_id", "document_id", "file_type"),
    [
        (
            UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            DOCUMENT_ID,
            "txt",
        ),
        (
            KNOWLEDGE_BASE_ID,
            UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
            "txt",
        ),
        (KNOWLEDGE_BASE_ID, DOCUMENT_ID, "md"),
    ],
)
def test_storage_rejects_stored_path_ownership_mismatch(
    tmp_path: Path,
    knowledge_base_id: UUID,
    document_id: UUID,
    file_type: str,
) -> None:
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)
    relative_path = promote_synthetic_document(storage)

    with pytest.raises(DocumentStorageError):
        storage.resolve_stored(
            relative_path,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            file_type=file_type,  # type: ignore[arg-type]
        )


def test_storage_rejects_missing_or_directory_stored_path(
    tmp_path: Path,
) -> None:
    storage = DocumentStorage(tmp_path / "uploads", max_upload_bytes=1024)
    relative_path = f"{KNOWLEDGE_BASE_ID}/{DOCUMENT_ID}.txt"
    directory_path = storage.root / Path(relative_path)
    directory_path.mkdir(parents=True)

    with pytest.raises(DocumentStorageError):
        storage.resolve_stored(
            relative_path,
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            document_id=DOCUMENT_ID,
            file_type="txt",
        )

    directory_path.rmdir()
    with pytest.raises(DocumentStorageError):
        storage.resolve_stored(
            relative_path,
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            document_id=DOCUMENT_ID,
            file_type="txt",
        )


@pytest.mark.parametrize("link_level", ["root", "knowledge_base", "file"])
def test_storage_resolver_rejects_symlink_or_reparse_ancestors(
    tmp_path: Path,
    link_level: str,
) -> None:
    storage_root = tmp_path / "uploads"
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_file = outside / f"{DOCUMENT_ID}.txt"
    outside_file.write_text("private outside", encoding="utf-8")
    knowledge_base_directory = storage_root / str(KNOWLEDGE_BASE_ID)
    stored_file = knowledge_base_directory / f"{DOCUMENT_ID}.txt"
    try:
        if link_level == "root":
            os.symlink(outside, storage_root, target_is_directory=True)
        elif link_level == "knowledge_base":
            storage_root.mkdir()
            os.symlink(
                outside,
                knowledge_base_directory,
                target_is_directory=True,
            )
        else:
            knowledge_base_directory.mkdir(parents=True)
            os.symlink(outside_file, stored_file)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")
    storage = DocumentStorage(storage_root, max_upload_bytes=1024)

    with pytest.raises(DocumentStorageError):
        storage.resolve_stored(
            f"{KNOWLEDGE_BASE_ID}/{DOCUMENT_ID}.txt",
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            document_id=DOCUMENT_ID,
            file_type="txt",
        )
