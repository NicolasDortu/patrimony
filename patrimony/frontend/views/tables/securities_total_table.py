import reflex as rx

from .common import header_cell, table_row, table_toolbar
from .pagination import pagination_view
from ...states.securities_total_state import TableStateTotal
from ...services import SecurityTotal
from ...dialogs import open_add_position_dialog
from ...templates import ThemeState, t


def _show_item(item: SecurityTotal, index: int) -> rx.Component:
    # Show the company name as the primary label and ticker as the
    # subtitle. Fall back to ticker as the primary if name is unknown.
    return table_row(
        rx.table.cell(
            rx.vstack(
                rx.cond(
                    item.name != "",
                    rx.text(item.name, weight="medium"),
                    rx.text(item.display_ticker, weight="medium"),
                ),
                rx.cond(
                    item.name != "",
                    rx.text(item.display_ticker, size="1", color_scheme="gray"),
                    rx.fragment(),
                ),
                spacing="0",
                align="start",
            )
        ),
        rx.table.cell(item.total_quantity),
        rx.table.cell(ThemeState.currency_symbol + f"{item.current_price:,.2f}"),
        rx.table.cell(ThemeState.currency_symbol + f"{item.total_value:,.2f}"),
        rx.table.cell(
            rx.icon_button(
                rx.icon("arrow_right_to_line", size=22),
                variant="ghost",
                on_click=lambda: TableStateTotal.open_detail_view(item.ticker),
            )
        ),
        index=index,
    )


def main_table() -> rx.Component:
    return rx.box(
        table_toolbar(
            TableStateTotal,
            [
                (t("label.company"), "ticker"),
                (t("label.quantity"), "total_quantity"),
                (t("label.current_price"), "current_price"),
                (t("label.total_value"), "total_value"),
            ],
            add_button=open_add_position_dialog(TableStateTotal.add_stock),
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    header_cell(t("label.company"), "building"),
                    header_cell(t("label.quantity"), "notebook-pen"),
                    header_cell(t("label.current_price"), "dollar-sign"),
                    header_cell(t("label.total_value"), "wallet"),
                    header_cell("", "chart_no_axes_combined"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    TableStateTotal.get_current_page,
                    lambda item, index: _show_item(item, index),
                )
            ),
            variant="surface",
            size="3",
            width="100%",
        ),
        pagination_view(TableStateTotal),
        width="100%",
    )
