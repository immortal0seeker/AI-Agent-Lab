# Plan 1 M4-S1～S3 Usage、错误与日志 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Repository policy keeps execution inline and reserves the final commit for the user.

**Goal:** 为现有非流式与 SSE Chat 增加成功调用的 token/cost/latency 持久化、安全的统一错误契约，以及带服务端 request ID 的基础日志。

**Architecture:** Service 层使用独立 helper 计算 usage/cost/latency；Provider adapter 把上游失败分类为安全异常；共享 API 错误映射同时服务普通 HTTP 与 SSE；纯 ASGI 中间件在整个响应生命周期内维护 request ID 并记录请求日志。实现不新增依赖，不创建 Trace 或后续 Plan 模块。

**Tech Stack:** Python 3.11、FastAPI 0.138、Pydantic 2、SQLAlchemy 2、httpx 0.28、SQLite、pytest、React/TypeScript/Vitest、Python 标准库 `logging`。

## Global Constraints

- 仅实现 `P1-M4-S1～P1-M4-S3`；不得实现 `P1-M4-S4` 及后续 Step。
- 不实现 Tool Calling、RAG、Memory、MCP、Voice、Vision、Desktop、Trace、重试或 Provider fallback。
- SQLite 是默认且长期支持的主数据库；本批不新增 migration，因为统计列已经存在。
- 不读取真实 `.env`、API key 或其他 secret；所有测试只用 mock Provider 和假凭据。
- 不调用真实付费模型服务。
- 必要代码注释使用中文，只解释非显而易见的边界。
- 不新增第三方依赖；日志使用 Python 标准库。
- API route 保持薄层；统计和成本计算不得放在 route。
- Registry 任一价格为 `null` 时 cost 必须保持 `null`。
- 普通 HTTP 与 SSE 使用同构结构化错误对象。
- request ID 始终由服务端生成，忽略客户端传入值。
- 不记录请求/响应 body、完整消息、Authorization、API key、Provider 原始正文、SQL 参数或数据库路径。
- Provider 失败、空流与取消继续回滚整个回合，不持久化失败 `LLMCall`。
- Codex 不执行 `git commit`；完成后只提供建议 commit message。

## File Map

### 新建

- `backend/app/services/llm_usage.py`：纯 usage/cost 计算与可测试的 Provider latency timer。
- `backend/tests/test_llm_usage.py`：成本精度、空值和 timer 单元测试。
- `backend/app/schemas/error.py`：统一 API/SSE 错误 schema。
- `backend/app/core/request_context.py`：request ID ContextVar 与纯 ASGI 中间件。
- `backend/app/core/logging.py`：安全 key=value formatter、日志初始化和安全堆栈位置提取。
- `backend/tests/test_request_logging.py`：request ID、中间件和日志安全测试。

### 修改

- `backend/app/providers/llm/base.py`：Provider 请求错误分类。
- `backend/app/providers/llm/openai_compatible.py`：HTTP/timeout/transport 分类且不传播上游正文。
- `backend/app/providers/llm/__init__.py`：如现有导出方式需要，同步新异常导出。
- `backend/app/services/chat_service.py`：非流式与流式计时、统计持久化和安全模型调用日志。
- `backend/app/api/errors.py`：共享错误映射、统一 exception handlers 与安全错误日志。
- `backend/app/api/v1/chat.py`：SSE 使用共享错误映射和结构化 payload。
- `backend/app/schemas/chat.py`：SSE error schema 改为统一 envelope，或直接复用 `ErrorResponse`。
- `backend/app/schemas/__init__.py`：导出错误 schema。
- `backend/app/main.py`：初始化日志并注册 request context middleware。
- `backend/tests/test_chat_service.py`：成功指标持久化、空价格及回滚断言。
- `backend/tests/test_openai_compatible_provider.py`：Provider 错误分类与脱敏。
- `backend/tests/test_chat_api.py`：统一 HTTP/SSE 错误、数据库错误和 request ID。
- `frontend/src/api/client.ts`：共享结构化错误消息解析器。
- `frontend/src/api/chat.ts`：HTTP/SSE 使用共享解析器。
- `frontend/src/api/client.test.ts`：新错误 envelope 与旧 `detail` 兼容。
- `frontend/src/api/chat.test.ts`：结构化 SSE/HTTP 错误与旧 `message` 兼容。
- `README.md`、`README_CN.md`：最小同步已完成范围和下一批范围。
- `docs/00-project-overview.md`：最小同步当前阶段。
- `docs/01-architecture.md`：记录统计、错误和 request ID 数据流。
- `docs/03-llm-provider.md`：记录 Provider 分类、usage/cost 与安全边界。
- `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`：仅把 Batch 10 / S1～S3 标记为完成。

---

### Task 1: 建立 Usage、Cost 与 Latency 纯逻辑

**Files:**

