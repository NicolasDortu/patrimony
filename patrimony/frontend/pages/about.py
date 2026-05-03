"""The about page."""

import reflex as rx

from ..components.card import card
from ..templates import template, t
from ..utils import tauri_open_url


_FEATURES = [
    ("bar-chart-3", "page.about.feature_track"),
    ("file-spreadsheet", "page.about.feature_import"),
    ("trending-up", "page.about.feature_charts"),
    ("coins", "page.about.feature_multi_currency"),
    ("languages", "page.about.feature_i18n"),
]

_GITHUB_URL = "https://github.com/NicolasDortu/patrimony"


def _feature_item(icon: str, key: str) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.icon(icon, size=20, color=rx.color("accent", 11)),
            padding="0.55rem",
            border_radius="999px",
            background=rx.color("accent", 3),
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        rx.text(t(key), size="3", weight="medium"),
        align="center",
        spacing="3",
        width="100%",
    )


def _hero() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.icon("chart_no_axes_combined", size=44, color=rx.color("accent", 11)),
            padding="1rem",
            border_radius="999px",
            background=rx.color("accent", 3),
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        rx.heading(
            t("page.about.title"),
            size="8",
            text_align="center",
        ),
        rx.text(
            t("page.about.intro"),
            size="3",
            color=rx.color("gray", 11),
            line_height="1.7",
            text_align="center",
        ),
        spacing="4",
        align="center",
        width="100%",
    )


def _features_section() -> rx.Component:
    return card(
        rx.vstack(
            rx.heading(
                t("page.about.features_title"),
                size="5",
                text_align="center",
            ),
            rx.vstack(
                *[_feature_item(icon, key) for icon, key in _FEATURES],
                spacing="3",
                width="100%",
                align="start",
            ),
            spacing="4",
            width="100%",
            align="center",
        ),
    )


def _github_section() -> rx.Component:
    return card(
        rx.vstack(
            rx.hstack(
                rx.icon("github", size=22),
                rx.heading(t("page.about.github_title"), size="5"),
                align="center",
                spacing="2",
            ),
            rx.text(
                t("page.about.github_desc"),
                size="3",
                color=rx.color("gray", 11),
                text_align="center",
                line_height="1.6",
            ),
            rx.button(
                rx.icon("external-link", size=16),
                t("page.about.github_link"),
                size="3",
                variant="solid",
                on_click=tauri_open_url(_GITHUB_URL),
            ),
            spacing="4",
            align="center",
            width="100%",
        ),
    )


@template(route="/about", title="About")
def about() -> rx.Component:
    """The about page."""
    return rx.center(
        rx.vstack(
            _hero(),
            _features_section(),
            _github_section(),
            spacing="6",
            align="center",
            width="100%",
            max_width="640px",
            padding_y="2rem",
        ),
        width="100%",
    )
