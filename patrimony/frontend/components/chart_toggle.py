"""Reusable chart/table toggle button component."""

import reflex as rx

from ..templates import t


def chart_table_toggle(state_cls) -> rx.Component:
    """Toggle button that switches between chart and table view.

    Args:
        state_cls: Any state class that inherits SearchSortMixin (has chart_view and toggle_chart_view).
    """
    return rx.button(
        rx.cond(
            state_cls.chart_view,
            rx.icon("table", size=16),
            rx.icon("bar-chart-3", size=16),
        ),
        rx.cond(
            state_cls.chart_view,
            t("btn.table_view"),
            t("btn.chart_view"),
        ),
        variant="ghost",
        size="2",
        on_click=state_cls.toggle_chart_view,
        cursor="pointer",
    )
