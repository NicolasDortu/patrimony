"""The cash page."""

import reflex as rx

from ..components.chart_toggle import chart_table_toggle
from ..components.empty_table import empty_table
from ..components.loading import loading_spinner
from ..dialogs import open_add_cash_dialog
from ..templates import template, t
from ..views.tables.cash_table import cash_table
from ..states.cash_state import CashTableState
from ..views.tables.spreadsheet_view import spreadsheet_or_table
from ..views.charts.cash_charts import cash_charts


@template(route="/cash", title="Cash", on_load=CashTableState.on_page_load)
def cash() -> rx.Component:
    """The cash page."""
    return rx.vstack(
        rx.hstack(
            rx.heading(t("page.cash.title"), size="5"),
            rx.spacer(),
            rx.cond(
                CashTableState.total_items > 0,
                chart_table_toggle(CashTableState),
            ),
            align="center",
            width="100%",
        ),
        rx.cond(
            CashTableState.is_loading,
            loading_spinner(),
            rx.cond(
                CashTableState.total_items > 0,
                rx.cond(
                    CashTableState.chart_view,
                    cash_charts(),
                    spreadsheet_or_table(CashTableState, cash_table()),
                ),
                empty_table(
                    "empty.cash",
                    "wallet",
                    open_add_cash_dialog(CashTableState.add_cash_entry),
                ),
            ),
        ),
        spacing="5",
        width="100%",
        on_unmount=CashTableState.set_chart_view(False),
    )
