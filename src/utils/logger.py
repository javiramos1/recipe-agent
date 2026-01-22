"""Logging infrastructure for Recipe Service.

Provides centralized logging with configurable format (text/JSON) and level.
Configured via environment variables:
- LOG_LEVEL: DEBUG, INFO, WARNING, ERROR (default: INFO)
- LOG_TYPE: text, json (default: text)
"""

import json
import logging
import os
import sys
from typing import Any


class JSONFormatter(logging.Formatter):
    """Formatter that outputs structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format.

        Returns:
            JSON string with timestamp, level, logger name, message, and optional traceback.
        """
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include exception traceback if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Include request_id and session_id if present in record
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id

        return json.dumps(log_data)


class RichTextFormatter(logging.Formatter):
    """Formatter that outputs colored text with emoji icons."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "RESET": "\033[0m",       # Reset
    }

    # Emoji icons for each level
    ICONS = {
        "DEBUG": "🔍",
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "ERROR": "❌",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as colored text.

        Args:
            record: Log record to format.

        Returns:
            Formatted string with color codes and emoji icon.
        """
        level = record.levelname
        color = self.COLORS.get(level, self.COLORS["RESET"])
        icon = self.ICONS.get(level, "")
        reset = self.COLORS["RESET"]

        # Format: YYYY-MM-DD HH:MM:SS
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")

        # Build message
        message = f"{color}{icon} {timestamp} {level:<8} {record.name:<20} {record.getMessage()}{reset}"

        # Include exception traceback if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return message


def get_logger(name: str) -> logging.Logger:
    """Create and configure logger instance.

    Args:
        name: Logger name, typically module name.

    Returns:
        Configured logger instance.
    """
    logger_instance = logging.getLogger(name)

    # Return existing logger if already configured
    if logger_instance.handlers:
        return logger_instance

    # Read configuration from environment
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_type = os.getenv("LOG_TYPE", "text").lower()

    # Set log level
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger_instance.setLevel(log_level)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Choose and attach formatter
    if log_type == "json":
        formatter = JSONFormatter()
    else:
        formatter = RichTextFormatter()

    handler.setFormatter(formatter)
    logger_instance.addHandler(handler)

    return logger_instance


# Create module-level logger instance
logger = get_logger("recipe_service")

# Suppress verbose informational warnings from external libraries
# (these are debug-level messages that clutter output)
logging.getLogger("google.genai").setLevel(logging.WARNING)  # Suppress Gemini debug logs