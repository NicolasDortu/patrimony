"""In-memory event buffer for the notification area.

Decoupled from logging configuration so that:
- ``logging_config.py`` is solely responsible for logger setup (SRP).
- UI states depend on this module, not on logging internals (DIP).
"""

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class EventRecord:
    """A single event for the notification area."""

    level: str
    summary: str
    detail: str
    timestamp: str


class EventCollector(logging.Handler):
    """Ring-buffer logging handler that stores the last *maxlen* records.

    Attach to any logger hierarchy; the notification state can then
    ``drain()`` buffered events for display in the UI.
    """

    def __init__(self, maxlen: int = 50) -> None:
        super().__init__(level=logging.INFO)
        self._buffer: deque[EventRecord] = deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        self._buffer.append(
            EventRecord(
                level=record.levelname,
                summary=record.getMessage()[:120],
                detail=self.format(record),
                timestamp=datetime.fromtimestamp(record.created).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            )
        )

    def drain(self) -> list[EventRecord]:
        """Return all buffered records and clear the buffer."""
        items = list(self._buffer)
        self._buffer.clear()
        return items

    def peek(self) -> list[EventRecord]:
        """Return buffered records without clearing."""
        return list(self._buffer)

    @property
    def count(self) -> int:
        return len(self._buffer)


# Module-level singleton — shared between logging_config (attaches it)
# and notification_state (drains it).
event_collector = EventCollector()
