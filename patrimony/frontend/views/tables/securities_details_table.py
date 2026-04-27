import reflex as rx

from .common import header_cell, table_row, table_toolbar
from .pagination import pagination_view
from ...states.securities_details_state import TableStateDetails
from ...services import SecurityPosition
from ...dialogs import open_add_position_dialog
from ...templates import ThemeState


def _show_item(item: SecurityPosition, index: int) -> rx.Component:
    return table_row(
        rx.table.cell(ThemeState.currency_symbol + f"{item.price:.2f}"),
        rx.table.cell(item.quantity),
        rx.table.cell(ThemeState.currency_symbol + f"{item.fees:.2f}"),
        rx.table.cell(item.date),
        index=index,
    )


def main_table() -> rx.Component:
    return rx.box(
        table_toolbar(
            TableStateDetails,
            ["price", "quantity", "fees", "date"],
            add_button=open_add_position_dialog(TableStateDetails.add_stock),
            default_sort_placeholder="Sort By: date",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    header_cell("Price", "dollar-sign"),
                    header_cell("Quantity", "notebook-pen"),
                    header_cell("Fees", "receipt"),
                    header_cell("Date", "calendar"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    TableStateDetails.get_current_page,
                    lambda item, index: _show_item(item, index),
                )
            ),
            variant="surface",
            size="3",
            width="100%",
        ),
        pagination_view(TableStateDetails),
        width="100%",
    )
