from datetime import datetime

import reflex as rx


def open_add_operation_dialog(on_submit: callable) -> rx.Component:
    """Button to open a dialog to add a new cash operation (deposit/expense)."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=26),
                rx.text("Add Operation", size="4"),
                size="3",
                variant="surface",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Add Cash Operation"),
            rx.dialog.description("Enter the details for the deposit or expense."),
            rx.form(
                rx.flex(
                    rx.input(
                        placeholder="Title (e.g., Salary, Rent)",
                        name="title",
                        required=True,
                    ),
                    rx.input(
                        placeholder="Amount (positive=deposit, negative=expense)",
                        name="amount",
                        type="number",
                        step="0.01",
                        required=True,
                    ),
                    rx.input(
                        placeholder="Operation Date",
                        name="operation_date",
                        type="date",
                        default_value=datetime.now().date().isoformat(),
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
                            rx.button("Add Operation", type="submit"),
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
