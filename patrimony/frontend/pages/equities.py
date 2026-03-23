"""The table page."""

import reflex as rx

from ..states.securities_total_state import TableStateTotal
from ..templates import template
from ..views.tables.equity_total_table import main_table


def _asset_type_filter() -> rx.Component:
    """Segmented control for filtering by asset type."""
    return rx.segmented_control.root(
        rx.foreach(
            TableStateTotal.available_asset_filters,
            lambda f: rx.segmented_control.item(f["label"], value=f["value"]),
        ),
        default_value="all",
        value=TableStateTotal.selected_asset_filter,
        on_change=TableStateTotal.set_asset_filter,
    )


@template(route="/equities", title="Equities", on_load=TableStateTotal.load_entries)
def equities() -> rx.Component:
    """The equities page.

    Returns:
        The UI for the equities page.
    """
    return rx.vstack(
        rx.hstack(
            rx.heading("Your positions", size="5"),
            _asset_type_filter(),
            justify="between",
            align="center",
            width="100%",
        ),
        main_table(),
        spacing="5",
        width="100%",
    )
