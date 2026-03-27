from datetime import datetime

import reflex as rx

from ..templates import t


def open_add_operation_dialog(on_submit: callable) -> rx.Component:
    """Button to open a dialog to add a new cash operation (deposit/expense)."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=26),
                rx.text(t("dialog.add_operation.submit"), size="4"),
                size="3",
                variant="surface",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title(t("dialog.add_operation.title")),
            rx.dialog.description(t("dialog.add_operation.desc")),
            rx.form(
                rx.flex(
                    rx.input(
                        placeholder=t("label.title"),
                        name="title",
                        required=True,
                    ),
                    rx.input(
                        placeholder=t("label.amount"),
                        name="amount",
                        type="number",
                        step="0.01",
                        required=True,
                    ),
                    rx.input(
                        placeholder=t("label.date"),
                        name="operation_date",
                        type="date",
                        default_value=datetime.now().date().isoformat(),
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
                                t("dialog.add_operation.submit"),
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