- Create: `backend/app/services/llm_usage.py`
- Create: `backend/tests/test_llm_usage.py`

**Interfaces:**

- Consumes: `TokenUsage`、`ModelInfo.input_price_per_1m`、`ModelInfo.output_price_per_1m`
- Produces: `LLMCallMetrics`、`build_llm_call_metrics(...)`、`ProviderLatencyTimer`

- [ ] **Step 1: 写 cost 与 timer 的失败测试**

创建 `backend/tests/test_llm_usage.py`，覆盖下面的具体行为：

```python
from decimal import Decimal

from app.providers.llm.base import TokenUsage
from app.providers.llm.registry import ModelInfo
from app.services.llm_usage import ProviderLatencyTimer, build_llm_call_metrics


def model_info(input_price: Decimal | None, output_price: Decimal | None) -> ModelInfo:
    return ModelInfo(
        provider="openai_compatible",
        model="example-model",
        display_name="Example Model",
        input_price_per_1m=input_price,
        output_price_per_1m=output_price,
    )


def test_build_metrics_calculates_decimal_cost_and_tokens() -> None:
    metrics = build_llm_call_metrics(
        usage=TokenUsage(input_tokens=1_000, output_tokens=500, total_tokens=1_500),
        model_info=model_info(Decimal("0.50"), Decimal("1.50")),
        latency_ms=123,
    )

    assert metrics.input_tokens == 1_000
    assert metrics.output_tokens == 500
    assert metrics.total_tokens == 1_500
    assert metrics.estimated_cost == Decimal("0.00125000")
    assert metrics.latency_ms == 123


def test_build_metrics_keeps_cost_null_when_usage_or_price_is_unknown() -> None:
    no_usage = build_llm_call_metrics(
        usage=None,
        model_info=model_info(Decimal("0.50"), Decimal("1.50")),
        latency_ms=1,
    )
    missing_output_price = build_llm_call_metrics(
        usage=TokenUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        model_info=model_info(Decimal("0.50"), None),
        latency_ms=1,
    )

    assert no_usage.input_tokens is None
    assert no_usage.estimated_cost is None
    assert missing_output_price.estimated_cost is None


def test_build_metrics_treats_zero_price_as_known() -> None:
    metrics = build_llm_call_metrics(
        usage=TokenUsage(input_tokens=10, output_tokens=20, total_tokens=30),
        model_info=model_info(Decimal("0"), Decimal("0")),
        latency_ms=0,
    )

    assert metrics.estimated_cost == Decimal("0E-8")


def test_build_metrics_rounds_to_database_scale() -> None:
    metrics = build_llm_call_metrics(
        usage=TokenUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        model_info=model_info(Decimal("0.004"), Decimal("0.004")),
        latency_ms=0,
    )

    assert metrics.estimated_cost == Decimal("1E-8")


def test_latency_timer_accumulates_only_measured_sections() -> None:
    ticks = iter([10.0, 10.010, 20.0, 20.015])
    timer = ProviderLatencyTimer(clock=lambda: next(ticks))

    with timer.measure():
        pass
    with timer.measure():
        pass

    assert timer.latency_ms == 25
```

- [ ] **Step 2: 运行测试并确认按预期失败**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_llm_usage.py -q
```

Expected: collection fails because `app.services.llm_usage` does not exist.

- [ ] **Step 3: 实现最小纯逻辑**

创建 `backend/app/services/llm_usage.py`：

```python
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from time import perf_counter

from app.providers.llm.base import TokenUsage
from app.providers.llm.registry import ModelInfo


COST_QUANTUM = Decimal("0.00000001")
TOKENS_PER_MILLION = Decimal("1000000")


@dataclass(frozen=True)
class LLMCallMetrics:
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost: Decimal | None
    latency_ms: int


class ProviderLatencyTimer:
    def __init__(self, *, clock: Callable[[], float] = perf_counter) -> None:
        self._clock = clock
        self._elapsed_seconds = 0.0

    @contextmanager
    def measure(self) -> Iterator[None]:
        started_at = self._clock()
        try:
            yield
        finally:
            self._elapsed_seconds += max(0.0, self._clock() - started_at)

    @property
    def latency_ms(self) -> int:
        return max(0, round(self._elapsed_seconds * 1000))


def build_llm_call_metrics(
    *,
    usage: TokenUsage | None,
    model_info: ModelInfo,
    latency_ms: int,
) -> LLMCallMetrics:
    estimated_cost: Decimal | None = None
    if (
        usage is not None
        and model_info.input_price_per_1m is not None
        and model_info.output_price_per_1m is not None
    ):
        raw_cost = (
            Decimal(usage.input_tokens) * model_info.input_price_per_1m
            + Decimal(usage.output_tokens) * model_info.output_price_per_1m
        ) / TOKENS_PER_MILLION
        estimated_cost = raw_cost.quantize(COST_QUANTUM, rounding=ROUND_HALF_UP)

    return LLMCallMetrics(
        input_tokens=usage.input_tokens if usage is not None else None,
        output_tokens=usage.output_tokens if usage is not None else None,
        total_tokens=usage.total_tokens if usage is not None else None,
        estimated_cost=estimated_cost,
        latency_ms=max(0, latency_ms),
    )
