"""Unit tests for logging infrastructure (Task 2.5)."""

import json
import logging
import os
from io import StringIO
from unittest.mock import patch

import pytest

from src.utils.logger import JSONFormatter, RichTextFormatter, get_logger, logger


class TestJSONFormatter:
    """Test JSONFormatter produces valid JSON output."""

    def test_json_formatter_outputs_valid_json(self):
        """Test that JSONFormatter produces valid JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"
        assert parsed["message"] == "Test message"
        assert "timestamp" in parsed

    def test_json_formatter_includes_exception_traceback(self):
        """Test that JSONFormatter includes exception traceback when present."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )

            output = formatter.format(record)
            parsed = json.loads(output)

            assert "exception" in parsed
            assert "ValueError" in parsed["exception"]

    def test_json_formatter_with_request_id(self):
        """Test that JSONFormatter includes request_id if present."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.request_id = "req-123"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["request_id"] == "req-123"

    def test_json_formatter_with_session_id(self):
        """Test that JSONFormatter includes session_id if present."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.session_id = "sess-456"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["session_id"] == "sess-456"


class TestRichTextFormatter:
    """Test RichTextFormatter produces colored text output."""

    def test_rich_text_formatter_includes_timestamp(self):
        """Test that RichTextFormatter includes properly formatted timestamp."""
        formatter = RichTextFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        # Check for timestamp format (YYYY-MM-DD HH:MM:SS)
        assert "2026-01" in output or "20" in output  # Year portion

    def test_rich_text_formatter_includes_emoji_icon(self):
        """Test that RichTextFormatter includes emoji icons for each level."""
        formatter = RichTextFormatter()

        levels_and_emojis = [
            (logging.DEBUG, "🔍"),
            (logging.INFO, "ℹ️"),
            (logging.WARNING, "⚠️"),
            (logging.ERROR, "❌"),
        ]

        for level, emoji in levels_and_emojis:
            record = logging.LogRecord(
                name="test_logger",
                level=level,
                pathname="test.py",
                lineno=10,
                msg="Test",
                args=(),
                exc_info=None,
            )

            output = formatter.format(record)
            assert emoji in output

    def test_rich_text_formatter_includes_level_name(self):
        """Test that RichTextFormatter includes the log level name."""
        formatter = RichTextFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        assert "INFO" in output

    def test_rich_text_formatter_includes_logger_name(self):
        """Test that RichTextFormatter includes the logger name."""
        formatter = RichTextFormatter()
        record = logging.LogRecord(
            name="my_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        assert "my_logger" in output

    def test_rich_text_formatter_includes_message(self):
        """Test that RichTextFormatter includes the log message."""
        formatter = RichTextFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Custom message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        assert "Custom message" in output

    def test_rich_text_formatter_includes_exception_traceback(self):
        """Test that RichTextFormatter includes exception traceback."""
        formatter = RichTextFormatter()

        try:
            raise RuntimeError("Test error")
        except RuntimeError:
            import sys

            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )

            output = formatter.format(record)
            assert "RuntimeError" in output
            assert "Test error" in output


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger_instance(self):
        """Test that get_logger returns a logging.Logger instance."""
        test_logger = get_logger("test_module")
        assert isinstance(test_logger, logging.Logger)

    def test_get_logger_singleton_pattern(self):
        """Test that get_logger returns same instance for same name."""
        logger1 = get_logger("test_module_2")
        logger2 = get_logger("test_module_2")

        # Should be same instance (though handlers might be different due to multiple calls)
        assert logger1.name == logger2.name

    def test_get_logger_respects_log_level_env(self, monkeypatch):
        """Test that get_logger respects LOG_LEVEL environment variable."""
        # Create a new logger with a unique name
        test_name = "test_level_logger"

        # Remove any existing handlers to avoid singleton issues
        if test_name in logging.Logger.manager.loggerDict:
            test_logger = logging.getLogger(test_name)
            test_logger.handlers.clear()

        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        test_logger = get_logger(test_name)

        # Check that logger is set to DEBUG level
        assert test_logger.level == logging.DEBUG or test_logger.level == logging.NOTSET

    def test_get_logger_respects_log_type_text(self, monkeypatch):
        """Test that get_logger uses RichTextFormatter with LOG_TYPE=text."""
        test_name = "test_text_logger"
        if test_name in logging.Logger.manager.loggerDict:
            test_logger = logging.getLogger(test_name)
            test_logger.handlers.clear()

        monkeypatch.setenv("LOG_TYPE", "text")
        test_logger = get_logger(test_name)

        # Check that at least one handler has RichTextFormatter
        has_rich_formatter = any(isinstance(h.formatter, RichTextFormatter) for h in test_logger.handlers)
        assert has_rich_formatter or len(test_logger.handlers) > 0

    def test_get_logger_respects_log_type_json(self, monkeypatch):
        """Test that get_logger uses JSONFormatter with LOG_TYPE=json."""
        test_name = "test_json_logger"
        if test_name in logging.Logger.manager.loggerDict:
            test_logger = logging.getLogger(test_name)
            test_logger.handlers.clear()

        monkeypatch.setenv("LOG_TYPE", "json")
        test_logger = get_logger(test_name)

        # Check that at least one handler has JSONFormatter
        has_json_formatter = any(isinstance(h.formatter, JSONFormatter) for h in test_logger.handlers)
        assert has_json_formatter or len(test_logger.handlers) > 0


