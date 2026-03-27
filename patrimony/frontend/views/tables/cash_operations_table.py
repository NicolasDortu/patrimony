import reflex as rx

from .common import header_cell
from .pagination import pagination_view
from ...states.cash_operations_state import CashOperationsState


def _show_item(item: dict, index: int) -> rx.Component:
    bg_color = rx.cond(
        index % 2 == 0,
        rx.color("gray", 1),
        rx.color("accent", 2),
    )
    hover_color = rx.cond(
        index % 2 == 0,
        rx.color("gray", 3),
        rx.color("accent", 3),
    )
    return rx.table.row(
        rx.table.row_header_cell(item["id"]),
        rx.table.cell(item["title"]),
        rx.table.cell(
            rx.cond(
                item["amount"].to(float) >= 0,
                rx.text(item["amount"], color=rx.color("grass", 9)),
                rx.text(item["amount"], color=rx.color("red", 9)),
            )
        ),
        rx.table.cell(item["balance"]),
        rx.table.cell(item["operation_date"]),
        rx.table.cell(item["entry_type"]),
        rx.table.cell(
            rx.hstack(
                # Edit button with dialog
                rx.dialog.root(
                    rx.dialog.trigger(
                        rx.icon_button(
                            rx.icon("pencil", size=18),
                            variant="ghost",
                            color_scheme="blue",
                            on_click=lambda: CashOperationsState.open_edit_dialog(item),
                        ),
                    ),
                    rx.dialog.content(
                        rx.dialog.title("Edit Operation"),
                        rx.dialog.description(
                            "Update the details for this operation.",
                        ),
                        rx.form(
                            rx.flex(
                                rx.input(
                                    placeholder="Title",
                                    name="title",
                                    default_value=CashOperationsState.edit_title,
                                    required=True,
                                ),
                                rx.input(
                                    placeholder="Amount",
                                    name="amount",
                                    type="number",
                                    step="0.01",
                                    default_value=CashOperationsState.edit_amount.to(
                                        str
                                    ),
                                    required=True,
                                ),
                                rx.input(
                                    placeholder="Operation Date",
                                    name="operation_date",
                                    type="date",
                                    default_value=CashOperationsState.edit_operation_date,
                                    required=True,
                                ),
                                rx.flex(
                                    rx.dialog.close(
                                        rx.button(
                                            "Cancel",
                                            variant="soft",
                                            color_scheme="gray",
                                        ),
                                    ),
                                    rx.dialog.close(
                                        rx.button("Save Changes", type="submit"),
                                    ),
                                    spacing="3",
                                    justify="end",
                                ),
                                direction="column",
                                spacing="4",
                            ),
                            on_submit=CashOperationsState.update_operation,
                            reset_on_submit=False,
                        ),
                        max_width="450px",
                    ),
                ),
                # Delete button with confirmation dialog
                rx.alert_dialog.root(
                    rx.alert_dialog.trigger(
                        rx.icon_button(
                            rx.icon("trash-2", size=18),
                            variant="ghost",
                            color_scheme="red",
                        ),
                    ),
                    rx.alert_dialog.content(
                        rx.alert_dialog.title("Delete Operation"),
                        rx.alert_dialog.description(
                            "Are you sure you want to delete this operation? This action cannot be undone.",
                        ),
                        rx.flex(
                            rx.alert_dialog.cancel(
                                rx.button(
                                    "Cancel",
                                    variant="soft",
                                    color_scheme="gray",
                                ),
                            ),
                            rx.alert_dialog.action(
                                rx.button(
                                    "Delete",
                                    color_scheme="red",
                                    on_click=lambda: CashOperationsState.delete_operation(
                                        item["id"]
                                    ),
                                ),
                            ),
                            spacing="3",
                            justify="end",
                        ),
                    ),
                ),
                spacing="2",
            ),
        ),
        style={"_hover": {"bg": hover_color}, "bg": bg_color},
        align="center",
    )


def cash_operations_table() -> rx.Component:
    """Main cash operations table component."""
    return rx.box(
        rx.flex(
            rx.flex(
                rx.cond(
                    CashOperationsState.sort_reverse,
                    rx.icon(
                        "arrow-down-z-a",
                        size=28,
                        stroke_width=1.5,
                        cursor="pointer",
                        flex_shrink="0",
                        on_click=CashOperationsState.toggle_sort,
                    ),
                    rx.icon(
                        "arrow-down-a-z",
                        size=28,
                        stroke_width=1.5,
                        cursor="pointer",
                        flex_shrink="0",
                        on_click=CashOperationsState.toggle_sort,
                    ),
                ),
                rx.select(
                    [
                        "title",
                        "amount",
                        "balance",
                        "operation_date",
                    ],
                    placeholder="Sort By: operation_date",
                    size="3",
                    on_change=CashOperationsState.set_sort_value,
                ),
                rx.input(
                    rx.input.slot(rx.icon("search")),
                    rx.input.slot(
                        rx.icon("x"),
                        justify="end",
                        cursor="pointer",
                        on_click=CashOperationsState.set_search_value(""),
                        display=rx.cond(
                            CashOperationsState.search_value, "flex", "none"
                        ),
                    ),
                    value=CashOperationsState.search_value,
                    placeholder="Search here...",
                    size="3",
                    max_width=["150px", "150px", "200px", "250px"],
                    width="100%",
                    variant="surface",
                    color_scheme="gray",
                    on_change=CashOperationsState.set_search_value,
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
                    header_cell("ID", "hash"),
                    header_cell("Title", "text"),
                    header_cell("Amount", "dollar-sign"),
                    header_cell("Balance", "wallet"),
                    header_cell("Date", "calendar"),
                    header_cell("Entry Type", "tag"),
                    header_cell("Actions", "cog"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    CashOperationsState.get_current_page,
                    lambda item, index: _show_item(item, index),
                )
            ),
            variant="surface",
            size="3",
            width="100%",
        ),
        pagination_view(CashOperationsState),
        width="100%",
    )