```

- [ ] **Step 4: 运行 pure logic 测试**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_llm_usage.py -q
```

Expected: `5 passed`。

- [ ] **Step 5: Review checkpoint**

检查 helper 不依赖 FastAPI、SQLAlchemy Session 或具体 Provider adapter；不 commit。

---

### Task 2: 在非流式与流式 Chat 中持久化成功指标

**Files:**

- Modify: `backend/app/services/chat_service.py`
- Modify: `backend/tests/test_chat_service.py`
- Modify: `backend/tests/test_chat_api.py`

**Interfaces:**

- Consumes: `build_llm_call_metrics(...)`、`ProviderLatencyTimer`
- Produces: completed `LLMCall` with provider/model/input/output/total/cost/latency

- [ ] **Step 1: 先把 Registry 测试价格设为确定值并写失败断言**

在 Chat Service/API 测试的 `create_registry()` 中加入：

```python
input_price_per_1m=Decimal("0.50"),
output_price_per_1m=Decimal("1.50"),
```

为非流式成功追加：

```python
assert result.llm_call.input_tokens == 4
assert result.llm_call.output_tokens == 2
assert result.llm_call.total_tokens == 6
assert result.llm_call.estimated_cost == Decimal("0.00000500")
assert result.llm_call.latency_ms is not None
assert result.llm_call.latency_ms >= 0
```

为流式成功追加：

```python
assert completed.result.llm_call.input_tokens == 7
assert completed.result.llm_call.output_tokens == 2
assert completed.result.llm_call.total_tokens == 9
assert completed.result.llm_call.estimated_cost == Decimal("0.00000650")
assert completed.result.llm_call.latency_ms is not None
```

新增一个价格未知测试，Registry 的任一价格为 `None`，Provider 返回 usage 后断言 `estimated_cost is None`。保留现有 Provider 失败、空流和取消测试对零 `LLMCall` 的断言。

- [ ] **Step 2: 运行 Service/API 目标测试并确认失败**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_chat_service.py tests/test_chat_api.py -q
```

Expected: success assertions fail because persisted token/cost/latency fields are still `None`。

- [ ] **Step 3: 修改 `ChatService.complete()`**

把 Registry 查询结果保存在 `model_info`，使用 timer 包裹 Provider await，并把 metrics 写入 `LLMCall`：

```python
model_info = self._registry.get_model(request.provider, request.model)
if model_info is None:
    raise ChatModelNotFoundError(request.provider, request.model)

timer = ProviderLatencyTimer()
try:
    with timer.measure():
        response = await provider.chat(provider_request)
except LLMProviderError:
    self._session.rollback()
    raise

metrics = build_llm_call_metrics(
    usage=response.usage,
    model_info=model_info,
    latency_ms=timer.latency_ms,
)
llm_call = LLMCall(
    conversation_id=conversation.id,
    message_id=assistant_message.id,
    provider=request.provider,
    model=response.model,
    input_tokens=metrics.input_tokens,
    output_tokens=metrics.output_tokens,
    total_tokens=metrics.total_tokens,
    estimated_cost=metrics.estimated_cost,
    latency_ms=metrics.latency_ms,
    status="completed",
)
```

- [ ] **Step 4: 修改 `ChatService.stream_complete()`**

使用同一个 `model_info`。手动等待每个 Provider chunk，使 timer 只覆盖 `anext()`：

```python
timer = ProviderLatencyTimer()
provider_stream = provider.stream_chat(provider_request)
try:
    while True:
        try:
            with timer.measure():
                chunk = await anext(provider_stream)
        except StopAsyncIteration:
            break

        if chunk.model:
            response_model = chunk.model
        if chunk.usage is not None:
            usage = chunk.usage
        if chunk.content:
            content_parts.append(chunk.content)
            yield ChatStreamDelta(content=chunk.content)
finally:
    close_stream = getattr(provider_stream, "aclose", None)
    if close_stream is not None:
        await close_stream()
```

完整成功后用 `build_llm_call_metrics(...)` 填充 `LLMCall` 的五个统计字段；保持 commit 在 `done` 前，保持 `finally` 中未完成回滚。

- [ ] **Step 5: 运行目标测试**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_llm_usage.py tests/test_chat_service.py tests/test_chat_api.py -q
```

Expected: all selected tests pass；失败、空流、取消仍无持久化记录。

- [ ] **Step 6: Review checkpoint**

