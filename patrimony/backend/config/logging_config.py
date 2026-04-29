"""Centralized logging configuration for the backend layer.

It uses a custom stream handler that flushes after every record, ensuring that log messages appear immediately in Tauri's dev console.
"""

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _FlushingStreamHandler(logging.StreamHandler):
    """An equivalent to `logging.StreamHandler` that flushes after every record."""

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


def setup_backend_logging(level: int = logging.INFO) -> None:
    """Configure the ``patrimony.backend`` logger hierarchy.

    * Adds a single custom :class:`_FlushingStreamHandler` writing to *stderr*.
    * Uses a uniform format with timestamp, level, and logger name.
    * Flushes after every record so Tauri's dev console shows output
      immediately.
    """
    backend_logger = logging.getLogger("patrimony.backend")

    backend_logger.setLevel(level)

    handler = _FlushingStreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    backend_logger.addHandler(handler)
    backend_logger.propagate = False
