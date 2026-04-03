import reflex as rx
from reflex.components.radix.themes.base import LiteralAccentColor

from ...templates import ThemeState, t

# Available Radix accent colors for asset types
_asset_color_options: list[str] = list(LiteralAccentColor.__args__)

ASSET_TYPES = [
    ("All", "all_color", ThemeState.all_color, ThemeState.set_all_color),
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
    (
        "Properties",
        "property_color",
        ThemeState.property_color,
        ThemeState.set_property_color,
    ),
]


def _color_swatch(color_name: str, current_color, on_select) -> rx.Component:
    """Clickable color swatch circle."""
    is_selected = current_color == color_name
    return rx.tooltip(
        rx.box(
            width="1.5rem",
            height="1.5rem",
            border_radius="50%",
            bg=f"var(--{color_name}-9)",
            cursor="pointer",
            border=rx.cond(
                is_selected,
                "2px solid var(--gray-12)",
                "2px solid transparent",
            ),
            on_click=on_select(color_name),
            _hover={"transform": "scale(1.2)"},
            transition="transform 0.15s",
        ),
        content=color_name,
    )


def _asset_type_color_row(label: str, current_color, on_select) -> rx.Component:
    """One row: asset type label + clickable swatch grid."""
    return rx.vstack(
        rx.text(label, size="3", weight="medium"),
        rx.flex(
            *[_color_swatch(c, current_color, on_select) for c in _asset_color_options],
            wrap="wrap",
            gap="0.4rem",
        ),
        spacing="2",
    )


def asset_color_picker() -> rx.Component:
    """Settings section for choosing asset type colors with visual swatches."""
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
