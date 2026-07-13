import logging
import traceback
from pathlib import Path
from typing import Any

from app.core.request_context import get_request_id


STANDARD_RECORD_KEYS = set(logging.makeLogRecord({}).__dict__)
_base_record_factory = logging.getLogRecordFactory()


def _request_record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
    record = _base_record_factory(*args, **kwargs)
    record.request_id = get_request_id()
    return record


class KeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields: dict[str, object] = {
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for key, value in record.__dict__.items():
            if key not in STANDARD_RECORD_KEYS and key not in {
                "asctime",
                "message",
                "request_id",
            }:
                fields[key] = value
        return " ".join(f"{key}={value!s}" for key, value in fields.items())


def configure_logging() -> None:
    if logging.getLogRecordFactory() is not _request_record_factory:
        logging.setLogRecordFactory(_request_record_factory)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    if not any(
        isinstance(handler.formatter, KeyValueFormatter)
        for handler in root.handlers
    ):
        handler = logging.StreamHandler()
        handler.setFormatter(KeyValueFormatter())
        root.addHandler(handler)


def safe_stack_locations(exc: BaseException) -> str:
    frames = traceback.extract_tb(exc.__traceback__)[-8:]
    return "<-".join(
        f"{Path(frame.filename).name}:{frame.name}:{frame.lineno}"
        for frame in frames
    )
