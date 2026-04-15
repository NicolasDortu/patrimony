"""Charts for the cash management page (all-accounts overview)."""

import reflex as rx

from ...components.card import card
from ...components.donut_chart import donut_pie_chart
from ...states.cash_state import CashTableState
from ...templates import t


def cash_charts() -> rx.Component:
    """Charts showing aggregated cash data across all accounts."""
    return rx.vstack(
        rx.cond(
            CashTableState.balance_by_account_data.length() > 0,
            card(
                rx.vstack(
                    rx.text(t("chart.balance_by_account"), size="3", weight="medium"),
                    donut_pie_chart(CashTableState.balance_by_account_data),
                    spacing="3",
                    width="100%",
                ),
            ),
        ),
        rx.cond(
            CashTableState.all_operations_expense_data.length() > 0,
            card(
                rx.vstack(
                    rx.text(t("chart.income_vs_expense"), size="3", weight="medium"),
                    rx.recharts.bar_chart(
                        rx.recharts.bar(
                            data_key="income",
                            fill="var(--green-9)",
                            radius=[4, 4, 0, 0],
                            name="Income",
                        ),
                        rx.recharts.bar(
                            data_key="expense",
                            fill="var(--red-9)",
                            radius=[4, 4, 0, 0],
                            name="Expense",
                        ),
                        rx.recharts.x_axis(data_key="month", type_="category"),
                        rx.recharts.y_axis(type_="number"),
                        rx.recharts.graphing_tooltip(),
                        rx.recharts.legend(),
                        data=CashTableState.all_operations_expense_data,
                        width="100%",
                        height=300,
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),
        ),
        rx.cond(
            CashTableState.all_operations_category_data.length() > 0,
            card(
                rx.vstack(
                    rx.text(t("chart.expense_by_category"), size="3", weight="medium"),
                    donut_pie_chart(CashTableState.all_operations_category_data),
                    spacing="3",
                    width="100%",
                ),
            ),
        ),
        spacing="5",
        width="100%",
    )
