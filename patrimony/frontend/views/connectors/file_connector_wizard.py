"""File import wizard view components — steps, preview, and indicators."""

import reflex as rx

from ...services import AssetType, Currency
from ...states.connector_state import ConnectorState

# Asset type options for the override dropdown - Exclude CASH
ASSET_TYPE_OPTIONS = [at.name for at in AssetType if at != AssetType.CASH]

CURRENCY_OPTIONS = [c.value for c in Currency]

DELIMITER_OPTIONS = [
    {"value": ",", "label": "Comma ( , )"},
    {"value": ";", "label": "Semicolon ( ; )"},
    {"value": "\t", "label": "Tab"},
    {"value": "|", "label": "Pipe ( | )"},
]

# JavaScript to open Tauri native file dialog (returns full path)
_PICK_FILE_JS = """
(async function() {
    if (!window.__TAURI__) return '';
    try {
        const path = await window.__TAURI__.dialog.open({
            multiple: false,
            directory: false,
            filters: [{name: 'Spreadsheets', extensions: ['csv', 'xlsx', 'xls']}]
        });
        return path || '';
    } catch (e) {
        return '';
    }
})()
"""


# ============================================================================
# Step 1: Upload
# ============================================================================


def _on_delimiter_change(label: str) -> None:
    """Map the display label back to the actual delimiter character."""
    mapping = {
        "Comma ( , )": ",",
        "Semicolon ( ; )": ";",
        "Tab": "\t",
        "Pipe ( | )": "|",
    }
    return ConnectorState.set_delimiter(mapping.get(label, ","))


def step_upload() -> rx.Component:
    """File upload step with import mode and delimiter selection."""
    return rx.vstack(
        rx.text("Select what you want to import:", weight="bold", size="3"),
        rx.segmented_control.root(
            rx.segmented_control.item("Positions", value="positions"),
            rx.segmented_control.item("Cash Operations", value="cash"),
            value=ConnectorState.import_mode,
            on_change=ConnectorState.set_import_mode,
        ),
        rx.separator(),
        rx.text("CSV Delimiter:", weight="bold", size="3"),
        rx.select(
            [opt["label"] for opt in DELIMITER_OPTIONS],
            value=rx.cond(
                ConnectorState.delimiter == ",",
                "Comma ( , )",
                rx.cond(
                    ConnectorState.delimiter == ";",
                    "Semicolon ( ; )",
                    rx.cond(
                        ConnectorState.delimiter == "\t",
                        "Tab",
                        "Pipe ( | )",
                    ),
                ),
            ),
            on_change=_on_delimiter_change,
        ),
        rx.text(
            "Only relevant for CSV files. Excel files ignore this setting.",
            size="1",
            color=rx.color("gray", 10),
        ),
        rx.separator(),
        # Tauri native file picker (full path)
        rx.button(
            rx.icon("folder-open", size=20),
            "Browse File",
            on_click=rx.call_script(
                _PICK_FILE_JS,
                callback=ConnectorState.handle_file_path,
            ),
            size="3",
            width="100%",
            variant="outline",
        ),
        rx.text(
            "Supports .csv, .xlsx, .xls files",
            size="1",
            color=rx.color("gray", 10),
        ),
        spacing="4",
        width="100%",
    )


# ============================================================================
# Step 2: Column Mapping
# ============================================================================


def _mapping_select(file_column: str) -> rx.Component:
    """A select dropdown for mapping a single file column to a target field."""
    return rx.hstack(
        rx.text(file_column, size="2", weight="bold", min_width="150px"),
        rx.icon("arrow-right", size=16, color=rx.color("gray", 9)),
        rx.select(
            ConnectorState.target_fields,
            value=ConnectorState.column_mapping[file_column],
            on_change=lambda val: ConnectorState.set_column_mapping(file_column, val),
            placeholder="-- Ignore --",
            width="250px",
        ),
        align="center",
        spacing="3",
    )


