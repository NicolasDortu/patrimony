import reflex as rx


def _form_field(label: str, input_component: rx.Component) -> rx.Component:
    """Reusable form field with label."""
    return rx.box(
        rx.text(label, as_="label", size="2", weight="bold"),
        input_component,
        width="100%",
    )


def _error_callout(state: rx.Component) -> rx.Component:
    """Conditional error message display."""
    return rx.cond(
        state.error_message != "",
        rx.callout(
            state.error_message,
            icon="triangle_alert",
            color="red",
            margin_top="8px",
        ),
    )


def dialog_form(fields, state=None) -> rx.Component:
    """Form content for dialogs."""
    return rx.flex(
        *[
            _form_field(
                label,
                rx.input(**input_props),
            )
            for label, input_props in fields
        ],
        _error_callout(state) if state else None,
        direction="column",
        spacing="3",
        width="100%",
    )


def dialog_actions(
    on_submit,
    submit_label="Submit",
    is_loading=False,
    show_close=True,
    **kwargs,
) -> rx.Component:
    """Action buttons for dialogs."""
    return rx.flex(
        (
            rx.dialog.close(
                rx.button("Cancel", color_scheme="gray", variant="soft"),
            )
            if show_close
            else None
        ),
        rx.button(
            submit_label,
            on_click=on_submit,
            loading=is_loading,
            **kwargs,
        ),
        spacing="3",
        margin_top="16px",
        justify="end",
    )