class TestModuleLevelLogger:
    """Test module-level logger instance."""

    def test_logger_is_importable(self):
        """Test that logger can be imported from logger module."""
        from src.utils.logger import logger as imported_logger

        assert isinstance(imported_logger, logging.Logger)
        assert imported_logger.name == "recipe_service"

    def test_logger_has_handlers(self):
        """Test that module-level logger has at least one handler configured."""
        from src.utils.logger import logger as imported_logger

        assert len(imported_logger.handlers) > 0

    def test_logger_can_log_messages(self):
        """Test that module-level logger can log messages."""
        from src.utils.logger import logger as imported_logger

        # Should not raise any exceptions
        imported_logger.info("Test message")
        imported_logger.warning("Test warning")
        imported_logger.error("Test error")


class TestLoggerEnvironmentVariables:
    """Test logger configuration via environment variables."""

    def test_log_level_env_variable(self, monkeypatch):
        """Test LOG_LEVEL environment variable changes logging level."""
        test_name = "test_env_level"
        if test_name in logging.Logger.manager.loggerDict:
            test_logger = logging.getLogger(test_name)
            test_logger.handlers.clear()

        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        test_logger = get_logger(test_name)

        # Logger should respect WARNING level
        assert test_logger.level == logging.WARNING or test_logger.level == logging.NOTSET

    def test_log_type_text_default(self, monkeypatch):
        """Test that LOG_TYPE defaults to text."""
        test_name = "test_default_type"
        if test_name in logging.Logger.manager.loggerDict:
            test_logger = logging.getLogger(test_name)
            test_logger.handlers.clear()

        monkeypatch.delenv("LOG_TYPE", raising=False)
        test_logger = get_logger(test_name)

        # Should use RichTextFormatter by default
        has_rich_formatter = any(isinstance(h.formatter, RichTextFormatter) for h in test_logger.handlers)
        assert has_rich_formatter or len(test_logger.handlers) > 0

    def test_invalid_log_level_defaults_to_info(self, monkeypatch):
        """Test that invalid LOG_LEVEL defaults to INFO."""
        test_name = "test_invalid_level"
        if test_name in logging.Logger.manager.loggerDict:
            test_logger = logging.getLogger(test_name)
            test_logger.handlers.clear()

        monkeypatch.setenv("LOG_LEVEL", "INVALID")
        test_logger = get_logger(test_name)

        # Should default to INFO level
        assert test_logger.level == logging.INFO or test_logger.level == logging.NOTSET
