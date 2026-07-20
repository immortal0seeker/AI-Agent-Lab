import json


class StandardJsonError(ValueError):
    """值无法安全表示为标准 JSON。"""


class StandardJsonSizeError(StandardJsonError):
    """标准 JSON 编码超过调用方声明的边界。"""


def ensure_standard_json(
    value: object,
    *,
    max_bytes: int | None = None,
) -> None:
    if max_bytes is not None:
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int):
            raise TypeError("max_bytes must be an integer")
        if max_bytes <= 0:
            raise ValueError("max_bytes must be greater than zero")
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StandardJsonError(
            "value must contain only standard JSON values"
        ) from exc
    if max_bytes is not None and len(encoded) > max_bytes:
        raise StandardJsonSizeError("value exceeds the allowed JSON size")
