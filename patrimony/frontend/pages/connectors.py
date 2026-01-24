"""The connectors page."""

import reflex as rx

from ..templates import template


@template(route="/connectors", title="Connectors")
def connectors() -> rx.Component:
    """The connectors page.

    Returns:
        The UI for the connectors page.
    """
    return rx.vstack(
        rx.heading("Connectors page WIP", size="5"),
        spacing="5",
        width="100%",
    )
