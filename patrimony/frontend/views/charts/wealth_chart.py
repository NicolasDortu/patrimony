"""Wealth chart visualization for portfolio overview."""

import reflex as rx

from .common import create_gradient, period_selector
from ...states.portfolio_state import PortfolioState


def _wealth_area_chart() -> rx.Component:
    """Area chart showing portfolio value over time."""
    return rx.recharts.area_chart(
        create_gradient("blue", "colorTotal"),
        create_gradient("green", "colorCash"),
        create_gradient("purple", "colorStocks"),
        create_gradient("orange", "colorETFs"),
        create_gradient("yellow", "colorCrypto"),
        create_gradient("red", "colorCommodity"),
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
            ((PortfolioState.asset_filter == "all") & PortfolioState.has_stocks)
            | (PortfolioState.asset_filter == "stocks"),
            rx.recharts.area(
                data_key="Stocks",
                stroke=rx.color("purple", 9),
                fill="url(#colorStocks)",
                type_="monotone",
            ),
        ),
        rx.cond(
            ((PortfolioState.asset_filter == "all") & PortfolioState.has_etfs)
            | (PortfolioState.asset_filter == "etfs"),
            rx.recharts.area(
                data_key="ETFs",
                stroke=rx.color("orange", 9),
                fill="url(#colorETFs)",
                type_="monotone",
            ),
        ),
        rx.cond(
            ((PortfolioState.asset_filter == "all") & PortfolioState.has_crypto)
            | (PortfolioState.asset_filter == "crypto"),
            rx.recharts.area(
                data_key="Crypto",
                stroke=rx.color("yellow", 9),
                fill="url(#colorCrypto)",
                type_="monotone",
            ),
        ),
        rx.cond(
            ((PortfolioState.asset_filter == "all") & PortfolioState.has_commodity)
            | (PortfolioState.asset_filter == "commodity"),
            rx.recharts.area(
                data_key="Commodity",
                stroke=rx.color("red", 9),
                fill="url(#colorCommodity)",
                type_="monotone",
            ),
        ),
        rx.cond(
            ((PortfolioState.asset_filter == "all") & PortfolioState.has_cash)
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
        data=PortfolioState.get_chart_data,
        width="100%",
        height=400,
    )


def _wealth_bar_chart() -> rx.Component:
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
            ((PortfolioState.asset_filter == "all") & PortfolioState.has_stocks)
            | (PortfolioState.asset_filter == "stocks"),
            rx.recharts.bar(
                data_key="Stocks",
                fill=rx.color("purple", 9),
            ),
        ),
        rx.cond(
            ((PortfolioState.asset_filter == "all") & PortfolioState.has_etfs)
            | (PortfolioState.asset_filter == "etfs"),
            rx.recharts.bar(
                data_key="ETFs",
                fill=rx.color("orange", 9),
            ),
        ),
        rx.cond(
            ((PortfolioState.asset_filter == "all") & PortfolioState.has_crypto)
            | (PortfolioState.asset_filter == "crypto"),
            rx.recharts.bar(
                data_key="Crypto",
                fill=rx.color("yellow", 9),
            ),
        ),
        rx.cond(
            ((PortfolioState.asset_filter == "all") & PortfolioState.has_commodity)
            | (PortfolioState.asset_filter == "commodity"),
            rx.recharts.bar(
                data_key="Commodity",
                fill=rx.color("red", 9),
            ),
        ),
        rx.cond(
            ((PortfolioState.asset_filter == "all") & PortfolioState.has_cash)
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
        data=PortfolioState.get_chart_data,
        width="100%",
        height=400,
    )


def _chart_type_toggle() -> rx.Component:
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


def _asset_filter_control() -> rx.Component:
    """Segmented control for filtering asset types."""
    return rx.segmented_control.root(
        rx.foreach(
            PortfolioState.available_filters,
            lambda f: rx.segmented_control.item(f["label"], value=f["value"]),
        ),
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
                period_selector(
                    PortfolioState.selected_period, PortfolioState.set_period
                ),
                _asset_filter_control(),
                _chart_type_toggle(),
                align="center",
                spacing="3",
            ),
            justify="between",
            width="100%",
            margin_bottom="1em",
        ),
        rx.cond(
            PortfolioState.chart_type == "area",
            _wealth_area_chart(),
            _wealth_bar_chart(),
        ),
        width="100%",
        spacing="4",
    )
