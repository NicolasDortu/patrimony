"""Empty state component for tables with no data."""

import reflex as rx

from ..templates import t


def empty_table(
    message_key: str,
    icon_name: str = "inbox",
    add_dialog: rx.Component | None = None,
) -> rx.Component:
    """Display a centered empty state message with icon and optional add button."""
    children: list[rx.Component] = [
        rx.icon(icon_name, size=48, color=rx.color("gray", 8)),
        rx.text(
            t(message_key),
            size="4",
            color=rx.color("gray", 10),
            weight="medium",
        ),
    ]
    if add_dialog is not None:
        children.append(add_dialog)
    return rx.center(
        rx.vstack(*children, align="center", spacing="3"),
        width="100%",
        min_height="300px",
    )
