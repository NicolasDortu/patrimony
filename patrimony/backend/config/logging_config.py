"""Centralized logging configuration for the backend layer.

Call ``setup_backend_logging()`` once at application startup (before any
business logic runs) to configure a consistent format, level, and flush
policy for every logger under the ``patrimony.backend`` namespace.
"""

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_backend_logging(level: int = logging.INFO) -> None:
    """Configure the ``patrimony.backend`` logger hierarchy.

    * Adds a single :class:`StreamHandler` writing to *stderr*.
    * Uses a uniform format with timestamp, level, and logger name.
    * Flushes after every record so Tauri's dev console shows output
      immediately.
    """
    backend_logger = logging.getLogger("patrimony.backend")

    # Avoid adding duplicate handlers on hot-reload
    if backend_logger.handlers:
        return

    backend_logger.setLevel(level)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    # Flush after every record so output appears immediately in Tauri console
    _orig_emit = handler.emit

    def _flushing_emit(record: logging.LogRecord) -> None:
        _orig_emit(record)
        handler.flush()

    handler.emit = _flushing_emit

    backend_logger.addHandler(handler)
    backend_logger.propagate = False
