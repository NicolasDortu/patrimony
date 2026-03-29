"""The cash page."""

import reflex as rx

from ..templates import template, t
from ..views.tables.cash_table import cash_table
from ..states.cash_state import CashTableState
from ..views.tables.spreadsheet_view import spreadsheet_or_table
from ..views.charts.cash_charts import cash_charts


@template(route="/cash", title="Cash", on_load=CashTableState.load_entries)
def cash() -> rx.Component:
    """The cash page.

    Returns:
        The UI for the cash page.
    """
    return rx.vstack(
        rx.hstack(
            rx.heading(t("page.cash.title"), size="5"),
            rx.spacer(),
            rx.button(
                rx.cond(
                    CashTableState.chart_view,
                    rx.icon("table", size=16),
                    rx.icon("bar-chart-3", size=16),
                ),
                rx.cond(
                    CashTableState.chart_view,
                    t("btn.table_view"),
                    t("btn.chart_view"),
                ),
                variant="ghost",
                size="2",
                on_click=CashTableState.toggle_chart_view,
                cursor="pointer",
            ),
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
