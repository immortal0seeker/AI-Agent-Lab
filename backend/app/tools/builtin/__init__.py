from pathlib import Path

from app.tools.builtin.read_file import (
    DEFAULT_MAX_READ_CHARACTERS,
    ReadFileTool,
)
from app.tools.registry import ToolRegistry
from app.tools.security import DEFAULT_MAX_FILE_BYTES, PROJECT_WORKSPACE_ROOT


def register_builtin_tools(
    registry: ToolRegistry,
    *,
    workspace_root: Path = PROJECT_WORKSPACE_ROOT,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_characters: int = DEFAULT_MAX_READ_CHARACTERS,
) -> None:
    if not isinstance(registry, ToolRegistry):
        raise TypeError("registry must be a ToolRegistry")
    registry.register_tool(
        ReadFileTool(
            workspace_root=workspace_root,
            max_file_bytes=max_file_bytes,
            max_characters=max_characters,
        )
    )


__all__ = [
    "DEFAULT_MAX_READ_CHARACTERS",
    "ReadFileTool",
    "register_builtin_tools",
]
