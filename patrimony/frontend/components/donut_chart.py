"""Reusable chart components."""

import reflex as rx

from ..templates import ThemeState


def donut_pie_chart(
    data: rx.Var,
    *,
    inner_radius: str = "80",
    outer_radius: str = "110",
    fill_opacity: float = 0.8,
    height: int = 300,
) -> rx.Component:
    """Standard donut-style pie chart used across pages.

    Args:
        data: Reactive list of dicts with ``name``, ``value``, and optional ``fill`` keys.
        inner_radius: Inner donut radius (CSS string).
        outer_radius: Outer donut radius (CSS string).
        fill_opacity: Fill opacity (0..1).
        height: Chart height in pixels.
    """
    return rx.recharts.pie_chart(
        rx.recharts.pie(
            data=data,
            data_key="value",
            name_key="name",
            cx="50%",
            cy="50%",
            label=True,
            label_line=True,
            inner_radius=inner_radius,
            outer_radius=outer_radius,
            stroke="none",
            fill_opacity=fill_opacity,
            padding_angle=1,
        ),
        rx.recharts.legend(
            vertical_align="bottom",
            wrapper_style={"paddingTop": "8px"},
        ),
        rx.recharts.graphing_tooltip(),
        # Reserve space on every side for the leader-line labels and the
        # bottom legend so amounts/names never get clipped by the chart box.
        margin={"top": 24, "right": 64, "bottom": 32, "left": 64},
        width="100%",
        height=height,
    )


def _legend_row(item, currency_symbol: rx.Var) -> rx.Component:
    """One legend row: color dot + name on the left, % + amount on the right."""
    return rx.hstack(
        rx.box(
            width="12px",
            height="12px",
            min_width="12px",
            border_radius="3px",
            background=item["fill"],
        ),
        rx.text(
            item["name"],
            size="2",
            weight="medium",
            white_space="nowrap",
            overflow="hidden",
            text_overflow="ellipsis",
        ),
        rx.spacer(),
        rx.vstack(
            rx.text(
                f"{item['percentage']}%",
                size="2",
                weight="bold",
                white_space="nowrap",
            ),
            rx.text(
                currency_symbol + f"{item['value']:,.2f}",
                size="1",
                color=rx.color("gray", 10),
                white_space="nowrap",
            ),
            spacing="0",
            align="end",
        ),
        align="center",
        spacing="2",
        width="100%",
        padding_y="0.25rem",
    )


def donut_pie_chart_with_legend(
    data: rx.Var,
    *,
    height: int = 280,
    inner_radius: str = "55",
    outer_radius: str = "85",
    fill_opacity: float = 0.85,
    currency_symbol: rx.Var | None = None,
) -> rx.Component:
    """Donut pie chart with a complete side-legend (name + % + amount)."""
    sym = currency_symbol if currency_symbol is not None else ThemeState.currency_symbol
    chart = rx.recharts.pie_chart(
        rx.recharts.pie(
            data=data,
            data_key="value",
            name_key="name",
            cx="50%",
            cy="50%",
            label=False,
            label_line=False,
            inner_radius=inner_radius,
            outer_radius=outer_radius,
            stroke="none",
            fill_opacity=fill_opacity,
            padding_angle=1,
        ),
        rx.recharts.graphing_tooltip(),
        margin={"top": 8, "right": 8, "bottom": 8, "left": 8},
        width="100%",
        height=height,
    )
    legend = rx.vstack(
        rx.foreach(data, lambda item: _legend_row(item, sym)),
        spacing="1",
        width="100%",
    )
    return rx.flex(
        rx.box(chart, flex="1 1 0", min_width="0", width="100%"),
        rx.box(legend, flex="1 1 0", min_width="0", width="100%"),
        align="center",
        gap="1rem",
        width="100%",
        wrap="wrap",
    )
