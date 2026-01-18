import reflex as rx

from ..states.table_stock_state import TableState


def open_delete_stock_dialog() -> rx.Component:
    """Button to open a dialog to delete a stock position."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("trash", size=26),
                rx.text("Delete Position", size="4"),
                size="3",
                variant="surface",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Delete Position"),
            rx.dialog.description(
                "Enter the id for the position you want to delete.",
            ),
            rx.form(
                rx.flex(
                    rx.input(
                        placeholder="ID (e.g., 123)",
                        name="id",
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
                            rx.button("Delete Position", type="submit"),
                        ),
                        spacing="3",
                        justify="end",
                    ),
                    direction="column",
                    spacing="4",
                ),
                on_submit=TableState.delete_stock,
                reset_on_submit=True,
            ),
            max_width="450px",
        ),
    )
