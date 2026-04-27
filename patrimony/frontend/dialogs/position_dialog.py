from datetime import date

import reflex as rx

from ..states.securities_total_state import TableStateTotal
from ..templates import t


def _suggestion_item(item: dict) -> rx.Component:
    """Single suggestion row in the autocomplete dropdown."""
    return rx.box(
        rx.hstack(
            rx.text(item["ticker"], weight="bold", size="2"),
            rx.text(item["name"], size="2", color=rx.color("gray", 11)),
            rx.badge(item["asset_type"], size="1"),
            spacing="2",
            align="center",
        ),
        padding="8px",
        cursor="pointer",
        _hover={"bg": rx.color("accent", 3)},
        on_click=TableStateTotal.select_suggestion(item["ticker"], item["asset_type"]),
        width="100%",
    )


def open_add_position_dialog(on_submit: callable) -> rx.Component:
    """Button to open a dialog to add a new position."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=26),
                rx.text(t("dialog.add_position.title"), size="4"),
                size="3",
                variant="surface",
                on_click=TableStateTotal.clear_ticker_search,
            ),
        ),
        rx.dialog.content(
            rx.dialog.title(t("dialog.add_position.title")),
            rx.dialog.description(
                t("dialog.add_position.desc"),
            ),
            rx.form(
                rx.flex(
                    # Ticker search with autocomplete
                    rx.vstack(
                        rx.text(t("label.ticker"), size="1", weight="medium"),
                        rx.box(
                            rx.input(
                                placeholder="AAPL or Apple",
                                value=TableStateTotal.ticker_search,
                                on_change=TableStateTotal.search_ticker,
                                name="ticker",
                                required=True,
                            ),
                            rx.cond(
                                TableStateTotal.show_suggestions,
                                rx.card(
                                    rx.foreach(
                                        TableStateTotal.ticker_suggestions,
                                        _suggestion_item,
                                    ),
                                    position="absolute",
                                    z_index="10",
                                    width="100%",
                                    max_height="200px",
                                    overflow_y="auto",
                                ),
                            ),
                            position="relative",
                            width="100%",
                        ),
                        spacing="1",
                        align="stretch",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text(t("label.asset_type"), size="1", weight="medium"),
                        rx.select(
                            ["STOCK", "ETF", "CRYPTO", "COMMODITY"],
                            value=TableStateTotal.selected_asset_type,
                            on_change=TableStateTotal.set_selected_asset_type,
                            name="asset_type",
                        ),
                        spacing="1",
                        align="stretch",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text(t("label.price"), size="1", weight="medium"),
                        rx.input(
                            placeholder=t("label.price"),
                            name="price",
                            type="number",
                            min="0.01",
                            step="0.01",
                            required=True,
                        ),
                        spacing="1",
                        align="stretch",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text(t("label.quantity"), size="1", weight="medium"),
                        rx.input(
                            placeholder=t("label.quantity"),
                            name="quantity",
                            type="number",
                            min="0.0001",
                            step="0.0001",
                            required=True,
                        ),
                        spacing="1",
                        align="stretch",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text(t("label.fees"), size="1", weight="medium"),
                        rx.input(
                            placeholder=t("label.fees"),
                            name="fees",
                            type="number",
                            min="0",
                            step="0.01",
                        ),
                        spacing="1",
                        align="stretch",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.text(t("label.purchase_date"), size="1", weight="medium"),
                        rx.input(
                            type="date",
                            name="date",
                            default_value=date.today().isoformat(),
                            max=date.today().isoformat(),
                        ),
                        spacing="1",
                        align="stretch",
                        width="100%",
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button(
                                t("btn.cancel"),
                                type="button",
                                variant="soft",
                                color_scheme="gray",
                                on_click=TableStateTotal.clear_ticker_search,
                            ),
                        ),
                        rx.dialog.close(
                            rx.button(
                                t("dialog.add_position.submit"),
                                type="submit",
                            ),
                        ),
                        spacing="3",
                        justify="end",
                    ),
                    direction="column",
                    spacing="4",
                ),
                on_submit=on_submit,
                reset_on_submit=True,
            ),
            max_width="450px",
        ),
    )
