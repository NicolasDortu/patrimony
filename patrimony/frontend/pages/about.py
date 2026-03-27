"""The about page."""

import reflex as rx

from ..templates import template, t


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
        rx.icon(icon, size=20, color=rx.color("accent", 9)),
        rx.text(t(key), size="3"),
        align="center",
        spacing="3",
    )


@template(route="/about", title="About")
def about() -> rx.Component:
    """The about page."""
    return rx.vstack(
        rx.heading(t("page.about.title"), size="5"),
        rx.text(
            t("page.about.intro"),
            size="3",
            color=rx.color("gray", 11),
            line_height="1.8",
        ),
        rx.separator(),
        rx.heading(t("page.about.features_title"), size="4"),
        rx.vstack(
            *[_feature_item(icon, key) for icon, key in _FEATURES],
            spacing="3",
            width="100%",
        ),
        rx.separator(),
        rx.hstack(
            rx.icon("github", size=20),
            rx.heading(t("page.about.github_title"), size="4"),
            align="center",
            spacing="2",
        ),
        rx.text(
            t("page.about.github_desc"),
            size="3",
            color=rx.color("gray", 11),
        ),
        rx.link(
            rx.button(
                rx.icon("external-link", size=16),
                t("page.about.github_link"),
                size="3",
                variant="surface",
            ),
            href=_GITHUB_URL,
            is_external=True,
        ),
        spacing="5",
        width="100%",
        max_width="680px",
    )
