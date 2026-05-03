"""Centralized logging configuration for the frontend layer.

It uses a custom stream handler that flushes after every record, ensuring that log messages appear immediately in Tauri's dev console.

Attaches the shared ``EventCollector`` (defined in ``event_collector.py``)
so that log records also feed the notification area.
"""

import logging
import sys

from .event_collector import event_collector

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _FlushingStreamHandler(logging.StreamHandler):
    """An equivalent to `logging.StreamHandler` that flushes after every record."""

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


def setup_frontend_logging(level: int = logging.INFO) -> None:
    """Configure the ``patrimony.frontend`` logger hierarchy."""
    frontend_logger = logging.getLogger("patrimony.frontend")

    if frontend_logger.handlers:
        return

    frontend_logger.setLevel(level)

    # Console handler
    console = _FlushingStreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    frontend_logger.addHandler(console)

    # Event collector handler (for notification area)
    event_collector.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    frontend_logger.addHandler(event_collector)

    frontend_logger.propagate = False
