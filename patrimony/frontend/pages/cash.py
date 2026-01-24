"""The cash page."""

import reflex as rx

from ..templates import template


@template(route="/cash", title="Cash")
def cash() -> rx.Component:
    """The cash page.

    Returns:
        The UI for the cash page.
    """
    return rx.vstack(
        rx.heading("Cash page WIP", size="5"),
        spacing="5",
        width="100%",
    )
