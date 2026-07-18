from pathlib import Path

from app.tools.builtin.list_dir import (
    DEFAULT_LIST_DIR_DEPTH,
    DEFAULT_MAX_LIST_ENTRIES,
    ListDirTool,
)
from app.tools.builtin.read_file import (
    DEFAULT_MAX_READ_CHARACTERS,
    ReadFileTool,
)
from app.tools.registry import DuplicateToolError, ToolRegistry
from app.tools.security import (
    DEFAULT_MAX_DIRECTORY_DEPTH,
    DEFAULT_MAX_FILE_BYTES,
    PROJECT_WORKSPACE_ROOT,
)


def register_builtin_tools(
    registry: ToolRegistry,
    *,
    workspace_root: Path = PROJECT_WORKSPACE_ROOT,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_characters: int = DEFAULT_MAX_READ_CHARACTERS,
    max_directory_depth: int = DEFAULT_MAX_DIRECTORY_DEPTH,
    max_directory_entries: int = DEFAULT_MAX_LIST_ENTRIES,
) -> None:
    if not isinstance(registry, ToolRegistry):
        raise TypeError("registry must be a ToolRegistry")
    tools = (
        ReadFileTool(
            workspace_root=workspace_root,
            max_file_bytes=max_file_bytes,
            max_characters=max_characters,
        ),
        ListDirTool(
            workspace_root=workspace_root,
            max_depth=max_directory_depth,
            max_entries=max_directory_entries,
        ),
    )
    existing_names = {tool.name for tool in registry.list_tools()}
    for tool in tools:
        if tool.name in existing_names:
            raise DuplicateToolError(
                f"Duplicate Tool registration: {tool.name}"
            )
    for tool in tools:
        registry.register_tool(tool)


__all__ = [
    "DEFAULT_LIST_DIR_DEPTH",
    "DEFAULT_MAX_LIST_ENTRIES",
    "DEFAULT_MAX_READ_CHARACTERS",
    "ListDirTool",
    "ReadFileTool",
    "register_builtin_tools",
]
