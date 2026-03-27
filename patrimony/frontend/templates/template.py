"""Common templates used between pages in the app."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

import reflex as rx

from ..services import CurrencyService
from ..languages import load_translations
from ..styles import styles
from ..components.navbar import navbar
from ..components.sidebar import sidebar

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


def _get_settings_path() -> Path:
    """Get the settings file path (same directory as the database)."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:
        base = Path.home() / ".local" / "share"
    settings_dir = base / "patrimony" / "settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir / "settings.json"


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

    @rx.var
    def currency_symbol(self) -> str:
        """Get the display symbol for the selected currency."""
        return CurrencyService.get_currency_symbol(self.default_currency)

    def _save(self) -> None:
        """Persist current settings to JSON."""
        data = {
            "accent_color": self.accent_color,
            "gray_color": self.gray_color,
            "radius": self.radius,
            "scaling": self.scaling,
            "default_currency": self.default_currency,
            "language": self.language,
            "stock_color": self.stock_color,
            "etf_color": self.etf_color,
            "crypto_color": self.crypto_color,
            "commodity_color": self.commodity_color,
            "cash_color": self.cash_color,
        }
        _get_settings_path().write_text(json.dumps(data, indent=2))

    @rx.event
    def load_settings(self) -> None:
        """Load settings from JSON file on app start."""
        path = _get_settings_path()
        if path.exists():
            data = json.loads(path.read_text())
            self.accent_color = data.get("accent_color", self.accent_color)
            self.gray_color = data.get("gray_color", self.gray_color)
            self.radius = data.get("radius", self.radius)
            self.scaling = data.get("scaling", self.scaling)
            self.default_currency = data.get("default_currency", self.default_currency)
            self.language = data.get("language", self.language)
            self.stock_color = data.get("stock_color", self.stock_color)
            self.etf_color = data.get("etf_color", self.etf_color)
            self.crypto_color = data.get("crypto_color", self.crypto_color)
            self.commodity_color = data.get("commodity_color", self.commodity_color)
            self.cash_color = data.get("cash_color", self.cash_color)
        self.translations = load_translations(self.language)

    @rx.event
    def set_scaling(self, value: str):
        self.scaling = value
        self._save()

    @rx.event
    def set_radius(self, value: str):
        self.radius = value
        self._save()

    @rx.event
    def set_accent_color(self, value: str):
        self.accent_color = value
        self._save()

    @rx.event
    def set_gray_color(self, value: str):
        self.gray_color = value
        self._save()

    @rx.event
    def set_default_currency(self, value: str):
        self.default_currency = value
        self._save()

    @rx.event
    def set_stock_color(self, value: str):
        self.stock_color = value
        self._save()

    @rx.event
    def set_etf_color(self, value: str):
        self.etf_color = value
        self._save()

    @rx.event
    def set_crypto_color(self, value: str):
        self.crypto_color = value
        self._save()

    @rx.event
    def set_commodity_color(self, value: str):
        self.commodity_color = value
        self._save()

    @rx.event
    def set_language(self, value: str):
        self.language = value
        self.translations = load_translations(value)
        self._save()

    @rx.event
    def set_cash_color(self, value: str):
        self.cash_color = value
        self._save()


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
