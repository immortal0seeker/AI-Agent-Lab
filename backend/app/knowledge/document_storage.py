from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal, Protocol
from uuid import UUID

from app.tools.security import is_reparse_point

from .errors import (
    DocumentError,
    DocumentFileInvalidError,
    DocumentStorageError,
    DocumentTooLargeError,
    DocumentTypeUnsupportedError,
)

UPLOAD_CHUNK_BYTES = 65_536
_SUPPORTED_SUFFIXES: dict[str, Literal["md", "txt", "pdf"]] = {
    ".md": "md",
    ".txt": "txt",
    ".pdf": "pdf",
}


class AsyncReadable(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


@dataclass(frozen=True)
class StagedDocument:
    temporary_path: Path
    original_filename: str
    file_type: Literal["md", "txt", "pdf"]
    file_size: int
    file_hash: str


@dataclass(frozen=True)
class StoredDocument:
    filename: str
    relative_path: str


class DocumentStorage:
    def __init__(self, root: Path, *, max_upload_bytes: int) -> None:
        self._root = Path(root).absolute()
        self._max_upload_bytes = max_upload_bytes

    @property
    def root(self) -> Path:
        return self._root

    @property
    def staging_directory(self) -> Path:
        return self._root / ".staging"

    async def stage(
        self,
        stream: AsyncReadable,
        *,
        original_filename: str | None,
    ) -> StagedDocument:
        safe_filename, file_type = self._validate_filename(original_filename)
        temporary_path: Path | None = None
        try:
            self._ensure_managed_directory(self._root)
            self._ensure_managed_directory(self.staging_directory)
            file_descriptor, raw_path = tempfile.mkstemp(
                prefix="upload-",
                suffix=".part",
                dir=self.staging_directory,
            )
            temporary_path = Path(raw_path)
            digest = hashlib.sha256()
            file_size = 0
            with os.fdopen(file_descriptor, "wb") as target:
                while True:
                    chunk = await stream.read(UPLOAD_CHUNK_BYTES)
                    if not isinstance(chunk, bytes):
                        raise DocumentStorageError()
                    if not chunk:
                        break
                    next_size = file_size + len(chunk)
                    if next_size > self._max_upload_bytes:
                        raise DocumentTooLargeError()
                    target.write(chunk)
                    digest.update(chunk)
                    file_size = next_size
            if file_size == 0:
                raise DocumentFileInvalidError()
            return StagedDocument(
                temporary_path=temporary_path,
                original_filename=safe_filename,
                file_type=file_type,
                file_size=file_size,
                file_hash=digest.hexdigest(),
            )
        except DocumentError:
            self._discard_temporary_path(temporary_path)
            raise
        except Exception as exc:
            self._discard_temporary_path(temporary_path)
            raise DocumentStorageError() from exc

    def promote(
        self,
        staged: StagedDocument,
        *,
        knowledge_base_id: UUID,
        document_id: UUID,
    ) -> StoredDocument:
        try:
            temporary_path = self._contained_path(staged.temporary_path)
            temporary_path.relative_to(self.staging_directory)
            temporary_stat = temporary_path.lstat()
            if (
                temporary_path.is_symlink()
                or is_reparse_point(temporary_stat)
                or not temporary_path.is_file()
            ):
                raise DocumentStorageError()
            knowledge_base_directory = self._root / str(knowledge_base_id)
            self._ensure_managed_directory(knowledge_base_directory)
            filename = f"{document_id}.{staged.file_type}"
            final_path = self._contained_path(
                knowledge_base_directory / filename
            )
            if final_path.exists() or final_path.is_symlink():
                raise DocumentStorageError()
            temporary_path.replace(final_path)
            return StoredDocument(
                filename=filename,
                relative_path=final_path.relative_to(self._root).as_posix(),
            )
        except DocumentError:
            raise
        except (OSError, ValueError) as exc:
            raise DocumentStorageError() from exc

    def discard_staged(self, staged: StagedDocument) -> None:
        try:
            path = self._contained_path(staged.temporary_path)
            path.relative_to(self.staging_directory)
            path.unlink(missing_ok=True)
        except (OSError, ValueError) as exc:
            raise DocumentStorageError() from exc

    def discard_stored(self, relative_path: str) -> None:
        try:
            path, _, _, _ = self._stored_path(relative_path)
            self._validate_managed_directory(self._root)
            self._validate_managed_directory(path.parent)
            path.unlink(missing_ok=True)
        except DocumentError:
            raise
        except (OSError, ValueError) as exc:
            raise DocumentStorageError() from exc

    def resolve_stored(
        self,
        relative_path: str,
        *,
        knowledge_base_id: UUID,
        document_id: UUID,
        file_type: Literal["md", "txt", "pdf"],
    ) -> Path:
        try:
            path, path_knowledge_base_id, path_document_id, path_file_type = (
                self._stored_path(relative_path)
            )
            if (
                path_knowledge_base_id != knowledge_base_id
                or path_document_id != document_id
                or path_file_type != file_type
            ):
                raise DocumentStorageError()
            self._validate_managed_directory(self._root)
            self._validate_managed_directory(path.parent)
            path_stat = path.lstat()
            if (
                path.is_symlink()
                or is_reparse_point(path_stat)
                or not path.is_file()
            ):
                raise DocumentStorageError()
            return path
        except DocumentError:
            raise
        except (OSError, ValueError) as exc:
            raise DocumentStorageError() from exc

    def _validate_filename(
        self,
        original_filename: str | None,
    ) -> tuple[str, Literal["md", "txt", "pdf"]]:
        if original_filename is None or not original_filename.strip():
            raise DocumentFileInvalidError()
        if any(ord(character) < 32 or ord(character) == 127 for character in original_filename):
            raise DocumentFileInvalidError()
        safe_filename = original_filename.replace("\\", "/").rsplit("/", 1)[-1]
        if (
            not safe_filename
            or not safe_filename.strip()
            or len(safe_filename) > 255
        ):
            raise DocumentFileInvalidError()
        file_type = _SUPPORTED_SUFFIXES.get(Path(safe_filename).suffix.lower())
        if file_type is None:
            raise DocumentTypeUnsupportedError()
        return safe_filename, file_type

    def _ensure_managed_directory(self, path: Path) -> None:
        candidate = self._contained_path(path)
        if candidate.exists() or candidate.is_symlink():
            self._validate_managed_directory(candidate)
            return
        candidate.mkdir(parents=True, exist_ok=False)
        self._validate_managed_directory(candidate)

    def _validate_managed_directory(self, path: Path) -> None:
        path_stat = path.lstat()
        if (
            path.is_symlink()
            or is_reparse_point(path_stat)
            or not path.is_dir()
        ):
            raise DocumentStorageError()

    def _stored_path(
        self,
        relative_path: str,
    ) -> tuple[
        Path,
        UUID,
        UUID,
        Literal["md", "txt", "pdf"],
    ]:
        normalized = PurePosixPath(relative_path)
        if normalized.is_absolute() or len(normalized.parts) != 2:
            raise ValueError("invalid stored document path")
        raw_knowledge_base_id, filename = normalized.parts
        knowledge_base_id = UUID(raw_knowledge_base_id)
        file_path = Path(filename)
        document_id = UUID(file_path.stem)
        file_type = _SUPPORTED_SUFFIXES.get(file_path.suffix.lower())
        if file_type is None:
            raise ValueError("invalid stored document suffix")
        path = self._contained_path(self._root.joinpath(*normalized.parts))
        return path, knowledge_base_id, document_id, file_type

    def _contained_path(self, path: Path) -> Path:
        candidate = Path(path).absolute()
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            raise DocumentStorageError() from exc
        return candidate

    def _discard_temporary_path(self, path: Path | None) -> None:
        if path is None:
            return
        try:
            candidate = self._contained_path(path)
            candidate.relative_to(self.staging_directory)
            candidate.unlink(missing_ok=True)
        except (OSError, ValueError, DocumentStorageError) as exc:
            raise DocumentStorageError() from exc
