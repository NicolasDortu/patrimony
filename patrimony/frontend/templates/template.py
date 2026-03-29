"""Common templates used between pages in the app."""

from __future__ import annotations

import json
from typing import Callable

import reflex as rx

from ..services import CurrencyService
from ..languages import load_translations
from ..styles import styles
from ..components.navigation import navbar, sidebar
from ..utils import get_settings_path

# Meta tags for the app.
default_meta = [
    {
        "name": "viewport",
        "content": "width=device-width, shrink-to-fit=no, initial-scale=1",
    },
]


def menu_item_link(text, href):
    return rx.menu.item(
        rx.link(
            text,
            href=href,
            width="100%",
            color="inherit",
        ),
        _hover={
            "color": styles.accent_color,
            "background_color": styles.accent_text_color,
        },
    )


class ThemeState(rx.State):
    """The state for the theme of the app."""

    accent_color: str = "crimson"

    gray_color: str = "gray"

    radius: str = "large"

    scaling: str = "100%"

    default_currency: str = "EUR"

    # Language
    language: str = "en"

    # Translations dict loaded from JSON files
    translations: dict[str, str] = {}

    # Asset type colors (Radix color names)
    stock_color: str = "purple"
    etf_color: str = "orange"
    crypto_color: str = "yellow"
    commodity_color: str = "red"
    cash_color: str = "green"
    all_color: str = "blue"

    @rx.var
    def currency_symbol(self) -> str:
        """Get the display symbol for the selected currency."""
        return CurrencyService.get_currency_symbol(self.default_currency)

    # Fields persisted to settings.json
    _SETTINGS_FIELDS: list[str] = [
        "accent_color",
        "gray_color",
        "radius",
        "scaling",
        "default_currency",
        "language",
        "stock_color",
        "etf_color",
        "crypto_color",
        "commodity_color",
        "cash_color",
        "all_color",
    ]

    def _save(self) -> None:
        """Persist current settings to JSON."""
        data = {field: getattr(self, field) for field in self._SETTINGS_FIELDS}
        get_settings_path().write_text(json.dumps(data, indent=2))

    def _set_and_save(self, field: str, value: str) -> None:
        """Set a single field and persist."""
        setattr(self, field, value)
        self._save()

    @rx.event
    def load_settings(self) -> None:
        """Load settings from JSON file on app start."""
        path = get_settings_path()
        if path.exists():
            data = json.loads(path.read_text())
            for field in self._SETTINGS_FIELDS:
                setattr(self, field, data.get(field, getattr(self, field)))
        self.translations = load_translations(self.language)

    @rx.event
    def set_scaling(self, value: str):
        self._set_and_save("scaling", value)

    @rx.event
    def set_radius(self, value: str):
        self._set_and_save("radius", value)

    @rx.event
    def set_accent_color(self, value: str):
        self._set_and_save("accent_color", value)

    @rx.event
    def set_gray_color(self, value: str):
        self._set_and_save("gray_color", value)

    @rx.event
    def set_default_currency(self, value: str):
        self._set_and_save("default_currency", value)

    @rx.event
    def set_stock_color(self, value: str):
        self._set_and_save("stock_color", value)

    @rx.event
    def set_etf_color(self, value: str):
        self._set_and_save("etf_color", value)

    @rx.event
    def set_crypto_color(self, value: str):
        self._set_and_save("crypto_color", value)

    @rx.event
    def set_commodity_color(self, value: str):
        self._set_and_save("commodity_color", value)

    @rx.event
    def set_language(self, value: str):
        self.language = value
        self.translations = load_translations(value)
        self._save()

    @rx.event
    def set_cash_color(self, value: str):
        self._set_and_save("cash_color", value)

    @rx.event
    def set_all_color(self, value: str):
        self._set_and_save("all_color", value)


def t(key: str):
    """Shorthand for ThemeState.translations[key]."""
    return ThemeState.translations[key]


ALL_PAGES = []


def template(
    route: str | None = None,
    title: str | None = None,
    description: str | None = None,
    meta: str | None = None,
    script_tags: list[rx.Component] | None = None,
    on_load: rx.event.EventType[()] | None = None,
) -> Callable[[Callable[[], rx.Component]], rx.Component]:
    """The template for each page of the app.

    Args:
        route: The route to reach the page.
        title: The title of the page.
        description: The description of the page.
        meta: Additional meta to add to the page.
        on_load: The event handler(s) called when the page load.
        script_tags: Scripts to attach to the page.

    Returns:
        The template with the page content.

    """

    def decorator(page_content: Callable[[], rx.Component]) -> rx.Component:
        """The template for each page of the app.

        Args:
            page_content: The content of the page.

        Returns:
            The template with the page content.

        """
        # Get the meta tags for the page.
        all_meta = [*default_meta, *(meta or [])]

        def templated_page():
            return rx.flex(
                navbar(),
                sidebar(),
                rx.flex(
                    rx.vstack(
                        page_content(),
                        width="100%",
                        **styles.template_content_style,
                    ),
                    width="100%",
                    **styles.template_page_style,
                    max_width=[
                        "100%",
                        "100%",
                        "100%",
                        "100%",
                        "100%",
                        styles.max_width,
                    ],
                ),
                flex_direction=[
                    "column",
                    "column",
                    "column",
                    "column",
                    "column",
                    "row",
                ],
                width="100%",
                margin="auto",
                position="relative",
            )

        # Always load theme settings alongside any page-specific on_load.
        if on_load is not None:
            combined_on_load = (
                [ThemeState.load_settings, on_load]
                if not isinstance(on_load, list)
                else [ThemeState.load_settings, *on_load]
            )
        else:
            combined_on_load = ThemeState.load_settings

        @rx.page(
            route=route,
            title=title,
            description=description,
            meta=all_meta,
            script_tags=script_tags,
            on_load=combined_on_load,
        )
        def theme_wrap():
            return rx.theme(
                templated_page(),
                has_background=True,
                accent_color=ThemeState.accent_color,
                gray_color=ThemeState.gray_color,
                radius=ThemeState.radius,
                scaling=ThemeState.scaling,
            )

        ALL_PAGES.append(
            {
                "route": route,
            }
            | ({"title": title} if title is not None else {})
        )

        return theme_wrap

    return decorator
