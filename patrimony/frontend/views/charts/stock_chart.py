"""Stock chart visualization for individual security detail view."""

import reflex as rx

from .common import create_gradient, period_selector
from ...states.securities_details_state import TableStateDetails


def stock_chart() -> rx.Component:
    """Stock price chart with period selector."""
    return rx.vstack(
        rx.hstack(
            rx.hstack(
                rx.icon("line-chart", size=20),
                rx.text("Price History", size="4", weight="medium"),
                align="center",
                spacing="2",
            ),
            period_selector(
                TableStateDetails.selected_period, TableStateDetails.set_chart_period
            ),
            justify="between",
            width="100%",
            margin_bottom="1em",
        ),
        rx.recharts.area_chart(
            create_gradient("accent", "colorPrice"),
            rx.recharts.area(
                data_key="price",
                stroke=rx.color("accent", 9),
                fill="url(#colorPrice)",
                type_="monotone",
            ),
            rx.recharts.x_axis(data_key="name", axis_line=False, tick_line=False),
            rx.recharts.y_axis(axis_line=False, tick_line=False),
            rx.recharts.cartesian_grid(stroke_dasharray="3 3", vertical=False),
            rx.recharts.graphing_tooltip(),
            data=TableStateDetails.stock_chart_data,
            width="100%",
            height=350,
        ),
        width="100%",
        spacing="4",
    )
