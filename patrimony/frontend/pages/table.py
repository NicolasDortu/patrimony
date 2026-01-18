"""The table page."""

import reflex as rx

from ..states.table_stock_state import TableState
from ..templates import template
from ..views.table import main_table


@template(route="/table", title="Table", on_load=TableState.load_entries)
def table() -> rx.Component:
    """The table page.

    Returns:
        The UI for the table page.

    """
    return rx.vstack(
        rx.heading("Your positions", size="5"),
        main_table(),
        spacing="5",
        width="100%",
    )
