"""
Structured logging configuration for QNWIS API.

Provides JSON-formatted logs with sensitive data redaction.
"""

from __future__ import annotations

import logging
import re
import sys

# Sensitive patterns to redact in logs
SENSITIVE_PATTERNS = [
    (re.compile(r"Bearer\s+[\w\-\.]+", re.IGNORECASE), "Bearer [REDACTED]"),
    (re.compile(r"api[_-]?key[\"']?\s*[:=]\s*[\"']?[\w\-]+", re.IGNORECASE), "api_key=[REDACTED]"),
    (re.compile(r"password[\"']?\s*[:=]\s*[\"']?[^\s\"']+", re.IGNORECASE), "password=[REDACTED]"),
    (re.compile(r"secret[\"']?\s*[:=]\s*[\"']?[^\s\"']+", re.IGNORECASE), "secret=[REDACTED]"),
    (re.compile(r"token[\"']?\s*[:=]\s*[\"']?[\w\-\.]+", re.IGNORECASE), "token=[REDACTED]"),
]


def mask_sensitive_data(text: str) -> str:
    """
    Mask sensitive data in text using pattern matching.

    Args:
        text: Input text potentially containing sensitive data

    Returns:
        Text with sensitive patterns redacted
    """
    masked = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        masked = pattern.sub(replacement, masked)
    return masked


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter to redact sensitive data from log records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to redact sensitive data.

        Args:
            record: Log record to filter

        Returns:
            True (always allow record, but modify in place)
        """
        # Redact message
        if isinstance(record.msg, str):
            record.msg = mask_sensitive_data(record.msg)

        # Redact args
        if record.args:
            record.args = tuple(
                mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )

        return True


class StructuredFormatter(logging.Formatter):
    """
    JSON-structured log formatter for machine parsing.

    Outputs logs in JSON format with standard fields:
    - timestamp: ISO 8601 timestamp
    - level: Log level
    - logger: Logger name
    - message: Log message
    - extra: Additional context fields
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        import json
        from datetime import UTC, datetime

        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in (
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
            )
        }
        if extra_fields:
            log_data["extra"] = extra_fields

        return json.dumps(log_data)


def configure_logging(
    level: str = "INFO",
    json_format: bool = False,
    enable_redaction: bool = True,
) -> None:
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, use JSON structured logging
        enable_redaction: If True, enable sensitive data redaction
    """
    # Get log level
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Set formatter
    if json_format:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    handler.setFormatter(formatter)

    # Add sensitive data filter if enabled
    if enable_redaction:
        handler.addFilter(SensitiveDataFilter())

    root_logger.addHandler(handler)

    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logging.info(f"Logging configured: level={level}, json={json_format}, redaction={enable_redaction}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with standard configuration.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
