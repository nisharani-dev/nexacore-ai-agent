"""
logging_config.py
-----------------
Centralized structured logging configuration.

Supports:
- JSON structured logging (for log aggregation)
- Colored console output (local development)
- File logging with rotation
- Request tracing with correlation IDs
- Context propagation (user, session, request info)

Usage:
    from backend.logging_config import setup_logging, get_logger
    
    setup_logging()  # Call once on startup
    logger = get_logger(__name__)
    logger.info("event", user_id="user123", action="login")
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Convert log record to JSON."""
        log_obj: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add extra fields (from logger.info(..., **extra_fields))
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "session_id"):
            log_obj["session_id"] = record.session_id
        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id
        if hasattr(record, "action"):
            log_obj["action"] = record.action
        if hasattr(record, "status"):
            log_obj["status"] = record.status
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms

        # Add any other extra fields
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "taskName",
                "asctime",
            }:
                log_obj[key] = str(value)

        return json.dumps(log_obj, default=str)


class ColoredFormatter(logging.Formatter):
    """Format logs with colors for console output."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format with colors."""
        levelname = record.levelname
        color = self.COLORS.get(levelname, "")

        # Build message with context
        msg_parts = [record.getMessage()]
        if hasattr(record, "request_id"):
            msg_parts.append(f"request_id={record.request_id}")
        if hasattr(record, "session_id"):
            msg_parts.append(f"session_id={record.session_id}")
        if hasattr(record, "user_id"):
            msg_parts.append(f"user_id={record.user_id}")

        message = " | ".join(msg_parts)

        formatted = f"{color}[{record.levelname:<8}]{self.RESET} {record.name}: {message}"

        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


class StructuredLogger(logging.LoggerAdapter):
    """Logger adapter that adds context (request_id, session_id, etc)."""

    def __init__(self, logger: logging.Logger, context: Optional[dict] = None):
        super().__init__(logger, context or {})

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        """Add context to every log call."""
        # Merge context into extra dict
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",  # "json" or "colored"
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
) -> None:
    """
    Configure centralized logging.

    Args:
        log_level: DEBUG, INFO, WARNING, ERROR, CRITICAL
        log_format: "json" for production, "colored" for development
        log_file: Optional file path for file logging
        log_dir: Directory to store rotated log files
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Select formatter
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = ColoredFormatter()

    # Console handler (always enabled)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        # Create log directory if needed
        if log_dir:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
            log_file = str(Path(log_dir) / log_file)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=5,  # Keep 5 rotated files
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(JSONFormatter())  # Always JSON for files
        root_logger.addHandler(file_handler)

    # Set common libraries to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def get_structured_logger(
    name: str, context: Optional[dict] = None
) -> StructuredLogger:
    """Get a logger with context support for request/session tracking."""
    logger = logging.getLogger(name)
    return StructuredLogger(logger, context)


# Convenience function for adding context to existing logger
def add_context(logger: logging.Logger, **context) -> StructuredLogger:
    """Wrap logger with context."""
    return StructuredLogger(logger, context)
