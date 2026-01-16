"""The table page."""

import reflex as rx

from ..states.table_stock_state import TableState
from ..templates import template
from ..views.table import main_table
from ..dialogs.add_stock import add_stock_dialog


@template(route="/table", title="Table", on_load=TableState.load_entries)
def table() -> rx.Component:
    """The table page.

    Returns:
        The UI for the table page.

    """
    return rx.vstack(
        rx.heading("Table", size="5"),
        add_stock_dialog(),
        main_table(),
        spacing="8",
        width="100%",
    )
