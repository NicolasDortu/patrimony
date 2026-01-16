import reflex as rx

from ..states.dialog_stock_state import AddStockState
from ..components.dialog import dialog_form, dialog_actions


def add_stock_dialog() -> rx.Component:
    fields = [
        (
            "Ticker Symbol",
            {
                "placeholder": "e.g., GOOG",
                "value": AddStockState.ticker,
                "on_change": AddStockState.set_ticker,
            },
        ),
        (
            "Buy Price ($)",
            {
                "type": "number",
                "placeholder": "0.01",
                "min": "0.01",
                "step": "0.01",
                "value": AddStockState.buy_price.to(str),
                "on_change": AddStockState.set_buy_price,
            },
        ),
        (
            "Quantity",
            {
                "type": "number",
                "placeholder": "1.0",
                "min": "1",
                "step": "1",
                "value": AddStockState.quantity.to(str),
                "on_change": AddStockState.set_quantity,
            },
        ),
    ]

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
            dialog_form(fields, state=AddStockState),
            dialog_actions(
                on_submit=AddStockState.add_position,
                submit_label="Add Position",
                is_loading=AddStockState.is_loading,
            ),
        ),
        open=AddStockState.is_open,
        on_open_change=AddStockState.set_is_open,
    )
