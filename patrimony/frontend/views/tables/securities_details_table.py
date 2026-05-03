import reflex as rx

from .common import header_cell, table_row, table_toolbar
from .pagination import pagination_view
from ...states.securities_details_state import TableStateDetails
from ...services import SecurityPosition
from ...dialogs import open_add_position_dialog
from ...templates import ThemeState, t


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
            [
                (t("label.price"), "price"),
                (t("label.quantity"), "quantity"),
                (t("label.fees"), "fees"),
                (t("label.date"), "date"),
            ],
            add_button=open_add_position_dialog(TableStateDetails.add_stock),
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    header_cell(t("label.price"), "dollar-sign"),
                    header_cell(t("label.quantity"), "notebook-pen"),
                    header_cell(t("label.fees"), "receipt"),
                    header_cell(t("label.date"), "calendar"),
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
