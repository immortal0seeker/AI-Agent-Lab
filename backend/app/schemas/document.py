from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)


DocumentFileType = Literal["md", "txt", "pdf"]
DocumentParseStatus = Literal["uploaded", "parsing", "parsed", "failed"]
DocumentChunkStatus = Literal["pending", "chunking", "chunked", "failed"]
DocumentEmbeddingStatus = Literal[
    "pending",
    "embedding",
    "ready",
    "failed",
]
FileName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
FilePath = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=4096),
]
Sha256Hex = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9a-fA-F]{64}$"),
]
OptionalHeading = Annotated[
    str,
    StringConstraints(max_length=512),
]
OptionalVectorId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class DocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    knowledge_base_id: UUID
    filename: FileName
    original_filename: FileName
    file_type: DocumentFileType
    file_path: FilePath
    file_size: int = Field(ge=0)
    file_hash: Sha256Hex
    parse_status: DocumentParseStatus = "uploaded"
    chunk_status: DocumentChunkStatus = "pending"
    embedding_status: DocumentEmbeddingStatus = "pending"
    error_message: str | None = None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="metadata_json",
        serialization_alias="metadata",
    )


class DocumentRead(DocumentCreate):
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
    )

    id: UUID
    created_at: datetime
    updated_at: datetime


class DocumentChunkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    document_id: UUID
    knowledge_base_id: UUID
    chunk_index: int = Field(ge=0)
    content: str
    token_count: int = Field(ge=0)
    char_count: int = Field(ge=0)
    heading: OptionalHeading | None = None
    page_number: int | None = Field(default=None, gt=0)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="metadata_json",
        serialization_alias="metadata",
    )
    vector_id: OptionalVectorId | None = None

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value


class DocumentChunkRead(DocumentChunkCreate):
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
    )

    id: UUID
    created_at: datetime
