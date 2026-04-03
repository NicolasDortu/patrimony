import reflex as rx

from ..states.properties_state import PROPERTY_CATEGORIES
from ..templates import t


def open_add_property_dialog(on_submit: callable) -> rx.Component:
    """Button to open a dialog to add a new property."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=26),
                rx.text(t("dialog.add_property.submit"), size="4"),
                size="3",
                variant="surface",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title(t("dialog.add_property.title")),
            rx.dialog.description(
                t("dialog.add_property.desc"),
            ),
            rx.form(
                rx.flex(
                    rx.input(
                        placeholder=t("label.name"),
                        name="name",
                        required=True,
                    ),
                    rx.input(
                        placeholder=t("label.description"),
                        name="description",
                    ),
                    rx.input(
                        placeholder=t("label.value"),
                        name="value",
                        type="number",
                        min="0.01",
                        step="0.01",
                        required=True,
                    ),
                    rx.select(
                        PROPERTY_CATEGORIES,
                        placeholder=t("label.category"),
                        name="category",
                        default_value="Other",
                    ),
                    rx.input(
                        placeholder=t("label.purchase_date"),
                        name="purchase_date",
                        type="date",
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
                                t("dialog.add_property.submit"),
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
