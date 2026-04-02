"""Centralized logging configuration for the frontend layer.

Call ``setup_frontend_logging()`` once at application startup.
Provides the same format/flush policy as the backend, scoped to
the ``patrimony.frontend`` namespace.

Attaches the shared ``EventCollector`` (defined in ``event_collector.py``)
so that log records also feed the notification area.
"""

import logging
import sys

from .event_collector import event_collector

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_frontend_logging(level: int = logging.INFO) -> None:
    """Configure the ``patrimony.frontend`` logger hierarchy."""
    frontend_logger = logging.getLogger("patrimony.frontend")

    if frontend_logger.handlers:
        return

    frontend_logger.setLevel(level)

    # Console handler (stderr, flushing)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    _orig_emit = console.emit

    def _flushing_emit(record: logging.LogRecord) -> None:
        _orig_emit(record)
        console.flush()

    console.emit = _flushing_emit

    frontend_logger.addHandler(console)

    # Event collector handler (for notification area)
    event_collector.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    frontend_logger.addHandler(event_collector)

    frontend_logger.propagate = False
