"""Frontend service for persistent event log."""

import logging

from ...backend.presentation.di_container import container

logger = logging.getLogger(__name__)


class EventLogService:
    """Frontend service for persistent event log."""

    @staticmethod
    def save_events(events: list[dict]) -> None:
        try:
            container.event_log_repository().add_batch(events)
        except Exception as e:
            logger.error("Failed to persist events: %s", e)

    @staticmethod
    def get_recent(limit: int = 100) -> list[dict]:
        try:
            df = container.event_log_repository().get_recent(limit)
            return df.to_dicts() if not df.is_empty() else []
        except Exception as e:
            logger.error("Failed to load events: %s", e)
            return []

    @staticmethod
    def clear() -> None:
        try:
            container.event_log_repository().clear()
        except Exception as e:
            logger.error("Failed to clear events: %s", e)
