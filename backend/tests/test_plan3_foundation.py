import importlib
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).parents[2]


def test_qdrant_compose_contract() -> None:
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text(
        encoding="utf-8"
    )

    assert "qdrant/qdrant:v1.15.4" in compose
    assert '"6333:6333"' in compose
    assert "qdrant_data:/qdrant/storage" in compose
    assert "\n  qdrant_data:\n" in compose
    assert 'QDRANT__TELEMETRY_DISABLED: "true"' in compose


@pytest.mark.parametrize(
    ("package_name", "ownership"),
    [
        ("app.knowledge", "知识库结构化元数据与编排边界。"),
        ("app.rag", "文档处理与 Naive RAG 流水线边界。"),
    ],
)
def test_plan3_packages_define_ownership(
    package_name: str,
    ownership: str,
) -> None:
    package = importlib.import_module(package_name)

    assert package.__doc__ == ownership
