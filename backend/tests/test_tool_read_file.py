import asyncio
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

from app.tools import (
    DEFAULT_LIST_DIR_DEPTH,
    DEFAULT_MAX_LIST_ENTRIES,
    DuplicateToolError,
    ListDirTool,
    ToolRegistry,
    register_builtin_tools,
)
from app.tools.builtin.read_file import (
    DEFAULT_MAX_READ_CHARACTERS,
    ReadFileTool,
)


def run_tool(tool: ReadFileTool, arguments: dict[str, Any]):
    return asyncio.run(tool.run(arguments))


def test_read_file_declares_stable_tool_metadata(tmp_path: Path) -> None:
    tool = ReadFileTool(workspace_root=tmp_path)

    assert tool.name == "read_file"
    assert tool.description == "Read a UTF-8 text file from the workspace"
    assert tool.permission_level == "read_only"
    assert tool.parameters_schema == {
        "type": "object",
        "properties": {
            "path": {"type": "string", "minLength": 1},
        },
        "required": ["path"],
        "additionalProperties": False,
    }
    assert tool.max_characters == DEFAULT_MAX_READ_CHARACTERS


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("max_file_bytes", 0),
        ("max_file_bytes", True),
        ("max_file_bytes", "1"),
        ("max_characters", -1),
        ("max_characters", True),
        ("max_characters", "1"),
    ],
)
def test_read_file_rejects_invalid_limits(
    tmp_path: Path,
    field_name: str,
    value: object,
) -> None:
    overrides: dict[str, object] = {
        "workspace_root": tmp_path,
        field_name: value,
    }

    with pytest.raises((TypeError, ValueError), match=field_name):
        ReadFileTool(**overrides)  # type: ignore[arg-type]


def test_read_file_reads_utf8_text_and_returns_metadata(tmp_path: Path) -> None:
    content = "# Guide\n你好，workspace\n"
    raw = content.encode("utf-8")
    (tmp_path / "README.md").write_bytes(raw)

    result = run_tool(ReadFileTool(workspace_root=tmp_path), {"path": "README.md"})

    assert result.success is True
    assert result.content == content
    assert result.error is None
    assert result.metadata == {
        "path": "README.md",
        "encoding": "utf-8",
        "size_bytes": len(raw),
        "character_count": len(content),
        "returned_characters": len(content),
        "truncated": False,
    }


def test_read_file_accepts_utf8_bom_without_returning_the_bom(tmp_path: Path) -> None:
    text = "BOM text"
    raw = b"\xef\xbb\xbf" + text.encode("utf-8")
    (tmp_path / "bom.txt").write_bytes(raw)

    result = run_tool(ReadFileTool(workspace_root=tmp_path), {"path": "bom.txt"})

    assert result.success is True
    assert result.content == text
    assert result.metadata["size_bytes"] == len(raw)
    assert result.metadata["character_count"] == len(text)


def test_read_file_truncates_by_character_with_explicit_metadata(
    tmp_path: Path,
) -> None:
    (tmp_path / "long.txt").write_text("abcdef", encoding="utf-8")
    tool = ReadFileTool(workspace_root=tmp_path, max_characters=4)

    result = run_tool(tool, {"path": "long.txt"})

    assert result.success is True
    assert result.content == "abcd"
    assert result.metadata["character_count"] == 6
    assert result.metadata["returned_characters"] == 4
    assert result.metadata["truncated"] is True


def test_read_file_default_workspace_reads_tracked_readme() -> None:
    result = run_tool(ReadFileTool(), {"path": "README.md"})

    assert result.success is True
    assert result.content.startswith("# AI Agent Lab")
    assert result.metadata["path"] == "README.md"


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"path": 42},
        {"path": "README.md", "secret_extra": "do-not-leak"},
    ],
)
def test_read_file_returns_safe_failure_for_invalid_arguments(
    tmp_path: Path,
    arguments: dict[str, Any],
) -> None:
    result = run_tool(ReadFileTool(workspace_root=tmp_path), arguments)

    assert result.success is False
    assert result.error == "Invalid read_file arguments"
    assert "do-not-leak" not in result.model_dump_json()


@pytest.mark.parametrize("path", [".env", "../outside.txt", "id_rsa"])
def test_read_file_rejects_unsafe_paths_without_echoing_them(
    tmp_path: Path,
    path: str,
) -> None:
    result = run_tool(ReadFileTool(workspace_root=tmp_path), {"path": path})

    assert result.success is False
    assert result.error == "The requested path is not allowed"
    assert path not in result.model_dump_json()


def test_read_file_returns_safe_failure_for_missing_file(tmp_path: Path) -> None:
    result = run_tool(
        ReadFileTool(workspace_root=tmp_path),
        {"path": "missing.txt"},
    )

    assert result.success is False
    assert result.error == "The requested file was not found"


def test_read_file_rejects_directory(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()

    result = run_tool(ReadFileTool(workspace_root=tmp_path), {"path": "docs"})

    assert result.success is False
    assert result.error == "The requested path is not a regular file"


def test_read_file_rejects_oversized_file_before_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "large.txt").write_bytes(b"x" * 11)

    def fail_if_open(_: Path, *args: object, **kwargs: object):
        pytest.fail("oversized file content must not be read")

    monkeypatch.setattr(Path, "open", fail_if_open)
    result = run_tool(
        ReadFileTool(workspace_root=tmp_path, max_file_bytes=10),
        {"path": "large.txt"},
    )

    assert result.success is False
    assert result.error == "The requested file exceeds the size limit"