检查 route 中没有 cost/latency 业务逻辑，`LLMCall` 字段与现有 migration 一致，不新增 migration；不 commit。

---

### Task 3: 细分 Provider 错误且切断上游敏感正文

**Files:**

- Modify: `backend/app/providers/llm/base.py`
- Modify: `backend/app/providers/llm/openai_compatible.py`
- Modify: `backend/app/providers/llm/__init__.py`
- Modify: `backend/tests/test_openai_compatible_provider.py`
- Modify: `backend/tests/test_llm_provider_base.py`

**Interfaces:**

- Consumes: `httpx.Response.status_code`、`httpx.TimeoutException`、`httpx.RequestError`
- Produces: typed safe Provider exceptions with optional `status_code`

- [ ] **Step 1: 写状态分类和脱敏失败测试**

为 `test_openai_compatible_provider.py` 增加参数化测试：

```python
@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (400, ProviderBadRequestError),
        (401, ProviderAuthError),
        (403, ProviderAuthError),
        (408, ProviderTimeoutError),
        (429, ProviderRateLimitError),
        (500, ProviderServerError),
        (504, ProviderTimeoutError),
    ],
)
def test_chat_classifies_http_errors_without_upstream_text(
    status_code: int,
    expected_error: type[ProviderRequestError],
) -> None:
    async def exercise() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code,
                json={"error": {"message": "secret upstream diagnostic"}},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenAICompatibleProvider(
                base_url="https://provider.example/v1",
                api_key="test-secret-key",
                default_model="default-model",
                client=client,
            )
            await provider.chat(
                ChatRequest(messages=[ChatMessage(role="user", content="hi")])
            )

    with pytest.raises(expected_error) as exc_info:
        asyncio.run(exercise())

    assert exc_info.value.status_code == status_code
    assert "secret upstream diagnostic" not in str(exc_info.value)
    assert "test-secret-key" not in str(exc_info.value)
```

再增加 `httpx.ReadTimeout` -> `ProviderTimeoutError` 和 `httpx.ConnectError` -> `ProviderUnknownError` 测试；非流式与流式各保留至少一个错误分类用例。

- [ ] **Step 2: 运行 Provider 测试并确认失败**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_llm_provider_base.py tests/test_openai_compatible_provider.py -q
```

Expected: imports fail because typed exceptions do not exist，或现有 adapter 仍暴露 upstream message。

- [ ] **Step 3: 实现异常层次**

在 `base.py` 保留 `ProviderRequestError` 共同父类，并增加：

```python
class ProviderAuthError(ProviderRequestError):
    """Provider 拒绝了服务端凭据。"""


class ProviderRateLimitError(ProviderRequestError):
    """Provider 已触发限流。"""


class ProviderTimeoutError(ProviderRequestError):
    """Provider 请求超时。"""


class ProviderBadRequestError(ProviderRequestError):
    """Provider 拒绝了请求。"""


class ProviderServerError(ProviderRequestError):
    """Provider 服务端失败。"""


class ProviderUnknownError(ProviderRequestError):
    """Provider 请求出现未分类故障。"""
```

`ProviderRequestError` 继续接收安全 message 和 `status_code`，确保已有 mock Provider 仍可构造该基类。

- [ ] **Step 4: 实现 adapter 分类**

新增安全 `_request_error_for_status(status_code)`，不要读取/拼接响应正文：

```python
def _request_error_for_status(status_code: int) -> ProviderRequestError:
    if status_code in {401, 403}:
        return ProviderAuthError("Provider authentication failed", status_code=status_code)
    if status_code == 429:
        return ProviderRateLimitError("Provider rate limit exceeded", status_code=status_code)
    if status_code in {408, 504}:
        return ProviderTimeoutError("Provider request timed out", status_code=status_code)
    if 400 <= status_code < 500:
        return ProviderBadRequestError("Provider rejected the request", status_code=status_code)
    if 500 <= status_code < 600:
        return ProviderServerError("Provider server error", status_code=status_code)
    return ProviderUnknownError("Provider request failed", status_code=status_code)
```

在 `chat()` 与 `stream_chat()` 中先捕获 `httpx.TimeoutException`，再捕获其他 `httpx.RequestError`：

```python
except httpx.TimeoutException as exc:
    raise ProviderTimeoutError("Provider request timed out") from exc
except httpx.RequestError as exc:
    raise ProviderUnknownError("Provider request failed") from exc
```

- [ ] **Step 5: 运行 Provider 测试**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_llm_provider_base.py tests/test_openai_compatible_provider.py tests/test_llm_provider_factory.py -q
```

Expected: all selected Provider tests pass，断言中不存在 upstream sensitive text 或 fake key。

- [ ] **Step 6: Review checkpoint**

确认异常字符串只含固定安全文本，分类没有重试/fallback；不 commit。

---

