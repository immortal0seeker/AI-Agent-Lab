class DocumentError(RuntimeError):
    """Document 上传领域错误基类。"""


class DocumentFileInvalidError(DocumentError):
    def __init__(self) -> None:
        super().__init__("Document file is invalid.")


class DocumentTooLargeError(DocumentError):
    def __init__(self) -> None:
        super().__init__("Document exceeds the upload size limit.")


class DocumentTypeUnsupportedError(DocumentError):
    def __init__(self) -> None:
        super().__init__("Document type is unsupported.")


class DocumentStorageError(DocumentError):
    def __init__(self) -> None:
        super().__init__("Document storage is unavailable.")


class DocumentDuplicateError(DocumentError):
    def __init__(self) -> None:
        super().__init__("Document content already exists.")


class KnowledgeBaseDocumentLimitReachedError(DocumentError):
    def __init__(self) -> None:
        super().__init__("Knowledge base document limit reached.")
