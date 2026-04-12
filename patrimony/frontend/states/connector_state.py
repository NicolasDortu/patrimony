"""State for the file connector wizard (CSV/Excel import)."""

from pathlib import Path

import reflex as rx

from ..services import FileConnectorService

# Fields the user can map to
POSITION_TARGET_FIELDS: list[str] = [
    "ticker",
    "price",
    "quantity",
    "fees",
    "date",
    "asset_type",
    "currency",
]

CASH_TARGET_FIELDS: list[str] = [
    "account_number",
    "amount",
    "title",
    "operation_date",
]


class ConnectorState(rx.State):
    """Multi-step wizard state for importing CSV/Excel files."""

    # Wizard step: 1=upload, 2=mapping, 3=review, 4=result
    step: int = 1

    # Import mode
    import_mode: str = "positions"  # "positions" or "cash"

    # Upload state
    filename: str = ""
    _file_bytes: bytes = b""
    _source_path: str = ""
    delimiter: str = ","

    # Parsed data
    file_columns: list[str] = []
    preview_rows: list[dict] = []

    # Column mapping: file_column -> target_field
    column_mapping: dict[str, str] = {}

    # Asset type resolution (for positions)
    unresolved_tickers: list[str] = []
    asset_type_overrides: dict[str, str] = {}

    # Unknown cash accounts (for cash import)
    unknown_accounts: list[str] = []
    new_account_details: dict[str, dict] = {}  # acct -> {"bank": str, "currency": str}

    # Import result
    result_message: str = ""
    result_success: bool = False
    result_errors: list[str] = []

    # Loading indicator
    is_loading: bool = False

    @rx.var
    def target_fields(self) -> list[str]:
        """Return the appropriate target fields based on import mode."""
        if self.import_mode == "cash":
            return CASH_TARGET_FIELDS
        return POSITION_TARGET_FIELDS

    @rx.var
    def has_file(self) -> bool:
        return self.filename != ""

    @rx.var
    def mapping_valid(self) -> bool:
        """Check if all required fields are mapped."""
        mapped_values = set(self.column_mapping.values())
        if self.import_mode == "positions":
            required = {"ticker", "quantity"}
        else:
            required = {"account_number", "amount", "title"}
        return required.issubset(mapped_values)

    @rx.var
    def has_unresolved_tickers(self) -> bool:
        return len(self.unresolved_tickers) > 0

    @rx.var
    def has_unknown_accounts(self) -> bool:
        return len(self.unknown_accounts) > 0

    @rx.var
    def all_accounts_configured(self) -> bool:
        """Check if all unknown accounts have bank and currency set."""
        return all(
            acct in self.new_account_details
            and self.new_account_details[acct].get("bank")
            and self.new_account_details[acct].get("currency")
            for acct in self.unknown_accounts
        )

    @rx.event
    def set_import_mode(self, mode: str | list[str]) -> None:
        """Switch between positions and cash import mode."""
        if isinstance(mode, list):
            mode = mode[0] if mode else "positions"
        self.import_mode = mode
        self.column_mapping = {}

    @rx.event
    def set_delimiter(self, value: str) -> None:
        """Set the CSV delimiter."""
        self.delimiter = value

    @rx.event
    def reset_wizard(self) -> None:
        """Reset all state to start fresh."""
        self.step = 1
        self.filename = ""
        self._file_bytes = b""
        self._source_path = ""
        self.delimiter = ","
        self.file_columns = []
        self.preview_rows = []
        self.column_mapping = {}
        self.unresolved_tickers = []
        self.asset_type_overrides = {}
        self.unknown_accounts = []
        self.new_account_details = {}
        self.result_message = ""
        self.result_success = False
        self.result_errors = []
        self.is_loading = False

    @rx.event
    async def handle_upload(self, files: list[rx.UploadFile]):
        """Handle file upload from rx.upload (browser fallback)."""
        if not files:
            return

        file = files[0]
        self.filename = file.filename or "unknown"
        upload_data = await file.read()
        self._file_bytes = upload_data
        self._source_path = ""  # No original path available in browser mode

        try:
            columns, preview = FileConnectorService.read_file(
                self._file_bytes, self.filename, self.delimiter
            )
            self.file_columns = columns
            self.preview_rows = preview
            # Initialize mapping with empty values
            self.column_mapping = {col: "" for col in columns}
            self.step = 2
        except Exception as e:
            yield rx.toast.error(f"Failed to read file: {e}", position="top-center")

    @rx.event
    def handle_file_path(self, path: str):
        """Handle file selection from Tauri native dialog (full path)."""
        if not path:
            return

        file_path = Path(path)
        if not file_path.is_file():
            yield rx.toast.error(f"File not found: {path}", position="top-center")
            return

        self.filename = file_path.name
        self._file_bytes = file_path.read_bytes()
        self._source_path = str(file_path)

        try:
            columns, preview = FileConnectorService.read_file(
                self._file_bytes, self.filename, self.delimiter
            )
            self.file_columns = columns
            self.preview_rows = preview
            self.column_mapping = {col: "" for col in columns}
            self.step = 2
        except Exception as e:
            yield rx.toast.error(f"Failed to read file: {e}", position="top-center")

    @rx.event
    def reparse_file(self):
        """Re-parse the file with a new delimiter (for CSV)."""
        if not self._file_bytes:
            return
        try:
            columns, preview = FileConnectorService.read_file(
                self._file_bytes, self.filename, self.delimiter
            )
            self.file_columns = columns
            self.preview_rows = preview
            self.column_mapping = {col: "" for col in columns}
        except Exception as e:
            yield rx.toast.error(f"Failed to re-parse file: {e}", position="top-center")

    @rx.event
    def set_column_mapping(self, file_column: str, target_field: str) -> None:
        """Set the mapping for one file column."""
        # Clear any previous mapping to this target to avoid duplicates
        for col, target in self.column_mapping.items():
            if target == target_field and col != file_column and target_field != "":
                self.column_mapping[col] = ""
        self.column_mapping[file_column] = target_field

    @rx.event
    def proceed_to_review(self):
        """Validate mapping and move to step 3 (review / asset type resolution)."""
        if not self.mapping_valid:
            yield rx.toast.error(
                "Please map all required fields before proceeding.",
                position="top-center",
            )
            return

        self.is_loading = True
        yield

        if self.import_mode == "positions":
            self._resolve_tickers()
        else:
            # For cash, detect unknown accounts
            clean_mapping = {k: v for k, v in self.column_mapping.items() if v}
            self.unknown_accounts = FileConnectorService.detect_unknown_cash_accounts(
                self._file_bytes, self.filename, clean_mapping, self.delimiter
            )
            self.new_account_details = {}

        self.is_loading = False
        self.step = 3

    def _resolve_tickers(self) -> None:
        """Resolve asset types for tickers found in the file."""
        ticker_col = None
        for col, target in self.column_mapping.items():
            if target == "ticker":
                ticker_col = col
                break
        if not ticker_col:
            return

        all_rows = FileConnectorService.read_file_full(
            self._file_bytes, self.filename, self.delimiter
        )

        # Collect unique non-empty tickers (handle None values from polars)
        tickers = list(
            {
                str(v).strip().upper()
                for row in all_rows
                if (v := row.get(ticker_col)) is not None and str(v).strip()
            }
        )
        if not tickers:
            return

        resolved = FileConnectorService.resolve_asset_types(tickers)
        self.unresolved_tickers = [t for t, at in resolved.items() if at is None]
        self.asset_type_overrides = {
            t: at for t, at in resolved.items() if at is not None
        }

    @rx.event
    def set_asset_type_override(self, ticker: str, asset_type: str) -> None:
        """Manually set the asset type for an unresolved ticker."""
        self.asset_type_overrides[ticker] = asset_type

    @rx.event
    def set_account_bank(self, account: str, bank: str) -> None:
        """Set the bank name for a new cash account."""
        if account not in self.new_account_details:
            self.new_account_details[account] = {}
        self.new_account_details[account]["bank"] = bank

    @rx.event
    def set_account_currency(self, account: str, currency: str) -> None:
        """Set the currency for a new cash account."""
        if account not in self.new_account_details:
            self.new_account_details[account] = {}
        self.new_account_details[account]["currency"] = currency

    @rx.var
    def all_tickers_resolved(self) -> bool:
        """Check if all unresolved tickers have been assigned an asset type."""
        return all(t in self.asset_type_overrides for t in self.unresolved_tickers)

    @rx.var
    def can_import(self) -> bool:
        """Whether the import can proceed."""
        if self.import_mode == "positions":
            return self.mapping_valid and self.all_tickers_resolved
        if self.unknown_accounts:
            return self.mapping_valid and self.all_accounts_configured
        return self.mapping_valid

    @rx.event
    def run_import(self):
        """Execute the import."""
        self.is_loading = True
        yield

        # Build clean mapping (only non-empty)
        clean_mapping = {k: v for k, v in self.column_mapping.items() if v}

        if self.import_mode == "positions":
            result = FileConnectorService.import_positions(
                file_bytes=self._file_bytes,
                filename=self.filename,
                column_mapping=clean_mapping,
                delimiter=self.delimiter,
                asset_type_overrides=self.asset_type_overrides,
                source_path=self._source_path,
            )
        else:
            result = FileConnectorService.import_cash_operations(
                file_bytes=self._file_bytes,
                filename=self.filename,
                column_mapping=clean_mapping,
                delimiter=self.delimiter,
                new_accounts=self.new_account_details
                if self.unknown_accounts
                else None,
                source_path=self._source_path,
            )

        self.result_message = result.message
        self.result_success = result.success
        self.result_errors = result.data.get("errors", []) if result.data else []
        self.is_loading = False
        self.step = 4

        if result.success:
            yield rx.toast.success(result.message, position="top-center")
        else:
            yield rx.toast.error(result.message, position="top-center")

    @rx.event
    def go_back(self) -> None:
        """Go back one step."""
        if self.step > 1:
            self.step -= 1
