import reflex as rx
from reflex.components.radix.themes.base import LiteralAccentColor


def create_gradient(color: LiteralAccentColor, id: str) -> rx.Component:
    """Create gradient definition for area chart."""
    return rx.el.svg.defs(
        rx.el.svg.linear_gradient(
            rx.el.svg.stop(
                stop_color=f"var(--{color}-9)",
                stop_opacity="0.8",
                offset="5%",
            ),
            rx.el.svg.stop(
                stop_color=f"var(--{color}-9)",
                stop_opacity="0",
                offset="95%",
            ),
            id=id,
            x1="0",
            x2="0",
            y1="0",
            y2="1",
        )
    )


def create_dynamic_gradient(color_var: rx.Var[str], id: str) -> rx.Component:
    """Create gradient definition using a reactive state variable for the color."""
    color_css = "var(--" + color_var + "-9)"
    return rx.el.svg.defs(
        rx.el.svg.linear_gradient(
            rx.el.svg.stop(
                stop_color=color_css,
                stop_opacity="0.8",
                offset="5%",
            ),
            rx.el.svg.stop(
                stop_color=color_css,
                stop_opacity="0",
                offset="95%",
            ),
            id=id,
            x1="0",
            x2="0",
            y1="0",
            y2="1",
        )
    )


def period_selector(value: str, on_change: callable) -> rx.Component:
    """Segmented control for selecting time period."""
    return rx.segmented_control.root(
        rx.segmented_control.item("1D", value="1D"),
        rx.segmented_control.item("5D", value="5D"),
        rx.segmented_control.item("1M", value="1M"),
        rx.segmented_control.item("6M", value="6M"),
        rx.segmented_control.item("1Y", value="1Y"),
        rx.segmented_control.item("5Y", value="5Y"),
        default_value="1M",
        value=value,
        on_change=on_change,
        size="1",
    )
