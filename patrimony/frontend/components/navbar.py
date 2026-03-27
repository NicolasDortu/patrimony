"""Navbar component for the app."""

import reflex as rx

from ..styles import styles

# Navigation items: (route, translation_key, icon)
_NAV_ITEMS = [
    ("/", "nav.overview", "home"),
    ("/securities", "nav.securities", "table-2"),
    ("/cash", "nav.cash", "wallet"),
    ("/connectors", "nav.connectors", "plug"),
    ("/settings", "nav.settings", "settings"),
]


def menu_item(text, icon: str, url: str) -> rx.Component:
    """Menu item with translated text and explicit icon."""
    active = rx.State.router.page.path == url

    return rx.link(
        rx.hstack(
            rx.icon(icon, size=20),
            rx.text(text, size="4", weight="regular"),
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


def navbar_footer() -> rx.Component:
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


def menu_button() -> rx.Component:
    from ..templates import t

    return rx.drawer.root(
        rx.drawer.trigger(
            rx.icon("align-justify"),
        ),
        rx.drawer.overlay(z_index="5"),
        rx.drawer.portal(
            rx.drawer.content(
                rx.vstack(
                    rx.hstack(
                        rx.spacer(),
                        rx.drawer.close(rx.icon(tag="x")),
                        justify="end",
                        width="100%",
                    ),
                    rx.divider(),
                    *[
                        menu_item(
                            text=t(key),
                            icon=icon,
                            url=route,
                        )
                        for route, key, icon in _NAV_ITEMS
                    ],
                    rx.spacer(),
                    navbar_footer(),
                    spacing="4",
                    width="100%",
                ),
                top="auto",
                left="auto",
                height="100%",
                width="20em",
                padding="1em",
                bg=rx.color("gray", 1),
            ),
            width="100%",
        ),
        direction="right",
    )


def navbar() -> rx.Component:
    return rx.el.nav(
        rx.hstack(
            rx.color_mode_cond(
                rx.image(src="/patrimony_black.svg", height="2em"),
                rx.image(src="/patrimony_white.svg", height="2em"),
            ),
            rx.spacer(),
            menu_button(),
            align="center",
            width="100%",
            padding_y="1.25em",
            padding_x=["1em", "1em", "2em"],
        ),
        display=["block", "block", "block", "block", "block", "none"],
        position="sticky",
        background_color=rx.color("gray", 1),
        top="0px",
        z_index="5",
        border_bottom=styles.border,
    )
