import json
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictInt,
    StringConstraints,
    ValidationError,
    field_validator,
)

from app.models import Document, DocumentChunk


PayloadFilename = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
PayloadHeading = Annotated[str, StringConstraints(max_length=512)]
EmbeddingProviderName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
EmbeddingModelName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class ChunkVectorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    knowledge_base_id: UUID
    document_id: UUID
    chunk_id: UUID
    embedding_provider: EmbeddingProviderName
    embedding_model: EmbeddingModelName
    filename: PayloadFilename
    chunk_index: StrictInt = Field(ge=0)
    content: str
    heading: PayloadHeading | None = None
    page_number: StrictInt | None = Field(default=None, gt=0)
    metadata: dict[str, JsonValue]

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("content must not be blank")
        return value

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, value: object) -> object:
        return _normalize_json_object(value)

    def to_qdrant_payload(self) -> dict[str, JsonValue]:
        return self.model_dump(mode="json")  # type: ignore[return-value]


def build_qdrant_payload(
    *,
    document: Document,
    chunk: DocumentChunk,
    embedding_provider: str,
    embedding_model: str,
) -> ChunkVectorPayload:
    from app.rag.vectorstores.base import VectorStoreInputError

    if (
        chunk.document_id != document.id
        or chunk.knowledge_base_id != document.knowledge_base_id
    ):
        raise VectorStoreInputError(
            "Document and chunk ownership must match."
        )
    try:
        metadata = _normalize_json_object(chunk.metadata_json)
    except ValueError:
        raise VectorStoreInputError(
            "Chunk metadata must be a JSON-safe object."
        ) from None
    try:
        return ChunkVectorPayload(
            knowledge_base_id=chunk.knowledge_base_id,
            document_id=chunk.document_id,
            chunk_id=chunk.id,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            filename=document.filename,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            heading=chunk.heading,
            page_number=chunk.page_number,
            metadata=metadata,
        )
    except ValidationError:
        raise VectorStoreInputError("Chunk payload is invalid.") from None


def _normalize_json_object(value: object) -> dict[str, JsonValue]:
    if not isinstance(value, dict) or not _has_only_string_keys(value):
        raise ValueError("metadata must be a JSON object")
    try:
        serialized = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        normalized = json.loads(serialized)
    except (TypeError, ValueError) as exc:
        raise ValueError("metadata must be JSON-safe") from exc
    if not isinstance(normalized, dict):
        raise ValueError("metadata must be a JSON object")
    return normalized


def _has_only_string_keys(value: object) -> bool:
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _has_only_string_keys(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(_has_only_string_keys(item) for item in value)
    return True
