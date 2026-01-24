"""The table page."""

import reflex as rx

from ..states.table_stock_state import TableState
from ..templates import template
from ..views.equity_table import main_table


@template(route="/equities", title="Equities", on_load=TableState.load_entries)
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
