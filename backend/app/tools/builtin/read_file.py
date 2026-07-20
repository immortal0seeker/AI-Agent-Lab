from __future__ import annotations

import asyncio
import stat
from pathlib import Path
from typing import Any

from app.tools.base import Tool, ToolResult
from app.tools.security import (
    DEFAULT_MAX_FILE_BYTES,
    MAX_TOOL_PATH_CHARACTERS,
    PROJECT_WORKSPACE_ROOT,
    ToolLimitError,
    ToolSecurityError,
    contains_private_key_material,
    resolve_workspace_path,
    validate_file_size,
)
from app.tools.validation import (
    ToolArgumentValidationError,
    validate_tool_arguments,
)


DEFAULT_MAX_READ_CHARACTERS = 100_000

_INVALID_ARGUMENTS_ERROR = "Invalid read_file arguments"
_UNSAFE_PATH_ERROR = "The requested path is not allowed"
_NOT_FOUND_ERROR = "The requested file was not found"
_NOT_FILE_ERROR = "The requested path is not a regular file"
_TOO_LARGE_ERROR = "The requested file exceeds the size limit"
_UNSUPPORTED_TEXT_ERROR = "The requested file is not supported UTF-8 text"
_READ_ERROR = "The requested file could not be read"


def _require_positive_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return value


class ReadFileTool(Tool):
    def __init__(
        self,
        *,
        workspace_root: Path = PROJECT_WORKSPACE_ROOT,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        max_characters: int = DEFAULT_MAX_READ_CHARACTERS,
    ) -> None:
        super().__init__(
            name="read_file",
            description="Read a UTF-8 text file from the workspace",
            parameters_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": MAX_TOOL_PATH_CHARACTERS,
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            permission_level="read_only",
        )
        if not isinstance(workspace_root, Path):
            raise TypeError("workspace_root must be a Path")
        self.workspace_root = workspace_root.resolve()
        self.max_file_bytes = _require_positive_int(
            max_file_bytes,
            "max_file_bytes",
        )
        self.max_characters = _require_positive_int(
            max_characters,
            "max_characters",
        )

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        try:
            validated = validate_tool_arguments(self, arguments)
        except ToolArgumentValidationError:
            return self._failure(_INVALID_ARGUMENTS_ERROR)
        return await asyncio.to_thread(self._read_file, validated["path"])

    def _read_file(self, path: str) -> ToolResult:
        try:
            resolved = resolve_workspace_path(
                path,
                workspace_root=self.workspace_root,
            )
        except ToolSecurityError:
            return self._failure(_UNSAFE_PATH_ERROR)
        except OSError:
            return self._failure(_READ_ERROR)

        try:
            file_stat = resolved.stat()
        except FileNotFoundError:
            return self._failure(_NOT_FOUND_ERROR)
        except OSError:
            return self._failure(_READ_ERROR)

        if not stat.S_ISREG(file_stat.st_mode):
            return self._failure(_NOT_FILE_ERROR)

        try:
            validate_file_size(
                file_stat.st_size,
                max_file_bytes=self.max_file_bytes,
            )
        except ToolLimitError:
            return self._failure(_TOO_LARGE_ERROR)

        try:
            with resolved.open("rb") as file:
                raw = file.read(self.max_file_bytes + 1)
        except FileNotFoundError:
            return self._failure(_NOT_FOUND_ERROR)
        except OSError:
            return self._failure(_READ_ERROR)

        try:
            validate_file_size(len(raw), max_file_bytes=self.max_file_bytes)
        except ToolLimitError:
            return self._failure(_TOO_LARGE_ERROR)

        if contains_private_key_material(raw):
            return self._failure(_UNSAFE_PATH_ERROR)
        if b"\x00" in raw:
            return self._failure(_UNSUPPORTED_TEXT_ERROR)
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return self._failure(_UNSUPPORTED_TEXT_ERROR)

        content = text[: self.max_characters]
        relative_path = resolved.relative_to(self.workspace_root).as_posix()
        return ToolResult(
            tool_name=self.name,
            success=True,
            content=content,
            metadata={
                "path": relative_path,
                "encoding": "utf-8",
                "size_bytes": len(raw),
                "character_count": len(text),
                "returned_characters": len(content),
                "truncated": len(content) < len(text),
            },
        )

    def _failure(self, error: str) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            success=False,
            error=error,
        )