def _preview_table() -> rx.Component:
    """Table showing the first few rows of the uploaded file."""
    return rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.foreach(
                        ConnectorState.file_columns,
                        lambda col: rx.table.column_header_cell(
                            rx.text(col, size="2", weight="bold")
                        ),
                    ),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    ConnectorState.preview_rows,
                    lambda row: rx.table.row(
                        rx.foreach(
                            ConnectorState.file_columns,
                            lambda col: rx.table.cell(
                                rx.text(row[col], size="1"),
                            ),
                        ),
                    ),
                ),
            ),
            width="100%",
            size="1",
        ),
        overflow_x="auto",
        width="100%",
    )


def step_mapping() -> rx.Component:
    """Column mapping step with preview table."""
    return rx.vstack(
        rx.hstack(
            rx.text("File Preview", weight="bold", size="3"),
            rx.text(
                f"({ConnectorState.filename})",
                size="2",
                color=rx.color("gray", 10),
            ),
            align="center",
            spacing="2",
        ),
        _preview_table(),
        rx.separator(),
        rx.text("Map your columns", weight="bold", size="3"),
        rx.text(
            "Link each column from your file to the corresponding data field.",
            size="2",
            color=rx.color("gray", 10),
        ),
        rx.vstack(
            rx.foreach(ConnectorState.file_columns, _mapping_select),
            spacing="3",
            width="100%",
        ),
        rx.separator(),
        rx.hstack(
            rx.button(
                rx.icon("arrow-left", size=16),
                "Back",
                variant="outline",
                on_click=ConnectorState.go_back,
                size="3",
            ),
            rx.spacer(),
            rx.button(
                "Continue",
                rx.icon("arrow-right", size=16),
                on_click=ConnectorState.proceed_to_review,
                disabled=~ConnectorState.mapping_valid,
                size="3",
            ),
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


# ============================================================================
# Step 3: Review & Asset Type Resolution
# ============================================================================


def _asset_type_row(ticker: str) -> rx.Component:
    """Row for assigning asset type to an unresolved ticker."""
    return rx.hstack(
        rx.text(ticker, size="2", weight="bold", min_width="120px"),
        rx.select(
            ASSET_TYPE_OPTIONS,
            placeholder="Select asset type",
            on_change=lambda val: ConnectorState.set_asset_type_override(ticker, val),
            width="200px",
        ),
        align="center",
        spacing="3",
    )


def _unknown_account_row(account: str) -> rx.Component:
    """Row for configuring a new cash account (bank + currency)."""
    return rx.hstack(
        rx.text(account, size="2", weight="bold", min_width="150px"),
        rx.input(
            placeholder="Bank name",
            on_change=lambda val: ConnectorState.set_account_bank(account, val),
            width="200px",
        ),
        rx.select(
            CURRENCY_OPTIONS,
            placeholder="Currency",
            on_change=lambda val: ConnectorState.set_account_currency(account, val),
            width="120px",
        ),
        align="center",
        spacing="3",
    )


def step_review() -> rx.Component:
    """Review step: show mapping summary and resolve unresolved tickers."""
    return rx.vstack(
        rx.text("Review your import", weight="bold", size="4"),
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.text("File:", weight="bold", size="2"),
                    rx.text(ConnectorState.filename, size="2"),
                    spacing="2",
                ),
                rx.hstack(
                    rx.text("Mode:", weight="bold", size="2"),
                    rx.badge(ConnectorState.import_mode),
                    spacing="2",
                ),
                rx.hstack(
                    rx.text("Rows:", weight="bold", size="2"),
                    rx.text(ConnectorState.preview_rows.length(), size="2"),
                    spacing="2",
                ),
                spacing="2",
            ),
            width="100%",
        ),
        rx.cond(
            ConnectorState.has_unresolved_tickers,
            rx.vstack(
                rx.separator(),
                rx.callout(
                    rx.text(
                        "The following tickers were not found in the reference database. "
                        "Please assign an asset type for each:",
                        size="2",
                    ),
                    icon="triangle-alert",
                    color_scheme="orange",
                    width="100%",
                ),
                rx.vstack(
                    rx.foreach(ConnectorState.unresolved_tickers, _asset_type_row),
                    spacing="2",
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
        ),
        rx.cond(
            ConnectorState.has_unknown_accounts,
            rx.vstack(
                rx.separator(),
                rx.callout(
                    rx.text(
                        "The following account numbers don't exist yet. "
                        "Please provide a bank name and currency for each:",
                        size="2",
                    ),
                    icon="triangle-alert",
                    color_scheme="orange",
                    width="100%",
                ),
                rx.vstack(
                    rx.foreach(ConnectorState.unknown_accounts, _unknown_account_row),
                    spacing="2",
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
        ),
        rx.separator(),
        rx.hstack(
            rx.button(
                rx.icon("arrow-left", size=16),
                "Back",
                variant="outline",
                on_click=ConnectorState.go_back,
                size="3",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("import", size=16),
                "Import",
                on_click=ConnectorState.run_import,
                disabled=~ConnectorState.can_import,
                loading=ConnectorState.is_loading,
                size="3",
            ),
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


# ============================================================================
# Step 4: Result
# ============================================================================


def step_result() -> rx.Component:
    """Import result step."""
    return rx.vstack(
        rx.cond(
            ConnectorState.result_success,
            rx.vstack(
                rx.icon("circle-check", size=48, color=rx.color("green", 9)),
                rx.text("Import Successful!", weight="bold", size="4"),
                rx.text(ConnectorState.result_message, size="2"),
                align="center",
                spacing="3",
            ),
            rx.vstack(
                rx.icon("circle-x", size=48, color=rx.color("red", 9)),
                rx.text("Import Failed", weight="bold", size="4"),
                rx.text(ConnectorState.result_message, size="2"),
                align="center",
                spacing="3",
            ),
        ),
        rx.cond(
            ConnectorState.result_errors.length() > 0,
            rx.vstack(
                rx.separator(),
                rx.text("Details:", weight="bold", size="3"),
                rx.box(
                    rx.foreach(
                        ConnectorState.result_errors,
                        lambda err: rx.text(err, size="1", color=rx.color("red", 11)),
                    ),
                    max_height="200px",
                    overflow_y="auto",
                    width="100%",
                    padding="2",
                    border=f"1px solid {rx.color('gray', 6)}",
                    border_radius="var(--radius-2)",
                ),
                spacing="2",
                width="100%",
            ),
        ),
        rx.separator(),
        rx.button(
            rx.icon("rotate-ccw", size=16),
            "Import Another File",
            on_click=ConnectorState.reset_wizard,
            size="3",
            width="100%",
        ),
        spacing="4",
        width="100%",
        align="center",
    )


# ============================================================================
# Step indicator
# ============================================================================


def step_indicator() -> rx.Component:
    """Visual indicator of the current wizard step."""

    def _dot(num: str, label: str) -> rx.Component:
        return rx.hstack(
            rx.cond(
                ConnectorState.step >= int(num),
                rx.box(
                    rx.text(num, size="1", color="white", weight="bold"),
                    background=rx.color("accent", 9),
                    border_radius="50%",
                    width="28px",
                    height="28px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
                rx.box(
                    rx.text(num, size="1", weight="bold"),
                    border=f"2px solid {rx.color('gray', 7)}",
                    border_radius="50%",
                    width="28px",
                    height="28px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                ),
            ),
            rx.text(label, size="2", weight="medium"),
            align="center",
            spacing="2",
        )

    return rx.hstack(
        _dot("1", "Upload"),
        rx.box(width="40px", height="2px", background=rx.color("gray", 6)),
        _dot("2", "Mapping"),
        rx.box(width="40px", height="2px", background=rx.color("gray", 6)),
        _dot("3", "Review"),
        rx.box(width="40px", height="2px", background=rx.color("gray", 6)),
        _dot("4", "Result"),
        justify="center",
        align="center",
        spacing="3",
        width="100%",
        padding_y="1em",
    )
