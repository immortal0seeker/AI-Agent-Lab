import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from app.tools.builtin.list_dir import (
    DEFAULT_LIST_DIR_DEPTH,
    DEFAULT_MAX_LIST_ENTRIES,
    ListDirTool,
)


def run_tool(tool: ListDirTool, arguments: dict[str, Any]):
    return asyncio.run(tool.run(arguments))


def create_windows_junction(link: Path, target: Path) -> None:
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip("directory junctions are unavailable in this environment")


def test_list_dir_declares_stable_tool_metadata(tmp_path: Path) -> None:
    tool = ListDirTool(workspace_root=tmp_path)

    assert tool.name == "list_dir"
    assert tool.description == "List files and directories in the workspace"
    assert tool.permission_level == "read_only"
    assert tool.parameters_schema == {
        "type": "object",
        "properties": {
            "path": {"type": "string", "minLength": 1},
            "max_depth": {
                "type": "integer",
                "minimum": 1,
                "maximum": 3,
                "default": 2,
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    }
    assert tool.default_depth == DEFAULT_LIST_DIR_DEPTH
    assert tool.max_entries == DEFAULT_MAX_LIST_ENTRIES


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("max_depth", 0),
        ("max_depth", 4),
        ("max_depth", True),
        ("max_depth", "3"),
        ("max_entries", 0),
        ("max_entries", True),
    ],
)
def test_list_dir_rejects_invalid_limits(
    tmp_path: Path,
    field_name: str,
    value: object,
) -> None:
    overrides: dict[str, object] = {
        "workspace_root": tmp_path,
        field_name: value,
    }

    with pytest.raises((TypeError, ValueError), match=field_name):
        ListDirTool(**overrides)  # type: ignore[arg-type]


def test_list_dir_returns_stable_names_types_sizes_and_default_depth(
    tmp_path: Path,
) -> None:
    alpha = tmp_path / "alpha"
    nested = alpha / "nested"
    nested.mkdir(parents=True)
    (alpha / "direct.txt").write_text("x", encoding="utf-8")
    (nested / "deep.txt").write_text("deep", encoding="utf-8")
    (tmp_path / "root.txt").write_text("root", encoding="utf-8")

    result = run_tool(ListDirTool(workspace_root=tmp_path), {"path": "."})

    assert result.success is True
    assert result.error is None
    assert result.data == {
        "entries": [
            {
                "path": "alpha",
                "name": "alpha",
                "type": "directory",
                "size_bytes": None,
            },
            {
                "path": "alpha/direct.txt",
                "name": "direct.txt",
                "type": "file",
                "size_bytes": 1,
            },
            {
                "path": "alpha/nested",
                "name": "nested",
                "type": "directory",
                "size_bytes": None,
            },
            {
                "path": "root.txt",
                "name": "root.txt",
                "type": "file",
                "size_bytes": 4,
            },
        ]
    }
    assert result.content == (
        "alpha\tdirectory\t-\n"
        "alpha/direct.txt\tfile\t1\n"
        "alpha/nested\tdirectory\t-\n"
        "root.txt\tfile\t4"
    )
    assert result.metadata == {
        "path": ".",
        "max_depth": 2,
        "entry_count": 4,
        "truncated": False,
    }


def test_list_dir_applies_explicit_depth_semantics(tmp_path: Path) -> None:
    nested = tmp_path / "level1" / "level2"
    nested.mkdir(parents=True)
    (nested / "level3.txt").write_text("x", encoding="utf-8")
    tool = ListDirTool(workspace_root=tmp_path)

    shallow = run_tool(tool, {"path": ".", "max_depth": 1})
    deep = run_tool(tool, {"path": ".", "max_depth": 3})

    assert [entry["path"] for entry in shallow.data["entries"]] == [
        "level1"
    ]
    assert [entry["path"] for entry in deep.data["entries"]] == [
        "level1",
        "level1/level2",
        "level1/level2/level3.txt",
    ]


def test_list_dir_returns_success_for_empty_directory(tmp_path: Path) -> None:
    result = run_tool(ListDirTool(workspace_root=tmp_path), {"path": "."})

    assert result.success is True
    assert result.content == ""
    assert result.data == {"entries": []}
    assert result.metadata["entry_count"] == 0
    assert result.metadata["truncated"] is False


def test_list_dir_truncates_at_stable_entry_limit(tmp_path: Path) -> None:
    for name in ["c.txt", "a.txt", "b.txt"]:
        (tmp_path / name).write_text(name, encoding="utf-8")

    result = run_tool(
        ListDirTool(workspace_root=tmp_path, max_entries=2),
        {"path": "."},
    )

    assert result.success is True
    assert [entry["path"] for entry in result.data["entries"]] == [
        "a.txt",
        "b.txt",
    ]
    assert result.metadata["entry_count"] == 2
    assert result.metadata["truncated"] is True


