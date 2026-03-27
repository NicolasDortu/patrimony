import reflex as rx

from ..services import Currency
from ..templates import t


def open_add_cash_dialog(on_submit: callable) -> rx.Component:
    """Button to open a dialog to add a new cash entry."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=26),
                rx.text(t("dialog.add_cash.submit"), size="4"),
                size="3",
                variant="surface",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title(t("dialog.add_cash.title")),
            rx.dialog.description(
                t("dialog.add_cash.desc"),
            ),
            rx.form(
                rx.flex(
                    rx.input(
                        placeholder=t("label.bank_name"),
                        name="bank",
                        required=True,
                    ),
                    rx.input(
                        placeholder=t("label.account_number"),
                        name="account_number",
                        required=True,
                    ),
                    rx.select(
                        [currency.value for currency in Currency],
                        placeholder=t("label.currency"),
                        name="currency",
                        default_value="EUR",
                        required=True,
                    ),
                    rx.input(
                        placeholder=t("label.balance"),
                        name="balance",
                        type="number",
                        min="0",
                        step="0.01",
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
                                t("dialog.add_cash.submit"),
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
