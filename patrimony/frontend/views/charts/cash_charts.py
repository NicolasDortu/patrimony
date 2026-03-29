"""Charts for the cash management page (all-accounts overview)."""

import reflex as rx

from ...components.card import card
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
                    rx.recharts.pie_chart(
                        rx.recharts.pie(
                            data=CashTableState.balance_by_account_data,
                            data_key="value",
                            name_key="name",
                            cx="50%",
                            cy="50%",
                            label=True,
                            inner_radius="80",
                            outer_radius="110",
                            stroke="none",
                            fill_opacity=0.8,
                        ),
                        rx.recharts.legend(),
                        rx.recharts.graphing_tooltip(),
                        width="100%",
                        height=300,
                    ),
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
                    rx.recharts.pie_chart(
                        rx.recharts.pie(
                            data=CashTableState.all_operations_category_data,
                            data_key="value",
                            name_key="name",
                            cx="50%",
                            cy="50%",
                            label=True,
                            inner_radius="80",
                            outer_radius="110",
                            stroke="none",
                            fill_opacity=0.8,
                        ),
                        rx.recharts.legend(),
                        rx.recharts.graphing_tooltip(),
                        width="100%",
                        height=300,
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),
        ),
        spacing="5",
        width="100%",
    )
