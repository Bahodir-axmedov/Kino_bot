"""Structured logging configuration (console + daily-rotated file).

Logs are emitted as structured key/value pairs via ``structlog`` so they are
both human-readable in the Railway log stream and greppable/parseable.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import structlog


def configure_logging(log_level: str, logs_path: str) -> None:
    """Configure stdlib logging + structlog for the whole process.

    A daily-rotated file handler keeps history under ``logs_path`` (retained
    for 14 days), while a plain stream handler ensures everything also shows
    up in Railway's own log viewer.
    """
    Path(logs_path).mkdir(parents=True, exist_ok=True)

    level = getattr(logging, log_level.upper(), logging.INFO)

    file_handler = TimedRotatingFileHandler(
        filename=str(Path(logs_path) / "bot.log"),
        when="midnight",
        backupCount=14,
        encoding="utf-8",
        utc=True,
    )
    stream_handler = logging.StreamHandler(sys.stdout)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[file_handler, stream_handler],
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
