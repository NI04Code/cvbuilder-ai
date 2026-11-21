"""Unit tests for app.core.logging."""

import logging

from app.core.logging import RequestIdFilter, configure_logging, request_id_var


def test_request_id_filter_injects_context_var():
    flt = RequestIdFilter()
    record = logging.LogRecord("test", logging.INFO, "file.py", 1, "hello", (), None)
    token = request_id_var.set("abc-999")
    try:
        assert flt.filter(record) is True
        assert record.request_id == "abc-999"  # type: ignore[attr-defined]
    finally:
        request_id_var.reset(token)


def test_configure_logging_sets_root_level_and_handler():
    configure_logging("DEBUG")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) == 1
    assert any(isinstance(f, RequestIdFilter) for f in root.handlers[0].filters)
    configure_logging("INFO")
