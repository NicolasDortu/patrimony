import reflex as rx

from .common import header_cell
from .pagination import pagination_view
from ...states.cash_state import CashTableState
from ...dialogs.cash_dialog import open_add_cash_dialog
from ...templates import t


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
        rx.table.cell(item["bank"]),
        rx.table.cell(item["account_number"]),
        rx.table.cell(item["currency"]),
        rx.table.cell(f"{item['balance']:.2f}"),
        rx.table.cell(
            rx.hstack(
                rx.dialog.root(
                    rx.dialog.trigger(
                        rx.icon_button(
                            rx.icon("pencil", size=18),
                            variant="ghost",
                            color_scheme="blue",
                            on_click=lambda: CashTableState.open_edit_dialog(item),
                        ),
                    ),
                    rx.dialog.content(
                        rx.dialog.title(t("dialog.edit_cash.title")),
                        rx.dialog.description(
                            t("dialog.edit_cash.desc"),
                        ),
                        rx.form(
                            rx.flex(
                                rx.input(
                                    placeholder=t("label.bank_name"),
                                    name="bank",
                                    default_value=CashTableState.edit_bank,
                                    required=True,
                                ),
                                rx.input(
                                    placeholder=t("label.account_number"),
                                    name="account_number",
                                    default_value=CashTableState.edit_account_number,
                                    required=True,
                                ),
                                rx.select(
                                    [
                                        "EUR",
                                        "USD",
                                        "GBP",
                                        "JPY",
                                    ],  # TODO: make it dynamic based on available currencies
                                    placeholder=t("label.currency"),
                                    name="currency",
                                    default_value=CashTableState.edit_currency,
                                    required=True,
                                ),
                                rx.flex(
                                    rx.dialog.close(
                                        rx.button(
                                            t("btn.cancel"),
                                            variant="soft",
                                            color_scheme="gray",
                                        ),
                                    ),
                                    rx.dialog.close(
                                        rx.button(
                                            t("btn.save"),
                                            type="submit",
                                        ),
                                    ),
                                    spacing="3",
                                    justify="end",
                                ),
                                direction="column",
                                spacing="4",
                            ),
                            on_submit=CashTableState.update_cash_entry,
                            reset_on_submit=False,
                        ),
                        max_width="450px",
                    ),
                ),
                rx.icon_button(
                    rx.icon("arrow_right_to_line", size=18),
                    variant="ghost",
                    on_click=lambda: CashTableState.open_operations_view(
                        item["account_number"], item["currency"]
                    ),
                ),
                rx.alert_dialog.root(
                    rx.alert_dialog.trigger(
                        rx.icon_button(
                            rx.icon("trash-2", size=18),
                            variant="ghost",
                            color_scheme="red",
                        ),
                    ),
                    rx.alert_dialog.content(
                        rx.alert_dialog.title(t("dialog.delete_cash.title")),
                        rx.alert_dialog.description(
                            t("dialog.delete_cash.desc"),
                        ),
                        rx.flex(
                            rx.alert_dialog.cancel(
                                rx.button(
                                    t("btn.cancel"),
                                    variant="soft",
                                    color_scheme="gray",
                                ),
                            ),
                            rx.alert_dialog.action(
                                rx.button(
                                    t("btn.delete"),
                                    color_scheme="red",
                                    on_click=lambda: CashTableState.delete_cash_entry(
                                        item
                                    ),
                                ),
                            ),
                            spacing="3",
                            justify="end",
                        ),
                    ),
                ),
                spacing="2",
            )
        ),
        style={"_hover": {"bg": hover_color}, "bg": bg_color},
        align="center",
    )


def cash_table() -> rx.Component:
    """Main cash table component."""
    return rx.box(
        rx.flex(
            open_add_cash_dialog(CashTableState.add_cash_entry),
            align="center",
            justify="start",
            spacing="4",
            padding_bottom="1.5em",
        ),
        rx.flex(
            rx.flex(
                rx.cond(
                    CashTableState.sort_reverse,
                    rx.icon(
                        "arrow-down-z-a",
                        size=28,
                        stroke_width=1.5,
                        cursor="pointer",
                        flex_shrink="0",
                        on_click=CashTableState.toggle_sort,
                    ),
                    rx.icon(
                        "arrow-down-a-z",
                        size=28,
                        stroke_width=1.5,
                        cursor="pointer",
                        flex_shrink="0",
                        on_click=CashTableState.toggle_sort,
                    ),
                ),
                rx.select(
                    ["bank", "account_number", "currency", "balance"],
                    placeholder="Sort By: bank",
                    size="3",
                    on_change=CashTableState.set_sort_value,
                ),
                rx.input(
                    rx.input.slot(rx.icon("search")),
                    rx.input.slot(
                        rx.icon("x"),
                        justify="end",
                        cursor="pointer",
                        on_click=CashTableState.set_search_value(""),
                        display=rx.cond(CashTableState.search_value, "flex", "none"),
                    ),
                    value=CashTableState.search_value,
                    placeholder="Search here...",
                    size="3",
                    max_width=["150px", "150px", "200px", "250px"],
                    width="100%",
                    variant="surface",
                    color_scheme="gray",
                    on_change=CashTableState.set_search_value,
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
                    header_cell("Bank", "landmark"),
                    header_cell("Account Number", "hash"),
                    header_cell("Currency", "badge-euro"),
                    header_cell("Balance", "wallet"),
                    header_cell("Actions", "settings"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    CashTableState.get_current_page,
                    lambda item, index: _show_item(item, index),
                )
            ),
            variant="surface",
            size="3",
            width="100%",
        ),
        pagination_view(CashTableState),
        width="100%",
    )
