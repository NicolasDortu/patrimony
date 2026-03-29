"""Balance operations page for a specific cash account."""

import reflex as rx

from ..states.cash_operations_state import CashOperationsState
from ..templates import template, t
from ..views.charts.expense_chart import expense_chart
from ..views.tables.cash_operations_table import cash_operations_table
from ..views.tables.spreadsheet_view import spreadsheet_or_table


@template(
    route="/cash_operations",
    title="Cash Operations",
    on_load=[CashOperationsState.on_page_load],
)
def cash_operations() -> rx.Component:
    """The cash operations page."""
    return rx.vstack(
        rx.hstack(
            rx.heading(
                t("cash_ops.title_prefix") + " " + CashOperationsState.account_number,
                size="5",
            ),
            rx.spacer(),
            rx.button(
                rx.cond(
                    CashOperationsState.chart_view,
                    rx.icon("table", size=16),
                    rx.icon("bar-chart-3", size=16),
                ),
                rx.cond(
                    CashOperationsState.chart_view,
                    t("btn.table_view"),
                    t("btn.chart_view"),
                ),
                variant="ghost",
                size="2",
                on_click=CashOperationsState.toggle_chart_view,
                cursor="pointer",
            ),
            align="center",
            width="100%",
        ),
        rx.flex(
            rx.button(
                rx.icon("arrow-left", size=20),
                t("cash_ops.back"),
                size="3",
                variant="soft",
                on_click=rx.redirect("/cash"),
            ),
            justify="end",
            width="100%",
        ),
        rx.cond(
            CashOperationsState.chart_view,
            expense_chart(),
            spreadsheet_or_table(CashOperationsState, cash_operations_table()),
        ),
        spacing="5",
        width="100%",
    )