### Task 4: 建立 request ID、中间件、统一 HTTP/SSE 错误契约

**Files:**

- Create: `backend/app/schemas/error.py`
- Create: `backend/app/core/request_context.py`
- Create: `backend/app/core/logging.py`
- Create: `backend/tests/test_request_logging.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/schemas/chat.py`
- Modify: `backend/app/api/errors.py`
- Modify: `backend/app/api/v1/chat.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_chat_api.py`

**Interfaces:**

- Produces: `ErrorDetail`、`ErrorResponse`、`ErrorSpec`、`error_spec_for_exception(exc)`、`error_response_for_exception(exc)`、`get_request_id()`、`RequestContextMiddleware`
- Consumes: typed Provider errors、Service errors、`RequestValidationError`、`HTTPException`、`SQLAlchemyError`

- [ ] **Step 1: 写统一错误和 request ID 失败测试**

在 `test_chat_api.py` 把旧 `{"detail": ...}` 断言升级为：

```python
body = response.json()
assert body["error"]["code"] == "model_not_found"
assert body["error"]["message"] == "The requested model is not available"
assert body["error"]["request_id"] == response.headers["x-request-id"]
```

增加这些测试：

```python
def test_server_generates_request_id_and_ignores_client_value(api_context: Any) -> None:
    client, _, _, _ = api_context

    response = client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "client-controlled"},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "client-controlled"
    UUID(response.headers["x-request-id"])


def test_validation_error_uses_unified_envelope(api_context: Any) -> None:
    client, _, _, _ = api_context

    response = client.post(
        "/api/v1/chat/completions",
        json={"provider": "openai_compatible", "model": "example-model", "content": "   "},
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "Request validation failed",
            "request_id": response.headers["x-request-id"],
        }
    }
```

通过 dependency override 模拟 `ProviderConfigurationError`；通过抛出 `SQLAlchemyError("simulated database failure")` 的 session dependency 模拟数据库失败，并断言响应中不含异常文本。把 SSE failure 断言升级为 `{"error": {...}}`，并验证事件 request ID 与响应头一致。

使用下面的具体 override 形态，避免读取任何本地 Provider 配置：

```python
def raise_provider_configuration_error() -> Mapping[str, BaseLLMProvider]:
    raise ProviderConfigurationError("fake local key must not be returned")


async def raise_database_error() -> AsyncIterator[Session]:
    raise SQLAlchemyError("simulated database failure with private detail")
    if False:
        yield Session()
```

对应测试使用 `app.dependency_overrides` 和 `TestClient(app, raise_server_exceptions=False)`，并在 `finally` 中清空 overrides。断言响应 code 分别为 `provider_unavailable` 和 `database_error`，且两段模拟敏感文本都不在 `response.text`。

- [ ] **Step 2: 运行 API 测试并确认失败**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_chat_api.py -q
```

Expected: headers/structured envelope assertions fail because middleware/schema/handlers do not exist。

- [ ] **Step 3: 创建错误 schema**

`backend/app/schemas/error.py`：

```python
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
```

让 `ChatStreamErrorResponse` 被 `ErrorResponse` 替代，或改为包含同一个 `ErrorDetail`；不得保留另一套 `message`-only 新契约。

- [ ] **Step 4: 创建安全日志基础**

`backend/app/core/logging.py` 提供：

```python
import logging
import traceback
from pathlib import Path

from app.core.request_context import get_request_id


STANDARD_RECORD_KEYS = set(logging.makeLogRecord({}).__dict__)
_base_record_factory = logging.getLogRecordFactory()


def _request_record_factory(*args: object, **kwargs: object) -> logging.LogRecord:
    record = _base_record_factory(*args, **kwargs)
    record.request_id = get_request_id()
    return record


class KeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields: dict[str, object] = {
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": record.request_id,
        }
        for key, value in record.__dict__.items():
            if key not in STANDARD_RECORD_KEYS and key not in {"message", "asctime"}:
                fields[key] = value
        return " ".join(f"{key}={value!s}" for key, value in fields.items())


def configure_logging() -> None:
    if logging.getLogRecordFactory() is not _request_record_factory:
        logging.setLogRecordFactory(_request_record_factory)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(handler.formatter, KeyValueFormatter) for handler in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(KeyValueFormatter())
        root.addHandler(handler)


def safe_stack_locations(exc: BaseException) -> str:
    frames = traceback.extract_tb(exc.__traceback__)[-8:]
    return "<-".join(
        f"{Path(frame.filename).name}:{frame.name}:{frame.lineno}"
        for frame in frames
    )
```

这里不格式化异常字符串，不读取 locals。

- [ ] **Step 5: 创建纯 ASGI request context 中间件**

`backend/app/core/request_context.py` 使用 ContextVar 和 `MutableHeaders`：

```python
import logging
from contextvars import ContextVar, Token
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


