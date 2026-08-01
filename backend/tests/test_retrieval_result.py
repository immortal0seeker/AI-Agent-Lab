from math import inf, nan
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas import RetrievalResult


KNOWLEDGE_BASE_ID = UUID("00000000-0000-0000-0000-000000000001")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000002")
CHUNK_ID = UUID("00000000-0000-0000-0000-000000000003")


def retrieval_result_values(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "knowledge_base_id": KNOWLEDGE_BASE_ID,
        "document_id": DOCUMENT_ID,
        "chunk_id": CHUNK_ID,
        "filename": "guide.md",
        "chunk_index": 0,
        "content": "Retriever overview",
        "score": 0.91,
        "heading": "Overview",
        "page_number": None,
        "metadata": {
            "source_format": "md",
            "line_range": [1, 2],
        },
    }
    values.update(overrides)
    return values


def test_retrieval_result_serializes_complete_source() -> None:
    result = RetrievalResult.model_validate(retrieval_result_values())

    assert result.model_dump(mode="json") == {
        "knowledge_base_id": str(KNOWLEDGE_BASE_ID),
        "document_id": str(DOCUMENT_ID),
        "chunk_id": str(CHUNK_ID),
        "filename": "guide.md",
        "chunk_index": 0,
        "content": "Retriever overview",
        "score": 0.91,
        "heading": "Overview",
        "page_number": None,
        "metadata": {
            "source_format": "md",
            "line_range": [1, 2],
        },
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("filename", "   "),
        ("chunk_index", True),
        ("chunk_index", -1),
        ("content", "\n\t"),
        ("score", True),
        ("score", nan),
        ("score", inf),
        ("page_number", True),
        ("page_number", 0),
    ],
)
def test_retrieval_result_rejects_invalid_source_fields(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        RetrievalResult.model_validate(
            retrieval_result_values(**{field: value})
        )


def test_retrieval_result_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        RetrievalResult.model_validate(
            retrieval_result_values(rank=1)
        )
