from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    model_validator,
)


KnowledgeBaseName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
OptionalProviderName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
OptionalModelName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


class KnowledgeBaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: KnowledgeBaseName
    description: str | None = None
    embedding_provider: OptionalProviderName | None = None
    embedding_model: OptionalModelName | None = None
    vector_store: OptionalProviderName = "qdrant"
    vector_collection_name: OptionalModelName | None = None


class KnowledgeBaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: KnowledgeBaseName | None = None
    description: str | None = None
    embedding_provider: OptionalProviderName | None = None
    embedding_model: OptionalModelName | None = None
    vector_store: OptionalProviderName | None = None
    vector_collection_name: OptionalModelName | None = None

    @model_validator(mode="after")
    def validate_partial_update(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("at least one field must be supplied")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name must not be null")
        if (
            "vector_store" in self.model_fields_set
            and self.vector_store is None
        ):
            raise ValueError("vector_store must not be null")
        return self


class KnowledgeBaseRead(KnowledgeBaseCreate):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
