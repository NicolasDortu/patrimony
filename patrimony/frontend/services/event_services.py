"""Frontend service for persistent event log."""

from ...backend.application import container
from .models import df_to_dicts, operation_result, safe_query


class EventLogService:
    """Frontend service for persistent event log."""

    @staticmethod
    @operation_result(failure="Failed to persist events")
    def save_events(events: list[dict]):
        container.event_log_repository().add_batch(events)

    @staticmethod
    @safe_query([])
    def get_recent(limit: int = 100) -> list[dict]:
        return df_to_dicts(container.event_log_repository().get_recent(limit))

    @staticmethod
    @operation_result(failure="Failed to clear events")
    def clear():
        container.event_log_repository().clear()
