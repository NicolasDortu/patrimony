"""The table page."""

import reflex as rx

from ..states.securities_total_state import TableStateTotal
from ..templates import template
from ..views.equity_total_table import main_table


@template(route="/equities", title="Equities", on_load=TableStateTotal.load_entries)
def equities() -> rx.Component:
    """The equities page.

    Returns:
        The UI for the equities page.
    """
    return rx.vstack(
        rx.heading("Your positions", size="5"),
        main_table(),
        spacing="5",
        width="100%",
    )
