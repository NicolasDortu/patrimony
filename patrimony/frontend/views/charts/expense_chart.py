"""Expense vs earning chart for cash operations page."""

import reflex as rx

from ...components.card import card
from ...states.cash_operations_state import CashOperationsState
from ...templates import t


def expense_chart() -> rx.Component:
    """Bar chart showing monthly income vs expense + category pie chart."""
    return rx.vstack(
        card(
            rx.vstack(
                rx.text(t("chart.income_vs_expense"), size="3", weight="medium"),
                rx.recharts.bar_chart(
                    rx.recharts.bar(
                        data_key="income",
                        fill="var(--green-9)",
                        radius=[4, 4, 0, 0],
                        name=t("label.income"),
                    ),
                    rx.recharts.bar(
                        data_key="expense",
                        fill="var(--red-9)",
                        radius=[4, 4, 0, 0],
                        name=t("label.expense"),
                    ),
                    rx.recharts.x_axis(data_key="month", type_="category"),
                    rx.recharts.y_axis(type_="number"),
                    rx.recharts.graphing_tooltip(),
                    rx.recharts.legend(),
                    data=CashOperationsState.expense_earning_data,
                    width="100%",
                    height=300,
                ),
                spacing="3",
                width="100%",
            ),
        ),
        rx.cond(
            CashOperationsState.category_expense_data.length() > 0,
            card(
                rx.vstack(
                    rx.text(t("chart.expense_by_category"), size="3", weight="medium"),
                    rx.recharts.pie_chart(
                        rx.recharts.pie(
                            data=CashOperationsState.category_expense_data,
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
