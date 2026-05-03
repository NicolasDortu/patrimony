import reflex as rx

from ..components.dialog_factory import DialogField, build_add_dialog
from ..services import Currency
from ..states.properties_state import PropertiesState


_PROPERTY_FIELDS = [
    DialogField(name="name", placeholder_key="label.name", required=True),
    DialogField(name="description", placeholder_key="label.description"),
    DialogField(
        name="value",
        placeholder_key="label.value",
        field_type="number",
        min="0.01",
        step="0.01",
        required=True,
    ),
    DialogField(
        name="category",
        placeholder_key="label.category",
    ),
    DialogField(
        name="currency",
        placeholder_key="label.currency",
        field_type="select",
        options=[c.value for c in Currency],
        default_value="EUR",
    ),
    DialogField(
        name="purchase_date", placeholder_key="label.purchase_date", field_type="date"
    ),
]


def open_add_property_dialog(on_submit: callable) -> rx.Component:
    """Button to open a dialog to add a new property."""
    return build_add_dialog(
        title_key="dialog.add_property.title",
        desc_key="dialog.add_property.desc",
        submit_key="dialog.add_property.submit",
        fields=_PROPERTY_FIELDS,
        on_submit=on_submit,
        open_var=PropertiesState.add_dialog_open,
        set_open=PropertiesState.set_add_dialog_open,
    )
