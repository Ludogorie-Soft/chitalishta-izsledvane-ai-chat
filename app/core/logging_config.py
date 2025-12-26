"""Structured logging configuration for the application."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

import structlog
from structlog.types import Processor

from app.core.config import settings


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    log_file_max_bytes: int = 10485760,  # 10MB
    log_file_backup_count: int = 5,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("json" or "console")
        log_file: Optional path to log file (if None, logs to stdout only)
        log_file_max_bytes: Maximum size of log file before rotation (bytes)
        log_file_backup_count: Number of backup log files to keep
    """
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    # Configure processors based on format
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,  # Merge context variables
        structlog.stdlib.add_log_level,  # Add log level
        structlog.stdlib.add_logger_name,  # Add logger name
        structlog.processors.TimeStamper(fmt="iso"),  # Add ISO timestamp
        structlog.processors.StackInfoRenderer(),  # Add stack info for exceptions
        structlog.processors.format_exc_info,  # Format exceptions
    ]

    # Add format-specific renderer
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:  # console format
        processors.append(
            structlog.dev.ConsoleRenderer(colors=True)
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure file logging with rotation if log_file is specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_path),
            maxBytes=log_file_max_bytes,
            backupCount=log_file_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)

        # Configure formatter for file (always JSON for structured logs)
        file_formatter = logging.Formatter("%(message)s")
        file_handler.setFormatter(file_formatter)

        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

        # Also configure structlog to write to file
        # We'll use a custom processor to write JSON to file
        if log_format == "console":
            # If console format is used, we still want JSON in the file
            # Add a separate file logger that outputs JSON
            file_logger = logging.getLogger("file_logger")
            file_logger.addHandler(file_handler)
            file_logger.setLevel(numeric_level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Initialize logging on module import
configure_logging(
    log_level=settings.log_level,
    log_format=settings.log_format,
    log_file=settings.log_file if settings.log_file else None,
    log_file_max_bytes=settings.log_file_max_bytes,
    log_file_backup_count=settings.log_file_backup_count,
)

