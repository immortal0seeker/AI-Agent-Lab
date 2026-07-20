import ast
import json
import tomllib
from pathlib import Path


EXPECTED_RELEASE_VERSION = "0.2.1"
BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent


def _fastapi_version() -> str:
    tree = ast.parse(
        (BACKEND_ROOT / "app" / "main.py").read_text(encoding="utf-8")
    )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "FastAPI":
            continue
        for keyword in node.keywords:
            if keyword.arg == "version" and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, str):
                    return keyword.value.value
    raise AssertionError("FastAPI version metadata is missing")


def test_backend_release_metadata_matches_plan2_version() -> None:
    project = tomllib.loads(
        (BACKEND_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert project["project"]["version"] == EXPECTED_RELEASE_VERSION
    assert _fastapi_version() == EXPECTED_RELEASE_VERSION


def test_frontend_release_metadata_matches_plan2_version() -> None:
    package = json.loads(
        (PROJECT_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    package_lock = json.loads(
        (PROJECT_ROOT / "frontend" / "package-lock.json").read_text(
            encoding="utf-8"
        )
    )

    assert package["version"] == EXPECTED_RELEASE_VERSION
    assert package_lock["version"] == EXPECTED_RELEASE_VERSION
    assert package_lock["packages"][""]["version"] == EXPECTED_RELEASE_VERSION
