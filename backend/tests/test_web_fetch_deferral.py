import importlib.util
from pathlib import Path

import app.tools.builtin as builtin_tools
from app.tools import ToolRegistry, register_builtin_tools


def test_web_fetch_has_no_executable_builtin_surface(tmp_path: Path) -> None:
    assert importlib.util.find_spec("app.tools.builtin.web_fetch") is None
    assert "WebFetchTool" not in builtin_tools.__all__
    assert "web_fetch" not in builtin_tools.__all__

    registry = ToolRegistry()
    register_builtin_tools(registry, workspace_root=tmp_path)

    assert [tool.name for tool in registry.list_tools()] == [
        "read_file",
        "list_dir",
    ]
    assert [
        schema["function"]["name"]
        for schema in registry.get_openai_tool_schemas()
    ] == ["read_file", "list_dir"]
