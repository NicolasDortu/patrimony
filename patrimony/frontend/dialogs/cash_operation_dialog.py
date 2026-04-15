from datetime import datetime

import reflex as rx

from ..components.dialog_factory import DialogField, build_add_dialog


_OPERATION_FIELDS = [
    DialogField(name="title", placeholder_key="label.title", required=True),
    DialogField(
        name="amount",
        placeholder_key="label.amount",
        field_type="number",
        step="0.01",
        required=True,
    ),
    DialogField(
        name="category", placeholder_key="label.category", default_value="Uncategorized"
    ),
    DialogField(
        name="operation_date",
        placeholder_key="label.date",
        field_type="date",
        default_value=datetime.now().date().isoformat(),
        required=True,
    ),
]


def open_add_operation_dialog(on_submit: callable) -> rx.Component:
    """Button to open a dialog to add a new cash operation (deposit/expense)."""
    return build_add_dialog(
        title_key="dialog.add_operation.title",
        desc_key="dialog.add_operation.desc",
        submit_key="dialog.add_operation.submit",
        fields=_OPERATION_FIELDS,
        on_submit=on_submit,
    )
