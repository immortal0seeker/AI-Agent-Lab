from pathlib import Path

import pytest

from app.tools import (
    DEFAULT_MAX_DIRECTORY_DEPTH,
    DEFAULT_MAX_FILE_BYTES,
    ToolLimitError,
    UnsafePathError,
    resolve_workspace_path,
    validate_directory_depth,
    validate_file_size,
)


def test_resolve_workspace_path_accepts_safe_relative_path(tmp_path: Path) -> None:
    resolved = resolve_workspace_path(
        "docs/guide.md",
        workspace_root=tmp_path,
    )

    assert resolved == (tmp_path / "docs" / "guide.md").resolve()


def test_resolve_workspace_path_accepts_workspace_root(tmp_path: Path) -> None:
    assert resolve_workspace_path(".", workspace_root=tmp_path) == tmp_path.resolve()


@pytest.mark.parametrize("unsafe_path", ["", "   ", "safe\x00name"])
def test_resolve_workspace_path_rejects_blank_or_nul(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    with pytest.raises(UnsafePathError):
        resolve_workspace_path(unsafe_path, workspace_root=tmp_path)


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "/outside.txt",
        r"C:\outside.txt",
        r"C:outside.txt",
        r"\\server\share\secret.txt",
    ],
)
def test_resolve_workspace_path_rejects_absolute_drive_and_unc_paths(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    with pytest.raises(UnsafePathError):
        resolve_workspace_path(unsafe_path, workspace_root=tmp_path)


@pytest.mark.parametrize(
    "unsafe_path",
    ["../outside.txt", r"docs\..\secret.txt", r"docs\.. \secret.txt"],
)
def test_resolve_workspace_path_rejects_parent_traversal(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    with pytest.raises(UnsafePathError):
        resolve_workspace_path(unsafe_path, workspace_root=tmp_path)


@pytest.mark.parametrize(
    "unsafe_path",
    [
        ".env",
        ".envrc",
        ".env ",
        "config/.ENV.local",
        ".ssh/config",
        ".Git/config",
        "DOCS-LOCAL/review.md",
    ],
)
def test_resolve_workspace_path_rejects_sensitive_components(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    with pytest.raises(UnsafePathError):
        resolve_workspace_path(unsafe_path, workspace_root=tmp_path)


@pytest.mark.parametrize(
    "unsafe_path",
    [
        ".npmrc",
        ".pypirc",
        ".netrc",
        "_netrc",
        ".git-credentials",
        "credentials.json",
        "secrets.toml",
        ".aws/credentials",
        ".azure/accessTokens.json",
        ".kube/config",
        ".docker/config.json",
        ".gnupg/private-keys-v1.d/key",
        ".password-store/example.gpg",
        ".config/gcloud/application_default_credentials.json",
        "client_secret.json",
        "service-account.json",
        "service_account.json",
    ],
)
def test_resolve_workspace_path_rejects_credential_paths(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    with pytest.raises(UnsafePathError):
        resolve_workspace_path(unsafe_path, workspace_root=tmp_path)


@pytest.mark.parametrize(
    "unsafe_path",
    [".env:stream", "docs/file.txt:stream"],
)
def test_resolve_workspace_path_rejects_windows_alternate_data_streams(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    with pytest.raises(UnsafePathError):
        resolve_workspace_path(unsafe_path, workspace_root=tmp_path)


@pytest.mark.parametrize(
    "unsafe_path",
    ["id_rsa", "keys/id_ed25519", "certs/private.pem", "keys/PRIVATE.KEY"],
)
def test_resolve_workspace_path_rejects_private_key_files(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    with pytest.raises(UnsafePathError):
        resolve_workspace_path(unsafe_path, workspace_root=tmp_path)


def test_resolve_workspace_path_allows_non_secret_similar_name(tmp_path: Path) -> None:
    resolved = resolve_workspace_path("docs/keynote.md", workspace_root=tmp_path)

    assert resolved == (tmp_path / "docs" / "keynote.md").resolve()


def test_validate_file_size_accepts_limit_and_rejects_oversize() -> None:
    assert validate_file_size(DEFAULT_MAX_FILE_BYTES) == DEFAULT_MAX_FILE_BYTES
    with pytest.raises(ToolLimitError, match="file size"):
        validate_file_size(DEFAULT_MAX_FILE_BYTES + 1)


@pytest.mark.parametrize("size_bytes", [-1, True, "1"])
def test_validate_file_size_rejects_invalid_values(size_bytes: object) -> None:
    with pytest.raises((TypeError, ToolLimitError)):
        validate_file_size(size_bytes)  # type: ignore[arg-type]


def test_validate_directory_depth_accepts_limit_and_rejects_excess() -> None:
    assert (
        validate_directory_depth(DEFAULT_MAX_DIRECTORY_DEPTH)
        == DEFAULT_MAX_DIRECTORY_DEPTH
    )
    with pytest.raises(ToolLimitError, match="directory depth"):
        validate_directory_depth(DEFAULT_MAX_DIRECTORY_DEPTH + 1)


@pytest.mark.parametrize("depth", [-1, True, "1"])
def test_validate_directory_depth_rejects_invalid_values(depth: object) -> None:
    with pytest.raises((TypeError, ToolLimitError)):
        validate_directory_depth(depth)  # type: ignore[arg-type]