def test_read_file_bounds_actual_read_when_file_grows_after_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_path = tmp_path / "growing.txt"
    file_path.write_bytes(b"small")

    class TrackingReader(BytesIO):
        read_sizes: list[int]

        def __init__(self, initial_bytes: bytes) -> None:
            super().__init__(initial_bytes)
            self.read_sizes = []

        def read(self, size: int = -1) -> bytes:
            self.read_sizes.append(size)
            return super().read(size)

    reader = TrackingReader(b"x" * 100)

    def open_growing_file(
        path: Path,
        mode: str = "r",
        *args: object,
        **kwargs: object,
    ) -> TrackingReader:
        assert path == file_path
        assert mode == "rb"
        return reader

    monkeypatch.setattr(Path, "open", open_growing_file)
    result = run_tool(
        ReadFileTool(workspace_root=tmp_path, max_file_bytes=10),
        {"path": "growing.txt"},
    )

    assert result.success is False
    assert result.error == "The requested file exceeds the size limit"
    assert reader.read_sizes == [11]


@pytest.mark.parametrize(
    "raw",
    [
        b"safe\x00hidden-value",
        b"\xffhidden-value",
    ],
)
def test_read_file_rejects_binary_or_non_utf8_without_content_leak(
    tmp_path: Path,
    raw: bytes,
) -> None:
    (tmp_path / "binary.dat").write_bytes(raw)

    result = run_tool(
        ReadFileTool(workspace_root=tmp_path),
        {"path": "binary.dat"},
    )

    assert result.success is False
    assert result.error == "The requested file is not supported UTF-8 text"
    assert "hidden-value" not in result.model_dump_json()


def test_read_file_returns_safe_failure_for_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "unreadable.txt").write_text("safe", encoding="utf-8")

    def raise_oserror(
        _: Path,
        *args: object,
        **kwargs: object,
    ):
        raise OSError("credential-value")

    monkeypatch.setattr(Path, "open", raise_oserror)
    result = run_tool(
        ReadFileTool(workspace_root=tmp_path),
        {"path": "unreadable.txt"},
    )

    assert result.success is False
    assert result.error == "The requested file could not be read"
    assert "credential-value" not in result.model_dump_json()


def test_register_builtin_tools_adds_both_tools_with_exportable_schemas(
    tmp_path: Path,
) -> None:
    registry = ToolRegistry()

    register_builtin_tools(
        registry,
        workspace_root=tmp_path,
        max_file_bytes=123,
        max_characters=45,
        max_directory_depth=1,
        max_directory_entries=7,
    )

    read_file = registry.get_tool("read_file")
    list_dir = registry.get_tool("list_dir")
    assert isinstance(read_file, ReadFileTool)
    assert read_file.workspace_root == tmp_path.resolve()
    assert read_file.max_file_bytes == 123
    assert read_file.max_characters == 45
    assert isinstance(list_dir, ListDirTool)
    assert DEFAULT_LIST_DIR_DEPTH == 2
    assert DEFAULT_MAX_LIST_ENTRIES == 500
    assert list_dir.workspace_root == tmp_path.resolve()
    assert list_dir.max_depth == 1
    assert list_dir.default_depth == 1
    assert list_dir.max_entries == 7
    assert [registered.name for registered in registry.list_tools()] == [
        "read_file",
        "list_dir",
    ]
    schemas = registry.get_openai_tool_schemas()
    assert [schema["function"]["name"] for schema in schemas] == [
        "read_file",
        "list_dir",
    ]
    assert schemas[1] == {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories in the workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "max_depth": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1,
                        "default": 1,
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    }


def test_register_builtin_tools_preserves_duplicate_error(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry, workspace_root=tmp_path)

    with pytest.raises(DuplicateToolError, match="read_file"):
        register_builtin_tools(registry, workspace_root=tmp_path)

    assert [tool.name for tool in registry.list_tools()] == [
        "read_file",
        "list_dir",
    ]


def test_register_builtin_tools_rejects_invalid_list_config_atomically(
    tmp_path: Path,
) -> None:
    registry = ToolRegistry()

    with pytest.raises(ValueError, match="max_entries"):
        register_builtin_tools(
            registry,
            workspace_root=tmp_path,
            max_directory_entries=0,
        )

    assert registry.list_tools() == []


def test_register_builtin_tools_rejects_existing_list_dir_atomically(
    tmp_path: Path,
) -> None:
    registry = ToolRegistry()
    existing = ListDirTool(workspace_root=tmp_path)
    registry.register_tool(existing)

    with pytest.raises(DuplicateToolError, match="list_dir"):
        register_builtin_tools(registry, workspace_root=tmp_path)

    assert registry.list_tools() == [existing]


def test_register_builtin_tools_rejects_non_registry(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="ToolRegistry"):
        register_builtin_tools(  # type: ignore[arg-type]
            object(),
            workspace_root=tmp_path,
        )
