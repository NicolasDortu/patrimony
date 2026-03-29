"""Reusable loading spinner component."""

import reflex as rx

from ..templates import t


def loading_spinner() -> rx.Component:
    """Loading spinner shown while data is being fetched."""
    return rx.center(
        rx.vstack(
            rx.spinner(size="3"),
            rx.text(
                t("page.overview.loading"),
                size="3",
                color=rx.color("gray", 10),
            ),
            align="center",
            spacing="3",
        ),
        width="100%",
        min_height="60vh",
    )
