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


def _icon_btn(icon: str, label: str, on_click, **kwargs) -> rx.Component:
    """Square icon-only button with a tooltip."""
    return rx.tooltip(
        rx.icon_button(rx.icon(icon, size=18), on_click=on_click, size="2", **kwargs),
        content=label,
    )


_DISPATCH_DELETE_JS = """
(() => {
  const canvas = document.querySelector('canvas[data-testid="data-grid-canvas"]');
  if (!canvas) return;
  canvas.focus();
  const evt = new KeyboardEvent('keydown', {
    key: 'Delete', code: 'Delete', keyCode: 46, which: 46, bubbles: true,
  });
  canvas.dispatchEvent(evt);
})();
"""


def _spreadsheet_toolbar(state_cls) -> rx.Component:
    """Toolbar shown only while in spreadsheet mode."""
    return rx.cond(
        state_cls.spreadsheet_mode,
        rx.hstack(
            _icon_btn(
                "save",
                t("spreadsheet.save"),
                state_cls.save_spreadsheet_changes,
                color_scheme="green",
                disabled=~state_cls.has_unsaved_changes,
            ),
            _icon_btn(
                "plus",
                t("spreadsheet.add_row"),
                state_cls.on_spreadsheet_row_appended,
                variant="soft",
            ),
            _icon_btn(
                "trash-2",
                t("spreadsheet.delete_selected"),
                rx.call_script(_DISPATCH_DELETE_JS),
                color_scheme="red",
                variant="soft",
            ),
            rx.button(
                rx.icon("x", size=16),
                t("spreadsheet.discard"),
                size="2",
                variant="outline",
                color_scheme="gray",
                on_click=state_cls.discard_spreadsheet_changes,
            ),
            spacing="2",
            align="center",
        ),
    )


def spreadsheet_grid(state_cls) -> rx.Component:
    """Editable data grid powered by Glide Data Grid.

    Edits live in state until the user hits Save:
      - new rows: "Add row" toolbar button
      - deletes: tick row markers, then press the Delete key
    """
    return rx.box(
        rx.data_editor(
            columns=state_cls.spreadsheet_columns,
            data=state_cls.spreadsheet_data,
            rows=state_cls.spreadsheet_row_count,
            on_cell_edited=state_cls.on_spreadsheet_cell_edited,
            on_delete=state_cls.on_spreadsheet_delete,
            theme=rx.color_mode_cond(_LIGHT_THEME, _DARK_THEME),
            row_markers="checkbox-visible",
            row_select="multi",
            smooth_scroll_x=True,
            smooth_scroll_y=True,
            column_select="none",
            width="100%",
            height="100%",
        ),
        width="100%",
        height="75vh",
        min_height="500px",
    )


def spreadsheet_toggle_button(state_cls) -> rx.Component:
    """Toggle between table and spreadsheet mode."""
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
    """Render the spreadsheet grid or the regular table, with a toolbar."""
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
