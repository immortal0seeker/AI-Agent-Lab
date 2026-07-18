import json
from pathlib import Path

import pytest

from app.providers.llm.tool_adapter import build_llm_tool_definitions
from app.tools import ToolRegistry
from app.tools.builtin import register_builtin_tools


def test_adapter_builds_serializable_builtin_definitions(
    tmp_path: Path,
) -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry, workspace_root=tmp_path)

    definitions = build_llm_tool_definitions(registry)
    payload = [definition.model_dump(mode="json") for definition in definitions]

    assert [definition.function.name for definition in definitions] == [
        "read_file",
        "list_dir",
    ]
    assert [item["type"] for item in payload] == ["function", "function"]
    assert payload == registry.get_openai_tool_schemas()
    assert json.loads(json.dumps(payload)) == payload


def test_adapter_returns_empty_tuple_for_empty_registry() -> None:
    assert build_llm_tool_definitions(ToolRegistry()) == ()


def test_adapter_returns_definitions_independent_from_registry(
    tmp_path: Path,
) -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry, workspace_root=tmp_path)

    first_payload = [
        definition.model_dump(mode="json")
        for definition in build_llm_tool_definitions(registry)
    ]
    first_payload[0]["function"]["parameters"]["properties"]["path"][
        "type"
    ] = "integer"

    second_payload = [
        definition.model_dump(mode="json")
        for definition in build_llm_tool_definitions(registry)
    ]
    registry_payload = registry.get_openai_tool_schemas()

    assert (
        second_payload[0]["function"]["parameters"]["properties"]["path"][
            "type"
        ]
        == "string"
    )
    assert (
        registry_payload[0]["function"]["parameters"]["properties"]["path"][
            "type"
        ]
        == "string"
    )


def test_adapter_rejects_non_registry_input() -> None:
    with pytest.raises(TypeError, match="ToolRegistry"):
        build_llm_tool_definitions(object())  # type: ignore[arg-type]
