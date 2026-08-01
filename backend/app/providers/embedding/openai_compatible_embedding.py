from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from math import isfinite
from typing import Any, Literal, Self

import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

from app.providers.embedding.base import (
    EmbeddingDimensionMismatchError,
    EmbeddingModelName,
    EmbeddingProvider,
    EmbeddingProviderAuthError,
    EmbeddingProviderBadRequestError,
    EmbeddingProviderConfigurationError,
    EmbeddingProviderInputError,
    EmbeddingProviderRateLimitError,
    EmbeddingProviderRequestError,
    EmbeddingProviderResponseError,
    EmbeddingProviderServerError,
    EmbeddingProviderTimeoutError,
    EmbeddingProviderUnknownError,
    EmbeddingResult,
    EmbeddingUsage,
)


class _EmbeddingDataItem(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    object: Literal["embedding"]
    embedding: tuple[FiniteFloat, ...] = Field(min_length=1)
    index: StrictInt = Field(ge=0)

    @field_validator("embedding", mode="before")
    @classmethod
    def reject_coerced_vector_values(cls, value: object) -> object:
        if not isinstance(value, (list, tuple)):
            return value
        if any(
            isinstance(component, bool)
            or not isinstance(component, (int, float))
            for component in value
        ):
            raise ValueError("embedding vector values must be numbers")
        return value


class _EmbeddingUsagePayload(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    prompt_tokens: StrictInt = Field(ge=0)
    total_tokens: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def validate_total_tokens(self) -> Self:
        if self.total_tokens < self.prompt_tokens:
            raise ValueError(
                "total tokens must not be smaller than prompt tokens"
            )
        return self


class _EmbeddingResponsePayload(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    object: Literal["list"]
    data: tuple[_EmbeddingDataItem, ...] = Field(min_length=1)
    model: EmbeddingModelName
    usage: _EmbeddingUsagePayload


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        default_model: str,
        expected_dimension: int,
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
        name: str = "openai_compatible",
    ) -> None:
        normalized_base_url = self._require_text(
            base_url,
            variable_name="OPENAI_COMPATIBLE_EMBEDDING_BASE_URL",
        )
        normalized_api_key = self._require_text(
            api_key,
            variable_name="OPENAI_COMPATIBLE_EMBEDDING_API_KEY",
        )
        normalized_model = self._require_text(
            default_model,
            variable_name="OPENAI_COMPATIBLE_EMBEDDING_MODEL",
        )
        if (
            isinstance(expected_dimension, bool)
            or not isinstance(expected_dimension, int)
            or expected_dimension <= 0
            or expected_dimension > 65_536
        ):
            raise EmbeddingProviderConfigurationError(
                "OPENAI_COMPATIBLE_EMBEDDING_DIMENSION must be between 1 and 65536"
            )
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not isfinite(timeout_seconds)
            or timeout_seconds <= 0
            or timeout_seconds > 3600
        ):
            raise EmbeddingProviderConfigurationError(
                "OPENAI_COMPATIBLE_EMBEDDING_TIMEOUT_SECONDS must be between 0 and 3600"
            )

        super().__init__(name=name)
        self._endpoint = f"{normalized_base_url.rstrip('/')}/embeddings"
        self._api_key = normalized_api_key
        self._default_model = normalized_model
        self._expected_dimension = expected_dimension
        self._timeout_seconds = float(timeout_seconds)
        self._client = client

    @staticmethod
    def _require_text(value: object, *, variable_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise EmbeddingProviderConfigurationError(
                f"{variable_name} is required"
            )
        return value.strip()

    @asynccontextmanager
    async def _client_context(self) -> AsyncIterator[httpx.AsyncClient]:
        if self._client is not None:
            yield self._client
            return

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            yield client

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        normalized_texts = self._validate_texts(texts)
        return await self._embed(normalized_texts)

    async def embed_query(self, query: str) -> EmbeddingResult:
        if not isinstance(query, str) or not query.strip():
            raise EmbeddingProviderInputError(
                "Embedding query must not be blank"
            )
        return await self._embed([query])

    @staticmethod
    def _validate_texts(texts: object) -> list[str]:
        if not isinstance(texts, list) or not texts:
            raise EmbeddingProviderInputError(
                "Embedding texts must not be empty"
            )
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise EmbeddingProviderInputError(
                "Embedding texts must not contain blank items"
            )
        return texts

    async def _embed(self, texts: list[str]) -> EmbeddingResult:
        payload = {
            "model": self._default_model,
            "input": texts,
            "dimensions": self._expected_dimension,
            "encoding_format": "float",
        }
        try:
            async with self._client_context() as client:
                response = await client.post(
                    self._endpoint,
                    headers=self._headers,
                    json=payload,
                    timeout=self._timeout_seconds,
                )
        except httpx.TimeoutException as exc:
            raise EmbeddingProviderTimeoutError(
                "Embedding Provider request timed out"
            ) from exc
        except httpx.RequestError as exc:
            raise EmbeddingProviderUnknownError(
                "Embedding Provider request failed"
            ) from exc

        self._raise_for_status(response)
        try:
            response_payload = response.json()
        except ValueError:
            raise EmbeddingProviderResponseError(
                "Embedding Provider response format is invalid: expected JSON"
            ) from None
        return self._parse_response(response_payload, expected_count=len(texts))

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.is_success:
            return
        raise OpenAICompatibleEmbeddingProvider._request_error_for_status(
            response.status_code
        )

    @staticmethod
    def _request_error_for_status(
        status_code: int,
    ) -> EmbeddingProviderRequestError:
        if status_code in {401, 403}:
            return EmbeddingProviderAuthError(
                "Embedding Provider authentication failed",
                status_code=status_code,
            )
        if status_code == 429:
            return EmbeddingProviderRateLimitError(
                "Embedding Provider rate limit exceeded",
                status_code=status_code,
            )
        if status_code in {408, 504}:
            return EmbeddingProviderTimeoutError(
                "Embedding Provider request timed out",
                status_code=status_code,
            )
        if 400 <= status_code < 500:
            return EmbeddingProviderBadRequestError(
                "Embedding Provider rejected the request",
                status_code=status_code,
            )
        if 500 <= status_code < 600:
            return EmbeddingProviderServerError(
                "Embedding Provider server error",
                status_code=status_code,
            )
        return EmbeddingProviderUnknownError(
            "Embedding Provider request failed",
            status_code=status_code,
        )

    def _parse_response(
        self,
        payload: Any,
        *,
        expected_count: int,
    ) -> EmbeddingResult:
        try:
            response = _EmbeddingResponsePayload.model_validate(payload)
            if len(response.data) != expected_count:
                raise ValueError("embedding result count does not match input")

            vectors_by_index: dict[int, tuple[float, ...]] = {}
            for item in response.data:
                if item.index >= expected_count or item.index in vectors_by_index:
                    raise ValueError("embedding result index is invalid")
                vectors_by_index[item.index] = item.embedding
            if set(vectors_by_index) != set(range(expected_count)):
                raise ValueError("embedding result indexes are incomplete")

            result = EmbeddingResult(
                model=response.model,
                vectors=tuple(
                    vectors_by_index[index]
                    for index in range(expected_count)
                ),
                usage=EmbeddingUsage(
                    input_tokens=response.usage.prompt_tokens,
                    total_tokens=response.usage.total_tokens,
                ),
            )
        except (TypeError, ValueError, ValidationError):
            raise EmbeddingProviderResponseError(
                "Embedding Provider response format is invalid"
            ) from None

        if result.dimension != self._expected_dimension:
            raise EmbeddingDimensionMismatchError(
                "Embedding dimension mismatch: "
                f"expected {self._expected_dimension}, received {result.dimension}"
            )
        return result