_request_id: ContextVar[str] = ContextVar("request_id", default="-")
logger = logging.getLogger("app.request")


def get_request_id() -> str:
    return _request_id.get()


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request_id = str(uuid4())
        token: Token[str] = _request_id.set(request_id)
        started_at = perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message).append("X-Request-ID", request_id)
            await send(message)

        try:
            await self._app(scope, receive, send_with_request_id)
        finally:
            logger.info(
                "request_completed",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status_code,
                    "duration_ms": max(0, round((perf_counter() - started_at) * 1000)),
                },
            )
            _request_id.reset(token)
```

- [ ] **Step 6: 实现共享错误映射与 handlers**

在 `api/errors.py` 定义不可变 `ErrorSpec(status_code, code, message)`，按下面的完整映射对每一种异常显式 `isinstance` 判断，子类必须排在共同父类前：

| Exception | status | code | message |
|---|---:|---|---|
| `RequestValidationError` | 422 | `validation_error` | `Request validation failed` |
| `ConversationNotFoundError` | 404 | `conversation_not_found` | `Conversation not found` |
| `ChatModelNotFoundError` | 400 | `model_not_found` | `The requested model is not available` |
| `ChatProviderUnavailableError` | 503 | `provider_unavailable` | `The requested provider is unavailable` |
| `ProviderConfigurationError` | 503 | `provider_unavailable` | `The model provider is not configured` |
| `ProviderAuthError` | 502 | `provider_auth_error` | `The model provider rejected its credentials` |
| `ProviderRateLimitError` | 429 | `provider_rate_limit` | `The model provider rate limit was exceeded` |
| `ProviderTimeoutError` | 504 | `provider_timeout` | `The model provider timed out` |
| `ProviderBadRequestError` | 502 | `provider_bad_request` | `The model provider rejected the request` |
| `ProviderServerError` | 502 | `provider_server_error` | `The model provider is unavailable` |
| `ProviderResponseError` | 502 | `provider_response_error` | `The model provider returned an invalid response` |
| `ProviderRequestError` / `ProviderUnknownError` | 502 | `provider_unknown_error` | `The model provider request failed` |
| `SQLAlchemyError` | 503 | `database_error` | `The database operation failed` |
| `HTTPException` | original | `http_error` | 404 使用 `Resource not found`，405 使用 `Method not allowed`，其他使用 `HTTP request failed` |
| other `Exception` | 500 | `internal_error` | `The request could not be completed` |

关键映射代码形态：

```python
if isinstance(exc, ProviderAuthError):
    return ErrorSpec(502, "provider_auth_error", "The model provider rejected its credentials")
if isinstance(exc, ProviderRateLimitError):
    return ErrorSpec(429, "provider_rate_limit", "The model provider rate limit was exceeded")
if isinstance(exc, ProviderTimeoutError):
    return ErrorSpec(504, "provider_timeout", "The model provider timed out")
if isinstance(exc, SQLAlchemyError):
    return ErrorSpec(503, "database_error", "The database operation failed")
return ErrorSpec(500, "internal_error", "The request could not be completed")
```

提供：

```python
def error_response_for_exception(exc: Exception) -> tuple[int, ErrorResponse]:
    spec = error_spec_for_exception(exc)
    return spec.status_code, ErrorResponse(
        error=ErrorDetail(
            code=spec.code,
            message=spec.message,
            request_id=get_request_id(),
        )
    )
```

所有 handler 调用同一函数；已知错误日志只写 `error_code`/`exception_type`，数据库与未预期错误可附 `safe_stack_locations(exc)`，不得写 `str(exc)`。

- [ ] **Step 7: 让 SSE 复用共享映射**

在 `stream_chat_events()` 的单个 `except Exception as exc` 中：

```python
except Exception as exc:
    session.rollback()
    _, error_response = error_response_for_exception(exc)
    yield encode_sse("error", error_response)
```

保留 `BaseException`（包括取消）不被转换为 SSE error，让 Service 的 `finally` 执行回滚。

- [ ] **Step 8: 在应用启动时注册日志和中间件**

`main.py` 在创建 app 前调用 `configure_logging()`，并注册：

```python
app.add_middleware(RequestContextMiddleware)
```

确保中间件在所有 API 路由和异常 handler 外层生效，且 CORS 回归测试仍通过。

- [ ] **Step 9: 运行 API/request 测试**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_chat_api.py tests/test_health.py -q
```

Expected: structured HTTP/SSE errors、header request ID 和现有成功 API 全部通过。

- [ ] **Step 10: Review checkpoint**

确认 SSE 与 HTTP 只有一套错误映射；所有响应 request ID 由服务端生成；不 commit。

---

### Task 5: 增加模型调用日志并保持前端错误兼容

**Files:**

