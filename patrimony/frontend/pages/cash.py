"""The cash page."""

import reflex as rx

from ..templates import template
from ..views.cash_table import cash_table
from ..states.cash_state import CashTableState


@template(route="/cash", title="Cash", on_load=CashTableState.load_entries)
def cash() -> rx.Component:
    """The cash page.

    Returns:
        The UI for the cash page.
    """
    return rx.vstack(
        rx.heading("Cash Management", size="5"),
        cash_table(),
        spacing="5",
        width="100%",
    )
