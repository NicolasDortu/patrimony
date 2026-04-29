"""The table page."""

import reflex as rx

from ..components.chart_toggle import chart_table_toggle
from ..components.empty_table import empty_table
from ..components.loading import loading_spinner
from ..dialogs import open_add_position_dialog
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


@template(route="/securities", title="Securities", on_load=TableStateTotal.on_page_load)
def securities() -> rx.Component:
    """The securities page."""
    return rx.vstack(
        rx.hstack(
            rx.heading(t("page.securities.title"), size="5"),
            _asset_type_filter(),
            rx.spacer(),
            rx.cond(
                TableStateTotal.total_items > 0,
                chart_table_toggle(TableStateTotal),
            ),
            justify="between",
            align="center",
            width="100%",
        ),
        rx.cond(
            TableStateTotal.is_loading,
            loading_spinner(),
            rx.cond(
                TableStateTotal.total_items > 0,
                rx.cond(
                    TableStateTotal.chart_view,
                    securities_charts(),
                    spreadsheet_or_table(TableStateTotal, main_table()),
                ),
                empty_table(
                    "empty.securities",
                    "briefcase",
                    open_add_position_dialog(TableStateTotal.add_stock),
                ),
            ),
        ),
        spacing="5",
        width="100%",
        on_unmount=TableStateTotal.set_chart_view(False),
    )
