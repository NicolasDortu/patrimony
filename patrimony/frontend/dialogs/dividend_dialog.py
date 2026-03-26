import reflex as rx

from ..states.dividends_state import DividendsState


def open_add_dividend_dialog() -> rx.Component:
    """Button to open a dialog to add a new dividend."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=26),
                rx.text("Add Dividend", size="4"),
                size="3",
                variant="surface",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Add Dividend"),
            rx.dialog.description(
                "Record a dividend payment received.",
            ),
            rx.form(
                rx.flex(
                    rx.input(
                        placeholder="Amount ($)",
                        name="amount",
                        type="number",
                        min="0.01",
                        step="0.01",
                        required=True,
                    ),
                    rx.input(
                        placeholder="Date (YYYY-MM-DD)",
                        name="date",
                        type="date",
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
                            rx.button("Add Dividend", type="submit"),
                        ),
                        spacing="3",
                        justify="end",
                    ),
                    direction="column",
                    spacing="4",
                ),
                on_submit=DividendsState.add_dividend,
                reset_on_submit=True,
            ),
            max_width="450px",
        ),
    )
