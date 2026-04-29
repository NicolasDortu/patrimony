"""Wealth chart visualization for portfolio overview."""

import reflex as rx

from .common import create_dynamic_gradient, period_selector
from ...states.portfolio_state import PortfolioState
from ...templates import ThemeState, t

# Asset config: (data_key, filter_value, color_var, has_var, gradient_id, label_key)
_ASSETS = [
    (
        "Stocks",
        "stocks",
        PortfolioState.stock_color,
        PortfolioState.has_stocks,
        "colorStocks",
        "asset_type.stocks",
    ),
    (
        "ETFs",
        "etfs",
        PortfolioState.etf_color,
        PortfolioState.has_etfs,
        "colorETFs",
        "asset_type.etfs",
    ),
    (
        "Crypto",
        "crypto",
        PortfolioState.crypto_color,
        PortfolioState.has_crypto,
        "colorCrypto",
        "asset_type.crypto",
    ),
    (
        "Commodity",
        "commodity",
        PortfolioState.commodity_color,
        PortfolioState.has_commodity,
        "colorCommodity",
        "asset_type.commodity",
    ),
    (
        "Cash",
        "cash",
        PortfolioState.cash_color,
        PortfolioState.has_cash,
        "colorCash",
        "asset_type.cash",
    ),
    (
        "Properties",
        "properties",
        PortfolioState.property_color,
        PortfolioState.has_properties,
        "colorProperties",
        "asset_type.properties",
    ),
]


def _asset_visible(filter_value: str, has_var: rx.Var[bool]) -> rx.Var[bool]:
    """Condition: show asset when filter is 'all' (and asset exists) or filter matches."""
    return ((PortfolioState.asset_filter == "all") & has_var) | (
        PortfolioState.asset_filter == filter_value
    )


def _wealth_area_chart() -> rx.Component:
    """Area chart showing portfolio value over time."""
    all_css = "var(--" + ThemeState.all_color + "-9)"

    gradients = [create_dynamic_gradient(ThemeState.all_color, "colorTotal")]
    gradients += [
        create_dynamic_gradient(color, gid) for _, _, color, _, gid, _ in _ASSETS
    ]

    areas = [
        rx.cond(
            PortfolioState.asset_filter == "all",
            rx.recharts.area(
                data_key="Total",
                name=t("label.total"),
                stroke=all_css,
                fill="url(#colorTotal)",
                type_="monotone",
            ),
        ),
    ]
    for data_key, fval, color, has_var, gid, label_key in _ASSETS:
        css = "var(--" + color + "-9)"
        areas.append(
            rx.cond(
                _asset_visible(fval, has_var),
                rx.recharts.area(
                    data_key=data_key,
                    name=t(label_key),
                    stroke=css,
                    fill=f"url(#{gid})",
                    type_="monotone",
                ),
            )
        )

    return rx.recharts.area_chart(
        *gradients,
        *areas,
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
    bars = [
        rx.cond(
            PortfolioState.asset_filter == "all",
            rx.recharts.bar(
                data_key="Total", name=t("label.total"), fill=rx.color("blue", 9)
            ),
        ),
    ]
    for data_key, fval, color, has_var, _, label_key in _ASSETS:
        css = "var(--" + color + "-9)"
        bars.append(
            rx.cond(
                _asset_visible(fval, has_var),
                rx.recharts.bar(data_key=data_key, name=t(label_key), fill=css),
            )
        )

    return rx.recharts.bar_chart(
        *bars,
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
                rx.text(
                    t("chart.wealth_overview"),
                    size="4",
                    weight="medium",
                ),
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
