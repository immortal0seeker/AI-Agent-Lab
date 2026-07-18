from __future__ import annotations

import asyncio
import os
import stat
from pathlib import Path
from typing import Any

from app.tools.base import Tool, ToolResult
from app.tools.security import (
    DEFAULT_MAX_DIRECTORY_DEPTH,
    PROJECT_WORKSPACE_ROOT,
    ToolLimitError,
    ToolSecurityError,
    is_sensitive_path_component,
    resolve_workspace_path,
    validate_directory_depth,
)
from app.tools.validation import (
    ToolArgumentValidationError,
    validate_tool_arguments,
)


DEFAULT_LIST_DIR_DEPTH = 2
DEFAULT_MAX_LIST_ENTRIES = 500

_INVALID_ARGUMENTS_ERROR = "Invalid list_dir arguments"
_UNSAFE_PATH_ERROR = "The requested path is not allowed"
_NOT_FOUND_ERROR = "The requested directory was not found"
_NOT_DIRECTORY_ERROR = "The requested path is not a directory"
_LIST_ERROR = "The requested directory could not be listed"


def _require_positive_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return value


class ListDirTool(Tool):
    def __init__(
        self,
        *,
        workspace_root: Path = PROJECT_WORKSPACE_ROOT,
        max_depth: int = DEFAULT_MAX_DIRECTORY_DEPTH,
        max_entries: int = DEFAULT_MAX_LIST_ENTRIES,
    ) -> None:
        if not isinstance(workspace_root, Path):
            raise TypeError("workspace_root must be a Path")
        configured_depth = _require_positive_int(max_depth, "max_depth")
        try:
            validate_directory_depth(configured_depth)
        except ToolLimitError as exc:
            raise ValueError(
                f"max_depth must not exceed {DEFAULT_MAX_DIRECTORY_DEPTH}"
            ) from exc
        configured_entries = _require_positive_int(max_entries, "max_entries")
        default_depth = min(DEFAULT_LIST_DIR_DEPTH, configured_depth)

        super().__init__(
            name="list_dir",
            description="List files and directories in the workspace",
            parameters_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "max_depth": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": configured_depth,
                        "default": default_depth,
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            permission_level="read_only",
        )
        self.workspace_root = workspace_root.resolve()
        self.max_depth = configured_depth
        self.default_depth = default_depth
        self.max_entries = configured_entries

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        try:
            validated = validate_tool_arguments(self, arguments)
        except ToolArgumentValidationError:
            return self._failure(_INVALID_ARGUMENTS_ERROR)
        requested_depth = validated.get("max_depth", self.default_depth)
        return await asyncio.to_thread(
            self._list_dir,
            validated["path"],
            requested_depth,
        )

    def _list_dir(self, path: str, max_depth: int) -> ToolResult:
        try:
            resolved = resolve_workspace_path(
                path,
                workspace_root=self.workspace_root,
            )
        except ToolSecurityError:
            return self._failure(_UNSAFE_PATH_ERROR)
        except OSError:
            return self._failure(_LIST_ERROR)

        try:
            directory_stat = resolved.stat()
        except FileNotFoundError:
            return self._failure(_NOT_FOUND_ERROR)
        except OSError:
            return self._failure(_LIST_ERROR)

        if not stat.S_ISDIR(directory_stat.st_mode):
            return self._failure(_NOT_DIRECTORY_ERROR)

        entries: list[dict[str, str | int | None]] = []
        try:
            truncated = self._walk_directory(
                resolved,
                current_depth=1,
                max_depth=max_depth,
                entries=entries,
            )
        except FileNotFoundError:
            return self._failure(_NOT_FOUND_ERROR)
        except OSError:
            return self._failure(_LIST_ERROR)

        entries.sort(
            key=lambda entry: (
                str(entry["path"]).casefold(),
                str(entry["path"]),
            )
        )
        relative_root = resolved.relative_to(self.workspace_root).as_posix()
        content = "\n".join(
            "\t".join(
                (
                    str(entry["path"]),
                    str(entry["type"]),
                    (
                        "-"
                        if entry["size_bytes"] is None
                        else str(entry["size_bytes"])
                    ),
                )
            )
            for entry in entries
        )
        return ToolResult(
            tool_name=self.name,
            success=True,
            content=content,
            data={"entries": entries},
            metadata={
                "path": relative_root,
                "max_depth": max_depth,
                "entry_count": len(entries),
                "truncated": truncated,
            },
        )

    def _walk_directory(
        self,
        directory: Path,
        *,
        current_depth: int,
        max_depth: int,
        entries: list[dict[str, str | int | None]],
    ) -> bool:
        with os.scandir(directory) as iterator:
            children = sorted(
                iterator,
                key=lambda entry: (entry.name.casefold(), entry.name),
            )

        for child in children:
            if is_sensitive_path_component(child.name):
                continue
            if child.is_symlink():
                entry_type = "symlink"
                size_bytes = None
            elif child.is_dir(follow_symlinks=False):
                entry_type = "directory"
                size_bytes = None
            elif child.is_file(follow_symlinks=False):
                entry_type = "file"
                size_bytes = child.stat(follow_symlinks=False).st_size
            else:
                continue

            child_path = Path(child.path)
            relative_path = child_path.relative_to(
                self.workspace_root
            ).as_posix()
            entries.append(
                {
                    "path": relative_path,
                    "name": child.name,
                    "type": entry_type,
                    "size_bytes": size_bytes,
                }
            )
            if len(entries) >= self.max_entries:
                return True
            if entry_type == "directory" and current_depth < max_depth:
                if self._walk_directory(
                    child_path,
                    current_depth=current_depth + 1,
                    max_depth=max_depth,
                    entries=entries,
                ):
                    return True
        return False

    def _failure(self, error: str) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            success=False,
            error=error,
        )
