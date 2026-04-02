"""State for the notification area on the overview page."""

import reflex as rx

from ..config.event_collector import event_collector


class NotificationState(rx.State):
    """Collects log events from the frontend EventCollector and exposes them to the UI."""

    events: list[dict] = []

    @rx.var
    def event_count(self) -> int:
        return len(self.events)

    @rx.var
    def has_events(self) -> bool:
        return len(self.events) > 0

    @rx.event
    def load_events(self) -> None:
        """Drain new events from the collector and prepend to the list."""
        new = event_collector.drain()
        if new:
            self.events = [
                {
                    "level": e.level,
                    "summary": e.summary,
                    "detail": e.detail,
                    "timestamp": e.timestamp,
                }
                for e in reversed(new)
            ] + self.events
            # Keep a reasonable limit
            self.events = self.events[:100]

    @rx.event
    def clear_events(self) -> None:
        """Clear all events."""
        self.events = []
