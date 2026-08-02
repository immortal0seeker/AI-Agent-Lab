from abc import ABC, abstractmethod
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictBool,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.rag.vectorstores.payload import (
    ChunkVectorPayload,
    EmbeddingModelName,
    EmbeddingProviderName,
)


CollectionName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9._-]+$",
    ),
]
Vector = tuple[FiniteFloat, ...]


class VectorCollectionStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    collection_name: CollectionName
    dimension: StrictInt = Field(gt=0, le=65_536)
    distance: Literal["cosine"]
    created: StrictBool


class VectorPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    vector: Vector = Field(min_length=1)
    payload: ChunkVectorPayload

    @field_validator("vector", mode="before")
    @classmethod
    def reject_coerced_vector_values(cls, value: object) -> object:
        _validate_vector_input(value)
        return value

    @model_validator(mode="after")
    def validate_point_id(self) -> Self:
        if self.id != self.payload.chunk_id:
            raise ValueError("point id must match chunk id")
        return self


class VectorSearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    knowledge_base_id: UUID
    embedding_provider: EmbeddingProviderName
    embedding_model: EmbeddingModelName
    vector: Vector = Field(min_length=1)
    limit: StrictInt = Field(default=5, ge=1, le=100)
    score_threshold: FiniteFloat | None = None

    @field_validator("vector", mode="before")
    @classmethod
    def reject_coerced_vector_values(cls, value: object) -> object:
        _validate_vector_input(value)
        return value

    @field_validator("score_threshold", mode="before")
    @classmethod
    def reject_coerced_score_threshold(cls, value: object) -> object:
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float))
        ):
            raise ValueError("score threshold must be a number")
        return value


class VectorSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    point_id: UUID
    score: FiniteFloat
    payload: ChunkVectorPayload

    @field_validator("score", mode="before")
    @classmethod
    def reject_coerced_score(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("score must be a number")
        return value

    @model_validator(mode="after")
    def validate_point_id(self) -> Self:
        if self.point_id != self.payload.chunk_id:
            raise ValueError("point id must match chunk id")
        return self


class VectorStoreError(RuntimeError):
    """Vector Store 边界的基础异常。"""


class VectorStoreConfigurationError(VectorStoreError):
    """Vector Store 配置缺失、无效或与已有 collection 不一致。"""


class VectorStoreDimensionMismatchError(VectorStoreConfigurationError):
    """向量维度与 Vector Store collection 不一致。"""


class VectorStoreInputError(VectorStoreError):
    """Vector Store 的本地输入无效。"""


class VectorStoreOperationError(VectorStoreError):
    """Vector Store 远端操作失败。"""


class VectorStoreResponseError(VectorStoreError):
    """Vector Store 返回了无法安全解析的响应。"""


class VectorStore(ABC):
    @property
    @abstractmethod
    def collection_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def ensure_collection(self) -> VectorCollectionStatus:
        raise NotImplementedError

    @abstractmethod
    async def upsert(self, points: list[VectorPoint]) -> tuple[UUID, ...]:
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        query: VectorSearchQuery,
    ) -> tuple[VectorSearchResult, ...]:
        raise NotImplementedError

    @abstractmethod
    async def delete_document_vectors(
        self,
        *,
        knowledge_base_id: UUID,
        document_id: UUID,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError


def _validate_vector_input(value: object) -> None:
    if not isinstance(value, (list, tuple)):
        return
    if any(
        isinstance(component, bool)
        or not isinstance(component, (int, float))
        for component in value
    ):
        raise ValueError("vector values must be numbers")