def test_list_dir_does_not_report_truncation_at_exact_entry_limit(
    tmp_path: Path,
) -> None:
    for name in ["a.txt", "b.txt"]:
        (tmp_path / name).write_text(name, encoding="utf-8")

    result = run_tool(
        ListDirTool(workspace_root=tmp_path, max_entries=2),
        {"path": "."},
    )

    assert result.metadata["entry_count"] == 2
    assert result.metadata["truncated"] is False


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"path": 42},
        {"path": ".", "max_depth": 0},
        {"path": ".", "max_depth": 4},
        {"path": ".", "secret_extra": "do-not-leak"},
    ],
)
def test_list_dir_returns_safe_failure_for_invalid_arguments(
    tmp_path: Path,
    arguments: dict[str, Any],
) -> None:
    result = run_tool(ListDirTool(workspace_root=tmp_path), arguments)

    assert result.success is False
    assert result.error == "Invalid list_dir arguments"
    assert "do-not-leak" not in result.model_dump_json()


@pytest.mark.parametrize(
    "path",
    ["../outside", ".env", ".envrc", ".git", "docs-local"],
)
def test_list_dir_rejects_unsafe_roots_without_echoing_them(
    tmp_path: Path,
    path: str,
) -> None:
    result = run_tool(ListDirTool(workspace_root=tmp_path), {"path": path})

    assert result.success is False
    assert result.error == "The requested path is not allowed"
    assert path not in result.model_dump_json()


def test_list_dir_filters_sensitive_entries_before_traversal(
    tmp_path: Path,
) -> None:
    for name in [
        ".aws",
        ".git",
        ".ssh",
        "docs-local",
        "__pycache__",
    ]:
        directory = tmp_path / name
        directory.mkdir()
        (directory / "hidden.txt").write_text("secret", encoding="utf-8")
    for name in [
        ".env",
        ".env.local",
        ".envrc",
        ".npmrc",
        "id_rsa",
        "private.pem",
        "private.key",
    ]:
        (tmp_path / name).write_text("secret", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("dist/", encoding="utf-8")
    (tmp_path / "visible.txt").write_text("safe", encoding="utf-8")

    result = run_tool(
        ListDirTool(workspace_root=tmp_path),
        {"path": ".", "max_depth": 3},
    )

    assert result.success is True
    assert [entry["path"] for entry in result.data["entries"]] == [
        ".gitignore",
        "visible.txt",
    ]
    serialized = result.model_dump_json()
    assert "hidden.txt" not in serialized
    assert ".npmrc" not in serialized
    assert "secret" not in serialized


def test_list_dir_reports_but_never_follows_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "inside.txt").write_text("safe", encoding="utf-8")
    link = tmp_path / "linked"
    try:
        link.symlink_to(target, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("symbolic links are unavailable in this environment")

    result = run_tool(
        ListDirTool(workspace_root=tmp_path),
        {"path": ".", "max_depth": 3},
    )

    linked = next(
        entry for entry in result.data["entries"] if entry["path"] == "linked"
    )
    assert linked["type"] == "symlink"
    assert "linked/inside.txt" not in {
        entry["path"] for entry in result.data["entries"]
    }


@pytest.mark.skipif(os.name != "nt", reason="Windows reparse-point regression")
def test_list_dir_reports_but_never_follows_directory_junction(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (outside / "synthetic-marker.txt").write_text("safe", encoding="utf-8")
    junction = workspace / "junction-out"
    create_windows_junction(junction, outside)
    try:
        result = run_tool(
            ListDirTool(workspace_root=workspace),
            {"path": ".", "max_depth": 3},
        )

        assert result.success is True
        paths = {entry["path"] for entry in result.data["entries"]}
        linked = next(
            entry
            for entry in result.data["entries"]
            if entry["path"] == "junction-out"
        )
        assert linked["type"] == "symlink"
        assert "junction-out/synthetic-marker.txt" not in paths
    finally:
        if junction.exists():
            os.rmdir(junction)


def test_list_dir_returns_safe_failure_for_missing_directory(
    tmp_path: Path,
) -> None:
    result = run_tool(
        ListDirTool(workspace_root=tmp_path),
        {"path": "missing"},
    )

    assert result.success is False
    assert result.error == "The requested directory was not found"


def test_list_dir_rejects_regular_file(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_text("safe", encoding="utf-8")

    result = run_tool(
        ListDirTool(workspace_root=tmp_path),
        {"path": "file.txt"},
    )

    assert result.success is False
    assert result.error == "The requested path is not a directory"


def test_list_dir_returns_safe_failure_for_permission_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_listing(_: Path):
        raise PermissionError("credential-value")

    monkeypatch.setattr(os, "scandir", deny_listing)
    result = run_tool(ListDirTool(workspace_root=tmp_path), {"path": "."})

    assert result.success is False
    assert result.error == "The requested directory could not be listed"
    assert "credential-value" not in result.model_dump_json()
