"""Mixin providing editable spreadsheet mode for table states."""

import reflex as rx


class SpreadsheetMixin(rx.State, mixin=True):
    """Shared spreadsheet editing infrastructure.

    Concrete states must implement:
    - spreadsheet_columns @rx.var: column definitions for the grid
    - _load_spreadsheet_rows() -> tuple[list[list], list]: load data + row ids
    - _save_spreadsheet_row(row, index, rid, is_new) -> str|None: persist one row
    - _delete_spreadsheet_row(rid): delete a removed row
    - _after_spreadsheet_save(): reload entries after save (can be async)
    """

    spreadsheet_mode: bool = False
    _spreadsheet_data: list[list] = []
    _row_ids: list = []  # Maps row index → DB identifier (int id or str key; None for new rows)
    _deleted_ids: list = []
    _has_edits: bool = False

    @rx.var
    def spreadsheet_data(self) -> list[list]:
        return self._spreadsheet_data

    @rx.var
    def spreadsheet_row_count(self) -> int:
        return len(self._spreadsheet_data)

    @rx.var
    def has_unsaved_changes(self) -> bool:
        return self._has_edits

    @rx.event
    def on_spreadsheet_cell_edited(self, pos: tuple[int, int], cell: dict) -> None:
        """Handle a cell edit from the data editor."""
        col, row = pos
        if 0 <= row < len(self._spreadsheet_data) and 0 <= col < len(
            self._spreadsheet_data[row]
        ):
            new_data = [r[:] for r in self._spreadsheet_data]
            new_data[row][col] = cell.get("data", "")
            self._spreadsheet_data = new_data
            self._has_edits = True

    @rx.event
    def on_spreadsheet_row_appended(self) -> None:
        """Handle trailing row append from the data editor."""
        if not self._spreadsheet_data:
            return
        col_count = len(self._spreadsheet_data[0]) if self._spreadsheet_data else 0
        blank = [""] * col_count
        self._spreadsheet_data = [r[:] for r in self._spreadsheet_data] + [blank]
        self._row_ids = list(self._row_ids) + [None]
        self._has_edits = True

    @rx.event
    def on_spreadsheet_delete(self, selection: dict) -> None:
        """Handle delete key press — remove selected rows."""
        row_items = selection.get("rows", {}).get("items", [])
        indices_to_delete: set[int] = set()
        for item in row_items:
            if isinstance(item, list) and len(item) == 2:
                for i in range(item[0], item[1]):
                    indices_to_delete.add(i)
            elif isinstance(item, int):
                indices_to_delete.add(item)

        if not indices_to_delete:
            return

        for idx in indices_to_delete:
            if 0 <= idx < len(self._row_ids) and self._row_ids[idx] is not None:
                self._deleted_ids = list(self._deleted_ids) + [self._row_ids[idx]]

        new_data = [
            r
            for i, r in enumerate(self._spreadsheet_data)
            if i not in indices_to_delete
        ]
        new_ids = [
            rid for i, rid in enumerate(self._row_ids) if i not in indices_to_delete
        ]
        self._spreadsheet_data = new_data
        self._row_ids = new_ids
        self._has_edits = True

    @rx.event
    def discard_spreadsheet_changes(self) -> None:
        """Discard all pending changes and exit spreadsheet mode."""
        self.spreadsheet_mode = False
        self._spreadsheet_data = []
        self._row_ids = []
        self._deleted_ids = []
        self._has_edits = False

    def _exit_spreadsheet_mode(self) -> None:
        """Clean up spreadsheet state after saving."""
        self.spreadsheet_mode = False
        self._spreadsheet_data = []
        self._row_ids = []
        self._deleted_ids = []
        self._has_edits = False

    # ── Override points for concrete states ──

    def _load_spreadsheet_rows(self) -> tuple[list[list], list]:
        """Load data rows and their IDs. Override in subclass."""
        return [], []

    def _save_spreadsheet_row(self, row: list, index: int, rid, is_new: bool):
        """Save a single row. Return error string to report, or None.
        Return 'skip' to silently skip the row. Override in subclass."""
        return None

    def _delete_spreadsheet_row(self, rid) -> None:
        """Delete a removed row by its ID. Override in subclass."""
        pass

    async def _after_spreadsheet_save(self) -> None:
        """Called after save completes. Override to reload entries."""
        pass

    @rx.event
    def toggle_spreadsheet_mode(self) -> None:
        """Toggle between normal table view and spreadsheet editing mode."""
        if not self.spreadsheet_mode:
            data, ids = self._load_spreadsheet_rows()
            self._spreadsheet_data = data
            self._row_ids = ids
            self._deleted_ids = []
            self._has_edits = False
            self.spreadsheet_mode = True
        else:
            self._exit_spreadsheet_mode()

    @rx.event
    async def save_spreadsheet_changes(self) -> None:
        """Save all pending spreadsheet changes (updates, inserts, deletes)."""
        errors: list[str] = []

        for i, row in enumerate(self._spreadsheet_data):
            rid = self._row_ids[i] if i < len(self._row_ids) else None
            is_new = rid is None
            try:
                result = self._save_spreadsheet_row(row, i, rid, is_new)
                if result and result != "skip":
                    errors.append(result)
            except Exception as e:
                errors.append(f"Row {i + 1}: {e}")

        for del_id in self._deleted_ids:
            self._delete_spreadsheet_row(del_id)

        self._exit_spreadsheet_mode()
        await self._after_spreadsheet_save()

        if errors:
            return rx.toast.error(
                f"Saved with {len(errors)} error(s)", position="top-center"
            )
        return rx.toast.success("Changes saved", position="top-center")
