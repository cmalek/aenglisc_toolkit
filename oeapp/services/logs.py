"""Logging configuration for Ænglisc Toolkit."""

import logging
import logging.handlers
import os
import sys
from typing import TYPE_CHECKING

import structlog

from oeapp.utils import get_app_data_path

if TYPE_CHECKING:
    from pathlib import Path


def get_log_dir() -> "Path":
    """
    Get the path to the log directory.

    Returns:
        The path to the log directory.

    """
    log_dir = get_app_data_path() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_file_path() -> "Path":
    """
    Get the path to the current log file.

    Returns:
        The path to the current log file.

    """
    return get_log_dir() / "oe_annotator.log.json"


def configure_logging() -> None:
    """
    Configure structlog and standard logging.

    - JSON logs to file with 3-week rotation.
    - Console logs for development.
    """
    log_file = get_log_file_path()

    # Shared processors for both structlog and standard logging
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # File handler (JSON)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when="D",
        interval=21,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
        )
    )
    handlers = [file_handler]

    if "AENGLISC_TOOLKIT_DEBUG" in os.environ:
        # Console handler (Text) - only for development or if specifically requested
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.dev.ConsoleRenderer(),
            )
        )
        handlers.append(console_handler)  # type: ignore[arg-type]

    # Configure standard logging
    logging.basicConfig(
        handlers=handlers,
        level=logging.INFO,
        force=True,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            *processors,  # type: ignore[list-item]
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance.

    Args:
        name: Logger name

    Returns:
        A structlog logger

    """
    return structlog.get_logger(name)