- Modify: `backend/app/services/chat_service.py`
- Create: `backend/tests/test_request_logging.py`
- Modify: `backend/tests/test_chat_api.py`
- Modify: `backend/tests/test_chat_service.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/chat.ts`
- Modify: `frontend/src/api/client.test.ts`
- Modify: `frontend/src/api/chat.test.ts`

**Interfaces:**

- Consumes: ContextVar request ID、`LLMCallMetrics`、`ErrorResponse` envelope
- Produces: safe request/model log records and user-readable frontend errors

- [ ] **Step 1: 写日志安全失败测试**

`backend/tests/test_request_logging.py` 单测 `KeyValueFormatter`、`safe_stack_locations()` 和无请求上下文的 `request_id=-`。请求/模型关联测试写在已有 `api_context` 所在的 `test_chat_api.py`，验证：

```python
assert any(
    record.getMessage() == "request_completed"
    and record.method == "POST"
    and record.path == "/api/v1/chat/completions"
    and record.status_code == 200
    and record.request_id == response.headers["x-request-id"]
    for record in caplog.records
)
assert any(
    record.getMessage() == "llm_call_completed"
    and record.provider == "openai_compatible"
    and record.model == "example-model"
    and record.latency_ms >= 0
    for record in caplog.records
)
assert "complete secret prompt" not in caplog.text
assert "test-secret-key" not in caplog.text
```

为 Provider failure 在 `test_chat_api.py` 断言 `llm_call_failed`。在现有 `test_stream_chat_rolls_back_when_consumer_stops_early` Service 测试中加入 `caplog`，断言 `llm_call_cancelled`，且数据库仍无本轮 `LLMCall`。这样不跨测试模块引用局部 fixture。

- [ ] **Step 2: 运行日志测试并确认失败**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_request_logging.py -q
```

Expected: model log records do not exist，或 request record 尚未暴露可断言的 request ID extra。

- [ ] **Step 3: 在 Chat Service 记录安全模型日志**

使用 `logging.getLogger("app.llm")`。成功时：

```python
logger.info(
    "llm_call_completed",
    extra={
        "provider": request.provider,
        "model": request.model,
        "latency_ms": metrics.latency_ms,
        "outcome": "completed",
        "input_tokens": metrics.input_tokens,
        "output_tokens": metrics.output_tokens,
        "total_tokens": metrics.total_tokens,
        "estimated_cost": metrics.estimated_cost,
    },
)
```

Provider 失败时记录固定 `error_code` 与异常类名；`GeneratorExit` / `asyncio.CancelledError` 记录 `outcome=cancelled` 后原样抛出。任何日志调用都不得传 `request.content`、Provider 异常字符串或 assistant content。

- [ ] **Step 4: 运行日志与回滚测试**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/test_request_logging.py tests/test_chat_service.py -q
```

Expected: all selected tests pass，`caplog.text` 不含 fake secret/full prompt。

- [ ] **Step 5: 先写前端结构化错误失败测试**

在 `client.test.ts` 增加：

```typescript
it("uses the structured backend error message", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "database_error",
            message: "The database operation failed",
            request_id: "request-1",
          },
        }),
        { status: 503, headers: { "Content-Type": "application/json" } },
      ),
    ),
  );

  await expect(getJson("/conversations")).rejects.toThrow(
    "The database operation failed",
  );
});
```

在 `chat.test.ts` 把主 SSE error 用例改为结构化 envelope，并保留一个旧 `{"message":"..."}` 兼容测试。

- [ ] **Step 6: 运行前端目标测试并确认失败**

Run:

```powershell
cd frontend
npm run test -- --run src/api/client.test.ts src/api/chat.test.ts
```

Expected: structured error tests fail because parsers only recognize `detail` / `message`。

- [ ] **Step 7: 抽取共享前端解析器**

在 `client.ts` 导出：

```typescript
type ApiErrorPayload = {
  error?: { message?: unknown };
  detail?: unknown;
  message?: unknown;
};

export function apiErrorMessage(payload: unknown, fallback: string): string {
  if (typeof payload !== "object" || payload === null) {
    return fallback;
  }
  const candidate = payload as ApiErrorPayload;
  if (
    typeof candidate.error === "object" &&
    candidate.error !== null &&
    typeof candidate.error.message === "string"
  ) {
    return candidate.error.message;
  }
  if (typeof candidate.detail === "string") {
    return candidate.detail;
  }
  if (typeof candidate.message === "string") {
    return candidate.message;
  }
  return fallback;
}

export async function readResponseError(response: Response): Promise<string> {
  const fallback = `Request failed with status ${response.status}`;
  try {
    return apiErrorMessage(await response.json(), fallback);
  } catch {
    return fallback;
  }
}
```

`chat.ts` 删除重复 HTTP parser，导入 `apiErrorMessage` / `readResponseError`；SSE `error` 使用 `apiErrorMessage(frame.data, "Streaming request failed")`。

