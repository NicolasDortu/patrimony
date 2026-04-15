"""Reusable chart components."""

import reflex as rx


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
            inner_radius=inner_radius,
            outer_radius=outer_radius,
            stroke="none",
            fill_opacity=fill_opacity,
        ),
        rx.recharts.legend(),
        rx.recharts.graphing_tooltip(),
        width="100%",
        height=height,
    )
