import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from pydantic import ValidationError

from app.providers.llm.base import (
    BaseLLMProvider,
    ChatChunk,
    ChatRequest,
    LLMResponse,
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderConfigurationError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderServerError,
    ProviderTimeoutError,
    ProviderUnknownError,
    TokenUsage,
)


class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        default_model: str,
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url.strip():
            raise ProviderConfigurationError(
                "OPENAI_COMPATIBLE_BASE_URL is required"
            )
        if not api_key.strip():
            raise ProviderConfigurationError(
                "OPENAI_COMPATIBLE_API_KEY is required"
            )
        if not default_model.strip():
            raise ProviderConfigurationError(
                "OPENAI_COMPATIBLE_MODEL is required"
            )
        if timeout_seconds <= 0:
            raise ProviderConfigurationError(
                "OPENAI_COMPATIBLE_TIMEOUT_SECONDS must be greater than 0"
            )

        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._api_key = api_key
        self._default_model = default_model
        self._timeout_seconds = timeout_seconds
        self._client = client

    @asynccontextmanager
    async def _client_context(self) -> AsyncIterator[httpx.AsyncClient]:
        if self._client is not None:
            yield self._client
            return

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            yield client

    def _build_payload(
        self,
        request: ChatRequest,
        *,
        stream: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model or self._default_model,
            "messages": [message.model_dump() for message in request.messages],
            "temperature": request.temperature,
            "stream": stream,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        return payload

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def chat(self, request: ChatRequest) -> LLMResponse:
        try:
            async with self._client_context() as client:
                response = await client.post(
                    self._endpoint,
                    headers=self._headers,
                    json=self._build_payload(request, stream=False),
                    timeout=self._timeout_seconds,
                )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Provider request timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderUnknownError("Provider request failed") from exc

        self._raise_for_status(response)

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderResponseError(
                "Provider response format is invalid: expected JSON"
            ) from exc

        return self._parse_response(payload)

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatChunk]:
        try:
            async with self._client_context() as client:
                async with client.stream(
                    "POST",
                    self._endpoint,
                    headers=self._headers,
                    json=self._build_payload(request, stream=True),
                    timeout=self._timeout_seconds,
                ) as response:
                    if not response.is_success:
                        await response.aread()
                        self._raise_for_status(response)

                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue

                        data = line.removeprefix("data:").strip()
                        if data == "[DONE]":
                            return
                        if not data:
                            continue

                        try:
                            payload = json.loads(data)
                        except json.JSONDecodeError as exc:
                            raise ProviderResponseError(
                                "Provider stream response format is invalid"
                            ) from exc
                        yield self._parse_chunk(payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Provider request timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderUnknownError("Provider request failed") from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_success:
            return

        raise self._request_error_for_status(response.status_code)

    @staticmethod
    def _request_error_for_status(status_code: int) -> ProviderRequestError:
        if status_code in {401, 403}:
            return ProviderAuthError(
                "Provider authentication failed",
                status_code=status_code,
            )
        if status_code == 429:
            return ProviderRateLimitError(
                "Provider rate limit exceeded",
                status_code=status_code,
            )
        if status_code in {408, 504}:
            return ProviderTimeoutError(
                "Provider request timed out",
                status_code=status_code,
            )
        if 400 <= status_code < 500:
            return ProviderBadRequestError(
                "Provider rejected the request",
                status_code=status_code,
            )
        if 500 <= status_code < 600:
            return ProviderServerError(
                "Provider server error",
                status_code=status_code,
            )
        return ProviderUnknownError(
            "Provider request failed",
            status_code=status_code,
        )

    def _parse_response(self, payload: Any) -> LLMResponse:
        try:
            choice = payload["choices"][0]
            message = choice["message"]
            content = message["content"]
            if not isinstance(content, str):
                raise TypeError("content must be a string")

            model = payload.get("model") or self._default_model
            usage = self._parse_usage(payload.get("usage"))
            return LLMResponse(
                id=payload.get("id"),
                model=model,
                content=content,
                finish_reason=choice.get("finish_reason"),
                usage=usage,
            )
        except (KeyError, IndexError, TypeError, ValidationError) as exc:
            raise ProviderResponseError(
                "Provider response format is invalid"
            ) from exc

    @staticmethod
    def _parse_usage(payload: Any) -> TokenUsage | None:
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise TypeError("usage must be an object")
        return TokenUsage(
            input_tokens=payload["prompt_tokens"],
            output_tokens=payload["completion_tokens"],
            total_tokens=payload["total_tokens"],
        )

    def _parse_chunk(self, payload: Any) -> ChatChunk:
        try:
            choice = payload["choices"][0]
            delta = choice["delta"]
            content = delta.get("content") or ""
            if not isinstance(content, str):
                raise TypeError("content must be a string")

            return ChatChunk(
                id=payload.get("id"),
                model=payload.get("model"),
                content=content,
                finish_reason=choice.get("finish_reason"),
                usage=self._parse_usage(payload.get("usage")),
            )
        except (KeyError, IndexError, TypeError, ValidationError) as exc:
            raise ProviderResponseError(
                "Provider stream response format is invalid"
            ) from exc
