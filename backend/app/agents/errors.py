from app.services.errors import ServiceError


class AgentError(ServiceError):
    """Simple Agent 服务边界的基础异常。"""


class AgentModelNotFoundError(AgentError):
    def __init__(self, provider: str, model: str) -> None:
        super().__init__(f"Model not found: {provider}/{model}")
        self.provider = provider
        self.model = model


class AgentModelToolsUnsupportedError(AgentError):
    def __init__(self, provider: str, model: str) -> None:
        super().__init__(f"Model does not support tools: {provider}/{model}")
        self.provider = provider
        self.model = model


class AgentProviderUnavailableError(AgentError):
    def __init__(self, provider: str) -> None:
        super().__init__(f"Provider is not configured: {provider}")
        self.provider = provider


class AgentLoopIncompleteError(AgentError):
    def __init__(self) -> None:
        super().__init__("Agent did not produce a final answer")
