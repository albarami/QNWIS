"""Basic logging utilities for QNWIS."""

from __future__ import annotations

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with standard configuration.

    Args:
        name: Logger name
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger
