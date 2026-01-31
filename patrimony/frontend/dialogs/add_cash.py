import reflex as rx

from ...shared.models.assets import Currency


def open_add_cash_dialog(on_submit: callable) -> rx.Component:
    """Button to open a dialog to add a new cash entry."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=26),
                rx.text("Add Cash", size="4"),
                size="3",
                variant="surface",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Add Cash Entry"),
            rx.dialog.description(
                "Enter the details for your new cash entry.",
            ),
            rx.form(
                rx.flex(
                    rx.input(
                        placeholder="Bank Name",
                        name="bank",
                        required=True,
                    ),
                    rx.input(
                        placeholder="Account Number",
                        name="account_number",
                        required=True,
                    ),
                    rx.select(
                        [currency.value for currency in Currency],
                        placeholder="Currency",
                        name="currency",
                        default_value="EUR",
                        required=True,
                    ),
                    rx.input(
                        placeholder="Balance",
                        name="balance",
                        type="number",
                        min="0",
                        step="0.01",
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
                            rx.button("Add Cash", type="submit"),
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