- [ ] **Step 8: 运行前端目标测试**

Run:

```powershell
cd frontend
npm run test -- --run src/api/client.test.ts src/api/chat.test.ts
```

Expected: structured and legacy error tests all pass。

- [ ] **Step 9: Review checkpoint**

确认前端只展示安全 message，不存储 request ID 或实现 Trace UI；不 commit。

---

### Task 6: 同步直接相关文档并完成批次验证

**Files:**

- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/03-llm-provider.md`
- Modify: `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`
- Verify: all files changed by Tasks 1～5

**Interfaces:**

- Consumes: final implemented behavior and fresh verification output
- Produces: truthful Batch 10 documentation and user-ready manual commit diff

- [ ] **Step 1: 更新最小状态说明**

把已完成范围更新为 `P1-M1-S1` through `P1-M4-S3`，下一批更新为 `P1-M4-S4～S6`。只陈述已验证行为：成功 Chat 指标、结构化错误、request ID、安全日志。不要声称 M4 完成、Plan 1 封版或 v0.1.0 tag 已创建。

- [ ] **Step 2: 更新架构和 Provider 文档**

明确记录：

```text
- token 来源于 Provider usage；缺失时为 null
- cost 使用 Registry Decimal 价格；任一价格为 null 时为 null
- latency 只覆盖 Provider 等待时间
- Provider failure/empty/cancel rollback
- HTTP/SSE error envelope 和 X-Request-ID
- Provider 分类及不传播上游正文
- 日志不记录 body、完整消息、key、SQL 参数
- 基础日志不是 Plan 4 Trace
```

- [ ] **Step 3: 更新执行步骤表状态**

仅将 Batch 10、`P1-M4-S1`、`P1-M4-S2`、`P1-M4-S3` 标记为完成；Batch 11/12 和 S4～S8 保持未完成。

- [ ] **Step 4: 运行后端全量测试**

Run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass；只允许记录已知 Starlette TestClient/httpx deprecation warning。

- [ ] **Step 5: 验证全新临时 SQLite migration**

使用临时 `DATABASE_URL`，不得删除或重建用户本地数据库：

```powershell
cd backend
$tempDb = Join-Path $env:TEMP 'ai-agent-lab-m4-verification.db'
if (Test-Path -LiteralPath $tempDb) { Remove-Item -LiteralPath $tempDb }
$env:DATABASE_URL = "sqlite:///$($tempDb -replace '\\','/')"
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current --check-heads
..\.venv\Scripts\python.exe -m alembic check
Remove-Item Env:DATABASE_URL
Remove-Item -LiteralPath $tempDb
```

Expected: upgrade/current/check all succeed；no new migration generated。

- [ ] **Step 6: 运行依赖与前端全量验证**

Run:

```powershell
..\.venv\Scripts\python.exe -m pip check
cd ..\frontend
npm run typecheck
npm run test -- --run
npm run build
```

Expected: `pip check` reports no broken requirements；typecheck/tests/build all pass。

- [ ] **Step 7: 运行无真实 Provider 的应用 smoke**

启动 Uvicorn 后验证：

```text
GET /api/v1/health -> 200 + X-Request-ID
GET /openapi.json -> chat/models/conversations routes still present
POST invalid chat payload -> 422 structured error + matching X-Request-ID
```

不得配置或调用真实 Provider credential。

- [ ] **Step 8: 运行 diff、安全和生成物检查**

Run:

```powershell
git diff --check
git status --short
rg -n --hidden -g '!**/.git/**' -g '!**/node_modules/**' -g '!**/.venv/**' '(sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._-]{12,}|OPENAI_COMPATIBLE_API_KEY\s*=\s*\S+)' .
rg --files -g '__pycache__/**' -g '.pytest_cache/**' -g 'frontend/dist/**'
```

Expected: diff check clean；secret scan only matches safe examples/tests if any and every match is manually classified；no tracked/generated artifacts added。

- [ ] **Step 9: Codex self-review**

检查：

1. diff 只覆盖 S1～S3 与必要测试/文档。
2. 无 Trace、retry、fallback 或后续 Plan 能力。
3. 普通/流式成功和失败事务语义保持一致。
4. request ID 在 HTTP header/body/SSE/log 中一致。
5. 日志与错误不泄露 fake key、完整内容、SQL 参数。
6. README/docs 不声称 M4 或 v0.1.0 已完成。
7. 所有新鲜验证证据可复述。

- [ ] **Step 10: 准备用户手动 commit 交接**

不执行 `git add` 或 `git commit`。建议 commit message：

```text
feat(observability): add llm usage errors and request logging
```

完成输出必须包含变更摘要、验证结果、Codex self-review、Fable 5 / Claude Code 复审判断、残留风险、下一批 `P1-M4-S4～S6` 建议和 commit message。
