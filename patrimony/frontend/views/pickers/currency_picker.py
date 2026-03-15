import reflex as rx

from ...services import Currency
from ...templates.template import ThemeState


def currency_picker() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon("banknote", color=rx.color("accent", 10)),
            rx.heading("Default currency", size="6"),
            align="center",
        ),
        rx.select.root(
            rx.select.trigger(),
            rx.select.content(
                *[rx.select.item(c.label, value=c.value) for c in Currency],
            ),
            size="3",
            value=ThemeState.default_currency,
            on_change=ThemeState.set_default_currency,
        ),
        spacing="4",
        width="100%",
    )
