"""Reusable spreadsheet view component using rx.data_editor."""

import reflex as rx

from ...templates import t


_LIGHT_THEME = rx.data_editor_theme(
    accent_color="#d6336c",
    accent_light="#f8d7e5",
    bg_cell="#ffffff",
    bg_header="#f8f9fa",
    bg_header_has_focus="#edf0f2",
    bg_header_hovered="#edf0f2",
    text_dark="#1a1a1a",
    text_medium="#495057",
    text_light="#868e96",
    text_header="#495057",
    border_color="#dee2e6",
    horizontal_border_color="#e9ecef",
    header_bottom_border_color="#ced4da",
    font_family="inherit",
)

_DARK_THEME = rx.data_editor_theme(
    accent_color="#d6336c",
    accent_light="#3d1a2b",
    bg_cell="#111113",
    bg_header="#1a1a1f",
    bg_header_has_focus="#222228",
    bg_header_hovered="#222228",
    text_dark="#eeeeee",
    text_medium="#b0b0b0",
    text_light="#787878",
    text_header="#b0b0b0",
    border_color="#2e2e32",
    horizontal_border_color="#252528",
    header_bottom_border_color="#3a3a40",
    font_family="inherit",
)


def _spreadsheet_toolbar(state_cls) -> rx.Component:
    """Toolbar with save and discard buttons (shown only in spreadsheet mode)."""
    return rx.cond(
        state_cls.spreadsheet_mode,
        rx.hstack(
            rx.button(
                rx.icon("save", size=16),
                t("spreadsheet.save"),
                size="2",
                color_scheme="green",
                disabled=~state_cls.has_unsaved_changes,
                on_click=state_cls.save_spreadsheet_changes,
            ),
            rx.button(
                rx.icon("x", size=16),
                t("spreadsheet.discard"),
                size="2",
                variant="outline",
                color_scheme="red",
                on_click=state_cls.discard_spreadsheet_changes,
            ),
            spacing="2",
            align="center",
        ),
    )


def spreadsheet_grid(state_cls) -> rx.Component:
    """Editable data grid powered by Glide Data Grid."""
    return rx.data_editor(
        columns=state_cls.spreadsheet_columns,
        data=state_cls.spreadsheet_data,
        rows=state_cls.spreadsheet_row_count,
        on_cell_edited=state_cls.on_spreadsheet_cell_edited,
        on_row_appended=state_cls.on_spreadsheet_row_appended,
        on_delete=state_cls.on_spreadsheet_delete,
        theme=rx.color_mode_cond(_LIGHT_THEME, _DARK_THEME),
        row_markers="checkbox-visible",
        row_select="multi",
        smooth_scroll_x=True,
        smooth_scroll_y=True,
        column_select="none",
        width="100%",
        height="65vh",
    )


def spreadsheet_toggle_button(state_cls) -> rx.Component:
    """Toggle button for switching between table and spreadsheet mode."""
    return rx.button(
        rx.cond(
            state_cls.spreadsheet_mode,
            rx.icon("table", size=16),
            rx.icon("sheet", size=16),
        ),
        t("btn.edit_mode"),
        size="3",
        variant="surface",
        on_click=state_cls.toggle_spreadsheet_mode,
    )


def spreadsheet_or_table(state_cls, table_component: rx.Component) -> rx.Component:
    """Conditionally render spreadsheet grid or the regular table view.

    Includes contextual save/discard controls when in spreadsheet mode.
    Place spreadsheet_toggle_button() separately in your page's action bar.
    """
    return rx.vstack(
        _spreadsheet_toolbar(state_cls),
        rx.cond(
            state_cls.spreadsheet_mode,
            spreadsheet_grid(state_cls),
            table_component,
        ),
        spacing="3",
        width="100%",
    )
