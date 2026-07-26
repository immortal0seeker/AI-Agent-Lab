"""知识库结构化元数据与编排边界。"""

from .document_storage import (
    AsyncReadable,
    DocumentStorage,
    StagedDocument,
    StoredDocument,
)
from .errors import (
    DocumentDuplicateError,
    DocumentError,
    DocumentFileInvalidError,
    DocumentStorageError,
    DocumentTooLargeError,
    DocumentTypeUnsupportedError,
    KnowledgeBaseDocumentLimitReachedError,
)

__all__ = [
    "AsyncReadable",
    "DocumentDuplicateError",
    "DocumentError",
    "DocumentFileInvalidError",
    "DocumentStorage",
    "DocumentStorageError",
    "DocumentTooLargeError",
    "DocumentTypeUnsupportedError",
    "KnowledgeBaseDocumentLimitReachedError",
    "StagedDocument",
    "StoredDocument",
]
