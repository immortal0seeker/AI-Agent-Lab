from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from app.tools.base import Tool, ToolError


PathPart = str | int


class ToolSchemaError(ToolError):
    """Tool 参数 schema 无法按约定安全使用。"""


@dataclass(frozen=True, slots=True)
class ToolValidationIssue:
    path: tuple[PathPart, ...]
    code: str
    message: str


class ToolArgumentValidationError(ToolError):
    def __init__(
        self,
        tool_name: str,
        issues: list[ToolValidationIssue],
    ) -> None:
        self.tool_name = tool_name
        self.issues = tuple(issues)
        summary = "; ".join(
            f"{_format_path(issue.path)} [{issue.code}] {issue.message}"
            for issue in self.issues
        )
        super().__init__(f"Invalid arguments for tool '{tool_name}': {summary}")


_SAFE_MESSAGES = {
    "additionalProperties": "unknown properties are not allowed",
    "enum": "value is not one of the allowed options",
    "maxItems": "array contains too many items",
    "maxLength": "text is too long",
    "maximum": "number is above the allowed maximum",
    "minItems": "array contains too few items",
    "minLength": "text is too short",
    "minimum": "number is below the allowed minimum",
    "pattern": "text does not match the required pattern",
    "required": "a required property is missing",
    "type": "value has an invalid type",
}


def _format_path(path: tuple[PathPart, ...]) -> str:
    if not path:
        return "$"
    escaped = [
        str(part).replace("~", "~0").replace("/", "~1") for part in path
    ]
    return "$/" + "/".join(escaped)


def _issue_from_error(error: ValidationError) -> ToolValidationIssue:
    code = str(error.validator or "schema")
    return ToolValidationIssue(
        path=tuple(error.absolute_path),
        code=code,
        message=_SAFE_MESSAGES.get(
            code,
            f"argument does not satisfy schema rule '{code}'",
        ),
    )


def validate_tool_schema(schema: Mapping[str, Any]) -> None:
    if not isinstance(schema, Mapping):
        raise ToolSchemaError("Tool parameter schema must be an object")
    try:
        Draft202012Validator.check_schema(dict(schema))
    except SchemaError as exc:
        raise ToolSchemaError("Invalid Tool parameter schema") from exc


def validate_tool_arguments(
    tool: Tool,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    validate_tool_schema(tool.parameters_schema)
    if not isinstance(arguments, Mapping):
        raise ToolArgumentValidationError(
            tool.name,
            [ToolValidationIssue((), "type", "arguments must be an object")],
        )

    payload = deepcopy(dict(arguments))
    validator = Draft202012Validator(tool.parameters_schema)
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            str(error.validator or "schema"),
            tuple(str(part) for part in error.absolute_schema_path),
        ),
    )
    if errors:
        raise ToolArgumentValidationError(
            tool.name,
            [_issue_from_error(error) for error in errors],
        )
    return payload
