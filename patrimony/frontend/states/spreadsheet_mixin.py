"""Mixin providing editable spreadsheet mode for table states."""

import reflex as rx


class SpreadsheetMixin(rx.State, mixin=True):
    """Shared spreadsheet editing infrastructure.

    Concrete states must implement:
    - enter_spreadsheet_mode(): populate _spreadsheet_data, _row_ids
    - save_spreadsheet_changes(): diff and persist to DB
    - spreadsheet_columns @rx.var: column definitions for the grid
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
