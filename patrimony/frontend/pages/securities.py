"""The table page."""

import reflex as rx

from ..states.securities_total_state import TableStateTotal
from ..templates import template, t
from ..views.charts.securities_charts import securities_charts
from ..views.tables.securities_total_table import main_table
from ..views.tables.spreadsheet_view import spreadsheet_or_table


def _asset_type_filter() -> rx.Component:
    """Segmented control for filtering by asset type."""
    return rx.segmented_control.root(
        rx.foreach(
            TableStateTotal.available_asset_filters,
            lambda f: rx.segmented_control.item(f["label"], value=f["value"]),
        ),
        default_value="all",
        value=TableStateTotal.selected_asset_filter,
        on_change=TableStateTotal.set_asset_filter,
    )


@template(route="/securities", title="Securities", on_load=TableStateTotal.load_entries)
def securities() -> rx.Component:
    """The securities page."""
    return rx.vstack(
        rx.hstack(
            rx.heading(t("page.securities.title"), size="5"),
            _asset_type_filter(),
            rx.spacer(),
            rx.button(
                rx.cond(
                    TableStateTotal.chart_view,
                    rx.icon("table", size=16),
                    rx.icon("bar-chart-3", size=16),
                ),
                rx.cond(
                    TableStateTotal.chart_view,
                    t("btn.table_view"),
                    t("btn.chart_view"),
                ),
                variant="ghost",
                size="2",
                on_click=TableStateTotal.toggle_chart_view,
                cursor="pointer",
            ),
            justify="between",
            align="center",
            width="100%",
        ),
        rx.cond(
            TableStateTotal.chart_view,
            securities_charts(),
            spreadsheet_or_table(TableStateTotal, main_table()),
        ),
        spacing="5",
        width="100%",
    )
