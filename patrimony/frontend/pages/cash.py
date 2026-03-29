"""The cash page."""

import reflex as rx

from ..components.chart_toggle import chart_table_toggle
from ..templates import template, t
from ..views.tables.cash_table import cash_table
from ..states.cash_state import CashTableState
from ..views.tables.spreadsheet_view import spreadsheet_or_table
from ..views.charts.cash_charts import cash_charts


@template(route="/cash", title="Cash", on_load=CashTableState.load_entries)
def cash() -> rx.Component:
    """The cash page."""
    return rx.vstack(
        rx.hstack(
            rx.heading(t("page.cash.title"), size="5"),
            rx.spacer(),
            chart_table_toggle(CashTableState),
            align="center",
            width="100%",
        ),
        rx.cond(
            CashTableState.chart_view,
            cash_charts(),
            spreadsheet_or_table(CashTableState, cash_table()),
        ),
        spacing="5",
        width="100%",
    )
