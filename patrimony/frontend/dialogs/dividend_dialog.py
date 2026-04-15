import reflex as rx

from ..components.dialog_factory import DialogField, build_add_dialog


_DIVIDEND_FIELDS = [
    DialogField(
        name="amount",
        placeholder_key="label.amount",
        field_type="number",
        min="0.01",
        step="0.01",
        required=True,
    ),
    DialogField(name="date", placeholder_key="label.date", field_type="date"),
]


def open_add_dividend_dialog(on_submit: callable) -> rx.Component:
    """Button to open a dialog to add a new dividend."""
    return build_add_dialog(
        title_key="dialog.add_dividend.title",
        desc_key="dialog.add_dividend.desc",
        submit_key="dialog.add_dividend.submit",
        fields=_DIVIDEND_FIELDS,
        on_submit=on_submit,
    )
