import reflex as rx

from ..components.dialog_factory import DialogField, build_add_dialog
from ..services import Currency
from ..states.cash_state import CashTableState


_CASH_FIELDS = [
    DialogField(name="bank", placeholder_key="label.bank_name", required=True),
    DialogField(
        name="account_number", placeholder_key="label.account_number", required=True
    ),
    DialogField(
        name="currency",
        placeholder_key="label.currency",
        field_type="select",
        options=[c.value for c in Currency],
        default_value="EUR",
        required=True,
    ),
    DialogField(
        name="balance",
        placeholder_key="label.balance",
        field_type="number",
        min="0",
        step="0.01",
        required=True,
    ),
]


def open_add_cash_dialog(on_submit: callable) -> rx.Component:
    """Button to open a dialog to add a new cash entry."""
    return build_add_dialog(
        title_key="dialog.add_cash.title",
        desc_key="dialog.add_cash.desc",
        submit_key="dialog.add_cash.submit",
        fields=_CASH_FIELDS,
        on_submit=on_submit,
        open_var=CashTableState.add_dialog_open,
        set_open=CashTableState.set_add_dialog_open,
    )
