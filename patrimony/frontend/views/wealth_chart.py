"""Wealth chart visualization for portfolio overview."""

import reflex as rx
from reflex.components.radix.themes.base import LiteralAccentColor

from ..states.portfolio_state import PortfolioState


def _create_gradient(color: LiteralAccentColor, id: str) -> rx.Component:
    """Create gradient definition for area chart."""
    return rx.el.svg.defs(
        rx.el.svg.linear_gradient(
            rx.el.svg.stop(
                stop_color=f"var(--{color}-9)",
                stop_opacity="0.8",
                offset="5%",
            ),
            rx.el.svg.stop(
                stop_color=f"var(--{color}-9)",
                stop_opacity="0",
                offset="95%",
            ),
            id=id,
            x1="0",
            x2="0",
            y1="0",
            y2="1",
        )
    )


def wealth_area_chart() -> rx.Component:
    """Area chart showing portfolio value over time."""
    return rx.recharts.area_chart(
        _create_gradient("blue", "colorTotal"),
        _create_gradient("green", "colorCash"),
        _create_gradient("purple", "colorStocks"),
        rx.cond(
            PortfolioState.asset_filter == "all",
            rx.recharts.area(
                data_key="Total",
                stroke=rx.color("blue", 9),
                fill="url(#colorTotal)",
                type_="monotone",
            ),
        ),
        rx.cond(
            (PortfolioState.asset_filter == "all")
            | (PortfolioState.asset_filter == "stocks"),
            rx.recharts.area(
                data_key="Stocks",
                stroke=rx.color("purple", 9),
                fill="url(#colorStocks)",
                type_="monotone",
            ),
        ),
        rx.cond(
            (PortfolioState.asset_filter == "all")
            | (PortfolioState.asset_filter == "cash"),
            rx.recharts.area(
                data_key="Cash",
                stroke=rx.color("green", 9),
                fill="url(#colorCash)",
                type_="monotone",
            ),
        ),
        rx.recharts.x_axis(data_key="Date", axis_line=False, tick_line=False),
        rx.recharts.y_axis(axis_line=False, tick_line=False),
        rx.recharts.cartesian_grid(stroke_dasharray="3 3", vertical=False),
        rx.recharts.legend(),
        rx.recharts.graphing_tooltip(),
        data=PortfolioState.wealth_chart_data,
        width="100%",
        height=400,
    )


def wealth_bar_chart() -> rx.Component:
    """Bar chart showing portfolio value over time."""
    return rx.recharts.bar_chart(
        rx.cond(
            PortfolioState.asset_filter == "all",
            rx.recharts.bar(
                data_key="Total",
                fill=rx.color("blue", 9),
            ),
        ),
        rx.cond(
            (PortfolioState.asset_filter == "all")
            | (PortfolioState.asset_filter == "stocks"),
            rx.recharts.bar(
                data_key="Stocks",
                fill=rx.color("purple", 9),
            ),
        ),
        rx.cond(
            (PortfolioState.asset_filter == "all")
            | (PortfolioState.asset_filter == "cash"),
            rx.recharts.bar(
                data_key="Cash",
                fill=rx.color("green", 9),
            ),
        ),
        rx.recharts.x_axis(data_key="Date", axis_line=False, tick_line=False),
        rx.recharts.y_axis(axis_line=False, tick_line=False),
        rx.recharts.cartesian_grid(stroke_dasharray="3 3", vertical=False),
        rx.recharts.legend(),
        rx.recharts.graphing_tooltip(),
        data=PortfolioState.wealth_chart_data,
        width="100%",
        height=400,
    )


def chart_type_toggle() -> rx.Component:
    """Toggle button for switching chart types."""
    return rx.cond(
        PortfolioState.chart_type == "area",
        rx.icon_button(
            rx.icon("area-chart"),
            size="2",
            cursor="pointer",
            variant="surface",
            on_click=PortfolioState.toggle_chart_type,
        ),
        rx.icon_button(
            rx.icon("bar-chart-3"),
            size="2",
            cursor="pointer",
            variant="surface",
            on_click=PortfolioState.toggle_chart_type,
        ),
    )


def asset_filter_control() -> rx.Component:
    """Segmented control for filtering asset types."""
    return rx.segmented_control.root(
        rx.segmented_control.item("All Assets", value="all"),
        rx.segmented_control.item("Stocks", value="stocks"),
        rx.segmented_control.item("Cash", value="cash"),
        default_value="all",
        value=PortfolioState.asset_filter,
        on_change=PortfolioState.set_asset_filter,
    )


def wealth_chart() -> rx.Component:
    """Main wealth chart component with controls."""
    return rx.vstack(
        rx.hstack(
            rx.hstack(
                rx.icon("trending-up", size=20),
                rx.text("Wealth Overview", size="4", weight="medium"),
                align="center",
                spacing="2",
            ),
            rx.hstack(
                asset_filter_control(),
                chart_type_toggle(),
                align="center",
                spacing="3",
            ),
            justify="between",
            width="100%",
            margin_bottom="1em",
        ),
        rx.cond(
            PortfolioState.chart_type == "area",
            wealth_area_chart(),
            wealth_bar_chart(),
        ),
        width="100%",
        spacing="4",
    )
