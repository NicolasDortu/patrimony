"""The file connector page — CSV/Excel import wizard."""

import reflex as rx

from ..services import AssetType, Currency
from ..states.connector_state import ConnectorState
from ..templates import template

# Asset type options for the override dropdown - Exclude CASH
ASSET_TYPE_OPTIONS = [at.name for at in AssetType if at != AssetType.CASH]

CURRENCY_OPTIONS = [c.value for c in Currency]

DELIMITER_OPTIONS = [
    {"value": ",", "label": "Comma ( , )"},
    {"value": ";", "label": "Semicolon ( ; )"},
    {"value": "\t", "label": "Tab"},
    {"value": "|", "label": "Pipe ( | )"},
]


# ============================================================================
# Step 1: Upload
# ============================================================================


def _step_upload() -> rx.Component:
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
        rx.upload(
            rx.vstack(
                rx.cond(
                    ConnectorState.has_file,
                    rx.vstack(
                        rx.icon("file-check", size=40, color=rx.color("green", 9)),
                        rx.text(
                            ConnectorState.filename,
                            size="3",
                            weight="bold",
                            color=rx.color("green", 11),
                        ),
                        rx.text(
                            "Click or drop a new file to replace",
                            size="2",
                            color=rx.color("gray", 10),
                        ),
                        align="center",
                        spacing="2",
                    ),
                    rx.vstack(
                        rx.icon("upload", size=40, color=rx.color("accent", 9)),
                        rx.text(
                            "Drag and drop or click to upload",
                            size="3",
                            weight="bold",
                        ),
                        rx.text(
                            "Supports .csv, .xlsx, .xls files",
                            size="2",
                            color=rx.color("gray", 10),
                        ),
                        align="center",
                        spacing="2",
                    ),
                ),
                align="center",
                spacing="2",
            ),
            id="connector_upload",
            accept={
                "text/csv": [".csv"],
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
                    ".xlsx"
                ],
                "application/vnd.ms-excel": [".xls"],
            },
            max_files=1,
            border=f"2px dashed {rx.color('accent', 6)}",
            border_radius="var(--radius-3)",
            padding="3em",
            width="100%",
            cursor="pointer",
            _hover={"border_color": rx.color("accent", 9)},
        ),
        rx.button(
            "Read File",
            on_click=ConnectorState.handle_upload(
                rx.upload_files(upload_id="connector_upload")
            ),
            disabled=~rx.selected_files("connector_upload"),
            size="3",
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


def _on_delimiter_change(label: str) -> None:
    """Map the display label back to the actual delimiter character."""
    mapping = {
        "Comma ( , )": ",",
        "Semicolon ( ; )": ";",
        "Tab": "\t",
        "Pipe ( | )": "|",
    }
    return ConnectorState.set_delimiter(mapping.get(label, ","))


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


def _step_mapping() -> rx.Component:
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


def _step_review() -> rx.Component:
    """Review step: show mapping summary and resolve unresolved tickers."""
    return rx.vstack(
        rx.text("Review your import", weight="bold", size="4"),
        # Summary
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
        # Unresolved tickers (only for positions)
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
        # Unknown cash accounts (only for cash import)
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


def _step_result() -> rx.Component:
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


def _step_indicator() -> rx.Component:
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


# ============================================================================
# Main page
# ============================================================================


@template(route="/connectors/file", title="File Import")
def file_connector() -> rx.Component:
    """The file connector page with a CSV/Excel import wizard."""
    return rx.vstack(
        rx.hstack(
            rx.link(
                rx.icon("arrow-left", size=20),
                href="/connectors",
            ),
            rx.heading("File Import", size="5"),
            align="center",
            spacing="3",
        ),
        rx.text(
            "Import positions or cash operations from CSV or Excel files.",
            size="2",
            color=rx.color("gray", 10),
        ),
        _step_indicator(),
        rx.card(
            rx.cond(
                ConnectorState.step == 1,
                _step_upload(),
                rx.cond(
                    ConnectorState.step == 2,
                    _step_mapping(),
                    rx.cond(
                        ConnectorState.step == 3,
                        _step_review(),
                        _step_result(),
                    ),
                ),
            ),
            width="100%",
            max_width="800px",
        ),
        spacing="5",
        width="100%",
        align="center",
    )
