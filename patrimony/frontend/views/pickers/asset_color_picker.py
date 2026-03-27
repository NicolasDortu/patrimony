import reflex as rx
from reflex.components.radix.themes.base import LiteralAccentColor

from ...templates import ThemeState, t

# Available Radix accent colors for asset types
_asset_color_options: list[str] = list(LiteralAccentColor.__args__)

ASSET_TYPES = [
    ("Stocks", "stock_color", ThemeState.stock_color, ThemeState.set_stock_color),
    ("ETFs", "etf_color", ThemeState.etf_color, ThemeState.set_etf_color),
    ("Crypto", "crypto_color", ThemeState.crypto_color, ThemeState.set_crypto_color),
    (
        "Commodity",
        "commodity_color",
        ThemeState.commodity_color,
        ThemeState.set_commodity_color,
    ),
    ("Cash", "cash_color", ThemeState.cash_color, ThemeState.set_cash_color),
]


def _color_preview(current_color) -> rx.Component:
    """Small color swatch preview next to the dropdown."""
    return rx.box(
        width="1.5rem",
        height="1.5rem",
        border_radius="var(--radius-2)",
        bg="var(--" + current_color + "-9)",
        flex_shrink="0",
    )


def _asset_type_color_row(label: str, current_color, on_select) -> rx.Component:
    """One row: asset type label + color preview + dropdown select."""
    return rx.hstack(
        rx.text(label, size="3", weight="medium", min_width="6rem"),
        _color_preview(current_color),
        rx.select(
            _asset_color_options,
            value=current_color,
            on_change=on_select,
            size="2",
            width="10rem",
        ),
        align="center",
        spacing="3",
    )


def asset_color_picker() -> rx.Component:
    """Settings section for choosing asset type colors."""
    return rx.vstack(
        rx.hstack(
            rx.icon("pie-chart", color=rx.color("accent", 10)),
            rx.heading(t("settings.asset_colors"), size="6"),
            align="center",
        ),
        rx.text(
            t("settings.asset_colors_desc"),
            size="2",
            color=rx.color("gray", 10),
        ),
        *[
            _asset_type_color_row(label, current_color, on_select)
            for label, _, current_color, on_select in ASSET_TYPES
        ],
        spacing="4",
        width="100%",
    )
