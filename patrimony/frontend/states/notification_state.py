"""State for the notification area on the overview page."""

import reflex as rx

from ..config.event_collector import event_collector
from ..services import EventLogService


class NotificationState(rx.State):
    """Collects log events from the frontend EventCollector and exposes them to the UI.

    Events are persisted to DuckDB so they survive app restarts.
    """

    events: list[dict] = []
    _loaded_from_db: bool = False

    @rx.var
    def event_count(self) -> int:
        return len(self.events)

    @rx.var
    def has_events(self) -> bool:
        return len(self.events) > 0

    @rx.event
    def load_events(self) -> None:
        """Drain new events from the collector, persist, and prepend to the list."""
        # On first load, hydrate from the database
        if not self._loaded_from_db:
            self._loaded_from_db = True
            stored = EventLogService.get_recent(100)
            self.events = [
                {
                    "level": e["level"],
                    "summary": e["summary"],
                    "detail": e.get("detail", ""),
                    "timestamp": str(e["created_at"])[:19]
                    if e.get("created_at")
                    else "",
                }
                for e in stored
            ]

        # Drain any new in-memory events
        new = event_collector.drain()
        if new:
            new_dicts = [
                {
                    "level": e.level,
                    "summary": e.summary,
                    "detail": e.detail,
                    "timestamp": e.timestamp,
                }
                for e in reversed(new)
            ]
            # Persist new events to DB
            EventLogService.save_events(new_dicts)
            self.events = new_dicts + self.events
            # Keep a reasonable limit
            self.events = self.events[:100]

    @rx.event
    def clear_events(self) -> None:
        """Clear all events from memory and database."""
        self.events = []
        EventLogService.clear()
