import reflex as rx

from .common import header_cell, table_row
from .pagination import pagination_view
from .spreadsheet_view import spreadsheet_toggle_button
from ...states.properties_state import PropertiesState
from ...dialogs.property_dialog import open_add_property_dialog
from ...templates import ThemeState


def _show_item(item: dict, index: int) -> rx.Component:
    return table_row(
        rx.table.cell(item["name"]),
        rx.table.cell(item.get("description", "")),
        rx.table.cell(ThemeState.currency_symbol + f"{item['value']:.2f}"),
        rx.table.cell(item.get("category", "Other")),
        rx.table.cell(item.get("purchase_date", "")),
        index=index,
    )


def properties_table() -> rx.Component:
    return rx.box(
        rx.flex(
            rx.flex(
                open_add_property_dialog(PropertiesState.add_property),
                spreadsheet_toggle_button(PropertiesState),
                rx.icon_button(
                    rx.icon("arrow-down-to-line", size=20),
                    variant="surface",
                    size="3",
                    on_click=PropertiesState.export_csv,
                ),
                align="center",
                spacing="3",
            ),
            rx.flex(
                rx.cond(
                    PropertiesState.sort_reverse,
                    rx.icon(
                        "arrow-down-z-a",
                        size=28,
                        stroke_width=1.5,
                        cursor="pointer",
                        flex_shrink="0",
                        on_click=PropertiesState.toggle_sort,
                    ),
                    rx.icon(
                        "arrow-down-a-z",
                        size=28,
                        stroke_width=1.5,
                        cursor="pointer",
                        flex_shrink="0",
                        on_click=PropertiesState.toggle_sort,
                    ),
                ),
                rx.select(
                    ["name", "value", "category", "purchase_date"],
                    placeholder="Sort By: name",
                    size="3",
                    on_change=PropertiesState.set_sort_value,
                ),
                rx.input(
                    rx.input.slot(rx.icon("search")),
                    rx.input.slot(
                        rx.icon("x"),
                        justify="end",
                        cursor="pointer",
                        on_click=PropertiesState.set_search_value(""),
                        display=rx.cond(PropertiesState.search_value, "flex", "none"),
                    ),
                    value=PropertiesState.search_value,
                    placeholder="Search here...",
                    size="3",
                    max_width=["150px", "150px", "200px", "250px"],
                    width="100%",
                    variant="surface",
                    color_scheme="gray",
                    on_change=PropertiesState.set_search_value,
                ),
                align="center",
                justify="end",
                spacing="3",
            ),
            spacing="3",
            justify="between",
            wrap="wrap",
            width="100%",
            padding_bottom="1em",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    header_cell("name", "tag"),
                    header_cell("description", "text"),
                    header_cell("value", "dollar-sign"),
                    header_cell("category", "folder"),
                    header_cell("purchase_date", "calendar"),
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
