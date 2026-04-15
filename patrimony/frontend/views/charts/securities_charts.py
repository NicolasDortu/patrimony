"""Chart views for the securities page — securities type allocation + weighted heatmap."""

import reflex as rx

from ...components.card import card
from ...components.donut_chart import donut_pie_chart
from ...states.securities_total_state import TableStateTotal
from ...templates import t


def _allocation_pie_chart() -> rx.Component:
    """Pie chart showing allocation by securities type."""
    return card(
        rx.vstack(
            rx.text(t("chart.securities_type_allocation"), size="3", weight="medium"),
            donut_pie_chart(TableStateTotal.asset_type_allocation),
            spacing="3",
            width="100%",
        ),
    )


def _heatmap_cell(item: dict) -> rx.Component:
    """Single cell in the weighted heatmap — sized by portfolio weight."""
    ret = item["return_pct"].to(float)
    weight = item["weight"].to(float)
    return rx.box(
        rx.vstack(
            rx.text(item["ticker"], size="2", weight="bold", color="white"),
            rx.text(
                rx.cond(ret >= 0, "+", ""),
                item["return_pct"],
                "%",
                size="1",
                color="white",
                opacity="0.9",
            ),
            align="center",
            spacing="1",
        ),
        background=rx.cond(
            ret >= 0,
            rx.cond(
                ret > 5,
                "var(--green-9)",
                "var(--green-7)",
            ),
            rx.cond(
                ret < -5,
                "var(--red-9)",
                "var(--red-7)",
            ),
        ),
        display="flex",
        align_items="center",
        justify_content="center",
        border_radius="6px",
        padding="0.75rem",
        min_height="70px",
        flex_grow=weight,
        flex_basis=rx.cond(weight > 15, "40%", rx.cond(weight > 5, "20%", "10%")),
    )


def _heatmap_grid() -> rx.Component:
    """Weighted heatmap — block sizes reflect portfolio weight."""
    return card(
        rx.vstack(
            rx.text(t("chart.performance_heatmap"), size="3", weight="medium"),
            rx.box(
                rx.foreach(
                    TableStateTotal.heatmap_data,
                    _heatmap_cell,
                ),
                display="flex",
                flex_wrap="wrap",
                gap="0.4rem",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
    )


def securities_charts() -> rx.Component:
    """Combined chart view for the securities page."""
    return rx.vstack(
        _allocation_pie_chart(),
        _heatmap_grid(),
        spacing="5",
        width="100%",
    )
