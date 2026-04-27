"""Reusable dialog factory for standard add-entity forms.

Provides ``build_add_dialog`` which constructs a consistent dialog structure:
trigger button → dialog content → form with fields → cancel/submit buttons.
"""

from dataclasses import dataclass

import reflex as rx

from ..templates import t


@dataclass(frozen=True)
class DialogField:
    """Describes one input field inside a dialog form.

    Attributes:
        name: Form field name (maps to ``form_data[name]``).
        placeholder_key: Translation key for the placeholder text.
        label_key: Optional translation key for a small label rendered
            above the input. Use this whenever the placeholder alone
            isn't enough context for the user.
        field_type: HTML input type (``text``, ``number``, ``date``, ``select``).
        required: Whether the field is required.
        options: For ``select`` fields — list of option values.
        default_value: Pre-filled default value.
        min: Minimum value for number/date inputs.
        step: Step value for number inputs.
    """

    name: str
    placeholder_key: str
    label_key: str | None = None
    field_type: str = "text"
    required: bool = False
    options: list[str] | None = None
    default_value: str | None = None
    min: str | None = None
    step: str | None = None


def _build_input(field: DialogField) -> rx.Component:
    """Build only the input element (no label)."""
    if field.field_type == "select" and field.options:
        kwargs = {
            "placeholder": t(field.placeholder_key),
            "name": field.name,
        }
        if field.default_value:
            kwargs["default_value"] = field.default_value
        if field.required:
            kwargs["required"] = True
        return rx.select(field.options, **kwargs)

    kwargs = {
        "placeholder": t(field.placeholder_key),
        "name": field.name,
        "type": field.field_type,
    }
    if field.required:
        kwargs["required"] = True
    if field.default_value:
        kwargs["default_value"] = field.default_value
    if field.min:
        kwargs["min"] = field.min
    if field.step:
        kwargs["step"] = field.step
    return rx.input(**kwargs)


def _build_field(field: DialogField) -> rx.Component:
    """Build a labelled form field. Falls back to a bare input when no label."""
    label_text = field.label_key or field.placeholder_key
    return rx.vstack(
        rx.text(t(label_text), size="1", weight="medium"),
        _build_input(field),
        spacing="1",
        align="stretch",
        width="100%",
    )


def build_add_dialog(
    *,
    title_key: str,
    desc_key: str,
    submit_key: str,
    fields: list[DialogField],
    on_submit: callable,
) -> rx.Component:
    """Build a standard add-entity dialog with trigger button, form, and action buttons.

    Args:
        title_key: Translation key for the dialog title and trigger button text.
        desc_key: Translation key for the dialog description.
        submit_key: Translation key for the submit button label.
        fields: Ordered list of ``DialogField`` descriptors.
        on_submit: Event handler receiving ``form_data`` dict on submit.
    """
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus", size=26),
                rx.text(t(submit_key), size="4"),
                size="3",
                variant="surface",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title(t(title_key)),
            rx.dialog.description(t(desc_key)),
            rx.form(
                rx.flex(
                    *[_build_field(f) for f in fields],
                    rx.flex(
                        rx.dialog.close(
                            rx.button(
                                t("btn.cancel"),
                                type="button",
                                variant="soft",
                                color_scheme="gray",
                            ),
                        ),
                        rx.dialog.close(
                            rx.button(t(submit_key), type="submit"),
                        ),
                        spacing="3",
                        justify="end",
                    ),
                    direction="column",
                    spacing="4",
                ),
                on_submit=on_submit,
                reset_on_submit=True,
            ),
            max_width="450px",
        ),
    )
