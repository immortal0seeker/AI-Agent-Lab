import logging

from app.core.logging import KeyValueFormatter, configure_logging, safe_stack_locations


def test_formatter_includes_request_id_outside_request_context() -> None:
    configure_logging()
    record = logging.getLogRecordFactory()(
        "test.logger",
        logging.INFO,
        __file__,
        1,
        "test_event",
        (),
        None,
    )

    formatted = KeyValueFormatter().format(record)

    assert "event=test_event" in formatted
    assert "request_id=-" in formatted


def test_safe_stack_locations_excludes_exception_message() -> None:
    try:
        raise RuntimeError("private database path and query parameters")
    except RuntimeError as exc:
        locations = safe_stack_locations(exc)

    assert "test_request_logging.py" in locations
    assert "test_safe_stack_locations_excludes_exception_message" in locations
    assert "private database path" not in locations
