import reflex as rx

from ..states import AddStockState


def _form_field(label: str, input_component: rx.Component) -> rx.Component:
    """Reusable form field with label."""
    return rx.box(
        rx.text(label, as_="label", size="2", weight="bold"),
        input_component,
        width="100%",
    )


def _error_callout() -> rx.Component:
    """Conditional error message display."""
    return rx.cond(
        AddStockState.error_message != "",
        rx.callout(
            AddStockState.error_message,
            icon="triangle_alert",
            color="red",
            margin_top="8px",
        ),
    )


def _dialog_form() -> rx.Component:
    """The form content of the dialog."""
    return rx.flex(
        _form_field(
            "Ticker Symbol",
            rx.input(
                placeholder="e.g., GOOG",
                value=AddStockState.ticker,
                on_change=AddStockState.set_ticker,
                width="100%",
            ),
        ),
        _form_field(
            "Buy Price ($)",
            rx.input(
                type="number",
                placeholder="0.01",
                min="0.01",
                step="0.01",
                value=AddStockState.buy_price.to(str),
                on_change=AddStockState.set_buy_price,
                width="100%",
            ),
        ),
        _form_field(
            "Quantity",
            rx.input(
                type="number",
                placeholder="1.0",
                min="1",
                step="1",
                value=AddStockState.quantity.to(str),
                on_change=AddStockState.set_quantity,
                width="100%",
            ),
        ),
        _error_callout(),
        direction="column",
        spacing="3",
        width="100%",
    )


def _dialog_actions() -> rx.Component:
    """The action buttons of the dialog."""
    return rx.flex(
        rx.dialog.close(
            rx.button("Cancel", color_scheme="gray", variant="soft"),
        ),
        rx.button(
            "Add Position",
            on_click=AddStockState.add_position,
            loading=AddStockState.is_loading,
        ),
        spacing="3",
        margin_top="16px",
        justify="end",
    )


def add_stock_dialog() -> rx.Component:
    """Dialog component to add a new stock position."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button("Add New Position", size="3"),
        ),
        rx.dialog.content(
            rx.dialog.title("Add New Position"),
            rx.dialog.description(
                "Enter the details for your new stock position.",
                size="2",
                margin_bottom="16px",
            ),
            _dialog_form(),
            _dialog_actions(),
        ),
        open=AddStockState.is_open,
        on_open_change=AddStockState.set_is_open,
    )
