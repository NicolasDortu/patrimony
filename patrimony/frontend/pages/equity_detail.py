"""The equity detail page."""

import reflex as rx

from ..templates import template


@template(route="/equity_detail", title="Equity Detail")
def equity_detail() -> rx.Component:
    """The equity detail page.

    Returns:
        The UI for the equity detail page.
    """
    return rx.vstack(
        rx.heading("Equity detail page WIP", size="5"),
        spacing="5",
        width="100%",
    )
