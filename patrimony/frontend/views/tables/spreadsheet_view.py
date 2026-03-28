"""Reusable spreadsheet view component using rx.data_editor."""

import reflex as rx

from ...templates import t


def spreadsheet_toolbar(state_cls) -> rx.Component:
    """Toolbar with spreadsheet toggle, save and discard buttons."""
    return rx.hstack(
        rx.tooltip(
            rx.icon_button(
                rx.cond(
                    state_cls.spreadsheet_mode,
                    rx.icon("table", size=18),
                    rx.icon("sheet", size=18),
                ),
                variant="ghost",
                size="2",
                on_click=state_cls.toggle_spreadsheet_mode,
            ),
            content=t("spreadsheet.toggle"),
        ),
        rx.cond(
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
            ),
        ),
        spacing="2",
        align="center",
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
        row_markers="checkbox-visible",
        row_select="multi",
        smooth_scroll_x=True,
        smooth_scroll_y=True,
        column_select="none",
        width="100%",
        height="65vh",
    )


def spreadsheet_or_table(state_cls, table_component: rx.Component) -> rx.Component:
    """Conditionally render spreadsheet grid or the regular table view."""
    return rx.cond(
        state_cls.spreadsheet_mode,
        spreadsheet_grid(state_cls),
        table_component,
    )
