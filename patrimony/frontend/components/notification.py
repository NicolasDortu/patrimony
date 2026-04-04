import reflex as rx
from reflex.components.radix.themes.base import (
    LiteralAccentColor,
)

from ..states.notification_state import NotificationState
from ..styles import styles
from ..templates import t


def _level_color(level: str) -> str:
    """Map log level to badge color."""
    return rx.cond(
        level == "ERROR",
        "tomato",
        rx.cond(level == "WARNING", "amber", "grass"),
    )


def _event_row(event: dict) -> rx.Component:
    """Single event row in the notification popover."""
    return rx.hstack(
        rx.badge(event["level"], color_scheme=_level_color(event["level"]), size="1"),
        rx.vstack(
            rx.text(event["summary"], size="2", weight="medium", trim="both"),
            rx.text(event["timestamp"], size="1", color=rx.color("gray", 9)),
            spacing="1",
            flex="1",
        ),
        width="100%",
        padding_y="0.35rem",
        align="center",
    )


def notification(icon: str, color: LiteralAccentColor) -> rx.Component:
    """Notification bell with dynamic event count and popover."""
    return rx.popover.root(
        rx.popover.trigger(
            rx.box(
                rx.icon_button(
                    rx.icon(icon),
                    padding="0.5rem",
                    radius="full",
                    variant="soft",
                    color_scheme=color,
                    size="3",
                    on_click=NotificationState.load_events,
                ),
                rx.cond(
                    NotificationState.event_count > 0,
                    rx.badge(
                        rx.text(NotificationState.event_count, size="1"),
                        radius="full",
                        variant="solid",
                        color_scheme="tomato",
                        style=styles.notification_badge_style,
                    ),
                ),
                position="relative",
            ),
        ),
        rx.popover.content(
            rx.vstack(
                rx.hstack(
                    rx.text(t("notification.title"), size="3", weight="bold"),
                    rx.spacer(),
                    rx.cond(
                        NotificationState.has_events,
                        rx.button(
                            t("btn.clear"),
                            size="1",
                            variant="ghost",
                            on_click=NotificationState.clear_events,
                        ),
                    ),
                    width="100%",
                    align="center",
                ),
                rx.separator(),
                rx.cond(
                    NotificationState.has_events,
                    rx.scroll_area(
                        rx.vstack(
                            rx.foreach(NotificationState.events, _event_row),
                            spacing="1",
                            width="100%",
                        ),
                        max_height="300px",
                        width="100%",
                    ),
                    rx.center(
                        rx.text(
                            t("notification.empty"),
                            size="2",
                            color=rx.color("gray", 9),
                        ),
                        padding="2em",
                    ),
                ),
                spacing="3",
                width="100%",
            ),
            side="bottom",
            align="end",
            style={"min_width": "320px", "max_width": "400px"},
        ),
    )
