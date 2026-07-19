import os
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath

from app.tools.base import ToolError


PROJECT_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MAX_FILE_BYTES = 1_048_576
DEFAULT_MAX_DIRECTORY_DEPTH = 3

_SENSITIVE_DIRECTORY_NAMES = frozenset(
    {
        ".aws",
        ".azure",
        ".docker",
        ".git",
        ".gnupg",
        ".kube",
        ".password-store",
        ".ssh",
        "__pycache__",
        "docs-local",
        "gcloud",
    }
)
_SENSITIVE_FILE_NAMES = frozenset(
    {
        ".git-credentials",
        ".netrc",
        ".npmrc",
        ".pypirc",
        "_netrc",
        "application_default_credentials.json",
        "client_secret.json",
        "credentials.json",
        "secrets.toml",
        "service-account.json",
        "service_account.json",
    }
)
_PRIVATE_KEY_NAMES = frozenset({"id_dsa", "id_ecdsa", "id_ed25519", "id_rsa"})


class ToolSecurityError(ToolError):
    """Tool 的只读路径或资源限制被拒绝。"""


class UnsafePathError(ToolSecurityError):
    pass


class ToolLimitError(ToolSecurityError):
    pass


def _path_parts(raw_path: str) -> tuple[str, ...]:
    return tuple(
        part
        for part in raw_path.replace("\\", "/").split("/")
        if part not in {"", "."}
    )


def _normalize_windows_component(component: str) -> str:
    normalized = component.rstrip(" ")
    if normalized in {".", ".."}:
        return normalized
    return normalized.rstrip(".")


def is_sensitive_path_component(component: str) -> bool:
    if not isinstance(component, str):
        raise TypeError("component must be a string")
    normalized = _normalize_windows_component(component).casefold()
    return (
        normalized in _SENSITIVE_DIRECTORY_NAMES
        or normalized in _SENSITIVE_FILE_NAMES
        or normalized.startswith(".env")
        or normalized in _PRIVATE_KEY_NAMES
        or normalized.endswith((".pem", ".key"))
    )


def is_reparse_point(path_stat: os.stat_result) -> bool:
    file_attributes = getattr(path_stat, "st_file_attributes", 0)
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
    return bool(file_attributes & reparse_attribute)


def resolve_workspace_path(
    path: str | Path,
    *,
    workspace_root: Path = PROJECT_WORKSPACE_ROOT,
) -> Path:
    if not isinstance(path, (str, Path)):
        raise TypeError("path must be a string or Path")
    raw_path = str(path)
    if not raw_path.strip() or "\x00" in raw_path:
        raise UnsafePathError("path must be non-blank and contain no NUL byte")

    windows_path = PureWindowsPath(raw_path)
    posix_path = PurePosixPath(raw_path)
    if windows_path.drive or windows_path.is_absolute() or posix_path.is_absolute():
        raise UnsafePathError(
            "absolute, drive-qualified, and UNC paths are forbidden"
        )

    raw_parts = _path_parts(raw_path)
    windows_normalized_parts = tuple(
        _normalize_windows_component(part) for part in raw_parts
    )
    if ".." in windows_normalized_parts:
        raise UnsafePathError("parent traversal is forbidden")
    if any(":" in part for part in raw_parts):
        raise UnsafePathError("Windows alternate data streams are forbidden")
    if any(is_sensitive_path_component(part) for part in raw_parts):
        raise UnsafePathError("sensitive workspace paths are forbidden")

    root = workspace_root.resolve()
    resolved = (root / Path(raw_path)).resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise UnsafePathError("path resolves outside the workspace") from exc
    if any(is_sensitive_path_component(part) for part in relative.parts):
        raise UnsafePathError("sensitive workspace paths are forbidden")
    return resolved


def _require_non_negative_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ToolLimitError(f"{field_name} must not be negative")
    return value


def validate_file_size(
    size_bytes: int,
    *,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> int:
    size_bytes = _require_non_negative_int(size_bytes, "file size")
    max_file_bytes = _require_non_negative_int(max_file_bytes, "file size limit")
    if size_bytes > max_file_bytes:
        raise ToolLimitError("file size exceeds the allowed limit")
    return size_bytes


def validate_directory_depth(
    depth: int,
    *,
    max_depth: int = DEFAULT_MAX_DIRECTORY_DEPTH,
) -> int:
    depth = _require_non_negative_int(depth, "directory depth")
    max_depth = _require_non_negative_int(max_depth, "directory depth limit")
    if depth > max_depth:
        raise ToolLimitError("directory depth exceeds the allowed limit")
    return depth
