from abc import ABC, abstractmethod
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)


EmbeddingModelName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
EmbeddingVector = tuple[FiniteFloat, ...]


class EmbeddingUsage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    input_tokens: StrictInt = Field(ge=0)
    total_tokens: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def validate_total_tokens(self) -> Self:
        if self.total_tokens < self.input_tokens:
            raise ValueError("total tokens must not be smaller than input tokens")
        return self


class EmbeddingResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model: EmbeddingModelName
    vectors: tuple[EmbeddingVector, ...] = Field(min_length=1)
    usage: EmbeddingUsage

    @field_validator("vectors", mode="before")
    @classmethod
    def reject_coerced_vector_values(cls, value: object) -> object:
        if not isinstance(value, (list, tuple)):
            return value
        for vector in value:
            if not isinstance(vector, (list, tuple)):
                continue
            if any(
                isinstance(component, bool)
                or not isinstance(component, (int, float))
                for component in vector
            ):
                raise ValueError("embedding vector values must be numbers")
        return value

    @model_validator(mode="after")
    def validate_vector_dimensions(self) -> Self:
        dimension = len(self.vectors[0])
        if dimension == 0:
            raise ValueError("embedding vectors must not be empty")
        if any(len(vector) != dimension for vector in self.vectors[1:]):
            raise ValueError("embedding vectors must have the same dimension")
        return self

    @property
    def dimension(self) -> int:
        return len(self.vectors[0])


class EmbeddingProviderError(RuntimeError):
    """Embedding Provider 边界的基础异常。"""


class EmbeddingProvider(ABC):
    def __init__(self, *, name: str) -> None:
        if not isinstance(name, str):
            raise TypeError("name must be a string")
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("name must not be blank")
        if len(normalized_name) > 100:
            raise ValueError("name must be at most 100 characters")
        self._name = normalized_name

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        raise NotImplementedError

    @abstractmethod
    async def embed_query(self, query: str) -> EmbeddingResult:
        raise NotImplementedError
