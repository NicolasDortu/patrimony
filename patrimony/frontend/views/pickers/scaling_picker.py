import reflex as rx

from ...templates import t
from ...templates.template import ThemeState


def scaling_picker() -> rx.Component:
    return (
        rx.vstack(
            rx.hstack(
                rx.icon("ruler", color=rx.color("accent", 10)),
                rx.heading(t("settings.scaling"), size="6"),
                align="center",
            ),
            rx.select(
                [
                    "90%",
                    "95%",
                    "100%",
                    "105%",
                    "110%",
                ],
                size="3",
                value=ThemeState.scaling,
                on_change=ThemeState.set_scaling,
            ),
            width="100%",
        ),
    )
