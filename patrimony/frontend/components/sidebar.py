"""Sidebar component for the app."""

import reflex as rx

from ..styles import styles

# Navigation items: (route, translation_key, icon)
_NAV_ITEMS = [
    ("/", "nav.overview", "home"),
    ("/securities", "nav.securities", "table-2"),
    ("/cash", "nav.cash_expenses", "wallet"),
    ("/connectors", "nav.connectors", "plug"),
    ("/settings", "nav.settings", "settings"),
]


def sidebar_header() -> rx.Component:
    return rx.hstack(
        rx.color_mode_cond(
            rx.image(src="/patrimony_black.svg", height="2.5em"),
            rx.image(src="/patrimony_white.svg", height="2.5em"),
        ),
        rx.spacer(),
        align="center",
        width="100%",
        padding="0.35em",
        margin_bottom="1em",
    )


def sidebar_footer() -> rx.Component:
    from ..templates import t

    return rx.hstack(
        rx.link(
            rx.text(t("nav.about"), size="3"),
            href="/about",
            color_scheme="gray",
            underline="none",
        ),
        rx.spacer(),
        rx.color_mode.button(style={"opacity": "0.8", "scale": "0.95"}),
        justify="start",
        align="center",
        width="100%",
        padding="0.35em",
    )


def sidebar_item(text, icon: str, url: str) -> rx.Component:
    """Sidebar item with translated text and explicit icon."""
    active = rx.State.router.page.path == url

    return rx.link(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(text, size="3", weight="regular"),
            color=rx.cond(
                active,
                styles.accent_text_color,
                styles.text_color,
            ),
            style={
                "_hover": {
                    "background_color": rx.cond(
                        active,
                        styles.accent_bg_color,
                        styles.gray_bg_color,
                    ),
                    "color": rx.cond(
                        active,
                        styles.accent_text_color,
                        styles.text_color,
                    ),
                    "opacity": "1",
                },
                "opacity": rx.cond(
                    active,
                    "1",
                    "0.95",
                ),
            },
            align="center",
            border_radius=styles.border_radius,
            width="100%",
            spacing="2",
            padding="0.35em",
        ),
        underline="none",
        href=url,
        width="100%",
    )


def sidebar() -> rx.Component:
    """The sidebar."""
    from ..templates import t

    return rx.flex(
        rx.vstack(
            sidebar_header(),
            rx.vstack(
                *[
                    sidebar_item(
                        text=t(key),
                        icon=icon,
                        url=route,
                    )
                    for route, key, icon in _NAV_ITEMS
                ],
                spacing="1",
                width="100%",
            ),
            rx.spacer(),
            sidebar_footer(),
            justify="end",
            align="end",
            width=styles.sidebar_content_width,
            height="100dvh",
            padding="1em",
        ),
        display=["none", "none", "none", "none", "none", "flex"],
        max_width=styles.sidebar_width,
        width="auto",
        height="100%",
        position="sticky",
        justify="end",
        top="0px",
        left="0px",
        flex="1",
        bg=rx.color("gray", 2),
    )
