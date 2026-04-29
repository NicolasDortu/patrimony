import reflex as rx

from .common import header_cell, table_row, table_toolbar
from .pagination import pagination_view
from ...states.properties_state import PropertiesState
from ...dialogs.property_dialog import open_add_property_dialog
from ...templates import t


def _show_item(item: dict, index: int) -> rx.Component:
    return table_row(
        rx.table.cell(item["name"]),
        rx.table.cell(item.get("description", "")),
        rx.table.cell(f"{item['value']:.2f}"),
        rx.table.cell(item.get("category", "Other")),
        rx.table.cell(item.get("currency", "EUR")),
        rx.table.cell(item.get("purchase_date", "")),
        index=index,
    )


def properties_table() -> rx.Component:
    return rx.box(
        table_toolbar(
            PropertiesState,
            [
                (t("label.name"), "name"),
                (t("label.value"), "value"),
                (t("label.category"), "category"),
                (t("label.currency"), "currency"),
                (t("label.purchase_date"), "purchase_date"),
            ],
            add_button=open_add_property_dialog(PropertiesState.add_property),
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    header_cell(t("label.name"), "tag"),
                    header_cell(t("label.description"), "text"),
                    header_cell(t("label.value"), "dollar-sign"),
                    header_cell(t("label.category"), "folder"),
                    header_cell(t("label.currency"), "coins"),
                    header_cell(t("label.purchase_date"), "calendar"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    PropertiesState.get_current_page,
                    lambda item, index: _show_item(item, index),
                )
            ),
            variant="surface",
            size="3",
            width="100%",
        ),
        pagination_view(PropertiesState),
        width="100%",
    )
