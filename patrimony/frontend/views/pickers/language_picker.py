import reflex as rx

from ...languages import AVAILABLE_LANGUAGES
from ...templates import ThemeState, t


def language_picker() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon("languages", color=rx.color("accent", 10)),
            rx.heading(t("settings.language"), size="6"),
            align="center",
        ),
        rx.text(
            t("settings.language_desc"),
            size="2",
            color_scheme="gray",
        ),
        rx.select.root(
            rx.select.trigger(),
            rx.select.content(
                *[
                    rx.select.item(label, value=code)
                    for code, label in AVAILABLE_LANGUAGES.items()
                ],
            ),
            size="3",
            value=ThemeState.language,
            on_change=ThemeState.set_language,
        ),
        spacing="4",
        width="100%",
    )
