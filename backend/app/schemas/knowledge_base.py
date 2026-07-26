from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints


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


class KnowledgeBaseRead(KnowledgeBaseCreate):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
