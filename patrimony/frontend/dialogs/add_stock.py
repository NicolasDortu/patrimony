import reflex as rx

from ..states.table_stock_state import TableState


def open_add_stock_dialog() -> rx.Component:
    """Button to open a dialog to add a new stock position."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=26),
                rx.text("Add New Position", size="4"),
                size="3",
                variant="surface",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Add New Position"),
            rx.dialog.description(
                "Enter the details for your new stock position.",
            ),
            rx.form(
                rx.flex(
                    rx.input(
                        placeholder="Ticker (e.g., GOOG)",
                        name="ticker",
                        required=True,
                    ),
                    rx.input(
                        placeholder="Buy Price ($)",
                        name="price",
                        type="number",
                        min="0.01",
                        step="0.01",
                        required=True,
                    ),
                    rx.input(
                        placeholder="Quantity",
                        name="quantity",
                        type="number",
                        min="1",
                        step="1",
                        required=True,
                    ),
                    # TODO: add dropdown for currency
                    rx.flex(
                        rx.dialog.close(
                            rx.button(
                                "Cancel",
                                variant="soft",
                                color_scheme="gray",
                            ),
                        ),
                        rx.dialog.close(
                            rx.button("Add Position", type="submit"),
                        ),
                        spacing="3",
                        justify="end",
                    ),
                    direction="column",
                    spacing="4",
                ),
                on_submit=TableState.add_stock,
                reset_on_submit=True,
            ),
            max_width="450px",
        ),
    )
