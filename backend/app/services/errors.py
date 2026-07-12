from uuid import UUID


class ServiceError(RuntimeError):
    """业务服务层异常基类。"""


class ConversationNotFoundError(ServiceError):
    def __init__(self, conversation_id: UUID) -> None:
        super().__init__(f"Conversation not found: {conversation_id}")
        self.conversation_id = conversation_id


class ChatModelNotFoundError(ServiceError):
    def __init__(self, provider: str, model: str) -> None:
        super().__init__(f"Model not found: {provider}/{model}")
        self.provider = provider
        self.model = model


class ChatProviderUnavailableError(ServiceError):
    def __init__(self, provider: str) -> None:
        super().__init__(f"Provider is not configured: {provider}")
        self.provider = provider
