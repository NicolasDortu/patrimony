"""Mixin providing editable spreadsheet mode for table states.

Everything stays in memory until the user hits "Save changes":
  * ``rows_state``      - the live grid (1:1 with what the user sees)
  * ``pending_deletes`` - DB ids whose rows the user removed in this session

Row identity is tracked by uuid + ``db_id`` (None = brand-new row), so
display-index shifts after deletes/inserts stay safe.

NOTE: We deliberately do NOT subscribe to ``on_grid_selection_change``.
Wiring any handler there - even one that only writes a backend-only var
- forces a server round-trip on every click/drag, which interrupts
Glide's internal cell-edit overlay AND wipes the selection highlight.
Deletion is handled by the keyboard Delete key (``on_delete``), which
carries the current selection in its event payload.

Subclass contract:
  - ``spreadsheet_columns`` (@rx.var)
  - ``_load_spreadsheet_rows() -> (list[list], list)``  (data, ids)
  - ``_save_spreadsheet_row(row, index, rid, is_new) -> str | None``
  - ``_delete_spreadsheet_row(rid)``
  - ``_after_spreadsheet_save()``  (async)
"""

from uuid import uuid4

import reflex as rx


_CLEAN = "clean"
_DIRTY = "dirty"


def _make_row(db_id, data: list, state: str = _CLEAN) -> dict:
    return {
        "uuid": uuid4().hex,
        "db_id": db_id,
        "state": state,
        "data": list(data),
        "original": list(data),
    }


def _selection_to_indices(selection, row_count: int) -> set[int]:
    """Extract visible row indices from a Glide GridSelection payload.

    Defensive against both ``{"items": [[s, e), ...]}`` and flat-list
    shapes, and clamps every range to the current grid size.
    """
    if not isinstance(selection, dict):
        return set()
    rows = selection.get("rows")
    items = rows.get("items") if isinstance(rows, dict) else rows
    if not isinstance(items, list):
        return set()

    out: set[int] = set()
    for item in items:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            try:
                start, end = int(item[0]), int(item[1])
            except (TypeError, ValueError):
                continue
            for i in range(max(0, start), min(row_count, end)):
                out.add(i)
        elif isinstance(item, int) and 0 <= item < row_count:
            out.add(item)
    return out


class SpreadsheetMixin(rx.State, mixin=True):
    """Shared spreadsheet editing infrastructure."""

    spreadsheet_mode: bool = False
    rows_state: list[dict] = []
    pending_deletes: list = []

    # Glide's keybindings handler clears the cells of every deleted row
    # immediately after our `on_delete` returns, firing `on_cell_edited` for
    # each cell with an empty value. By the time those events reach the
    # backend, our `rows_state` has already shrunk, so the indices now point
    # at the row that took the deleted row's slot. Without this counter,
    # the row right after the deleted one gets silently blanked. We count
    # how many post-delete blanking events to swallow.
    _post_delete_skip: int = 0

    # -- Display vars --

    @rx.var
    def spreadsheet_data(self) -> list[list]:
        return [r["data"] for r in self.rows_state]

    @rx.var
    def spreadsheet_row_count(self) -> int:
        return len(self.rows_state)

    @rx.var
    def has_unsaved_changes(self) -> bool:
        return bool(self.pending_deletes) or any(
            r["state"] != _CLEAN or r["db_id"] is None for r in self.rows_state
        )

    # -- Internal helpers --

    def _blank_row_data(self) -> list:
        defaults = []
        for c in self.spreadsheet_columns or []:
            t = c.get("type", "str") if isinstance(c, dict) else "str"
            defaults.append(
                0 if t in ("int", "float") else False if t == "bool" else ""
            )
        return defaults

    def _row_at_visible_index(self, idx: int) -> dict | None:
        if 0 <= idx < len(self.rows_state):
            return self.rows_state[idx]
        return None

    def _replace_row(self, uuid: str, mutator) -> None:
        """Apply ``mutator(row)`` in-place to the row with this uuid."""
        new_rows = []
        for r in self.rows_state:
            if r["uuid"] == uuid:
                r = {**r, "data": list(r["data"])}
                mutator(r)
            new_rows.append(r)
        self.rows_state = new_rows

    def _consume_post_delete_blank(self) -> bool:
        """Return True if this cell-edit is Glide's post-delete blanking and
        should be ignored. Subclasses overriding ``on_spreadsheet_cell_edited``
        must call this at the top of their handler."""
        if self._post_delete_skip > 0:
            self._post_delete_skip -= 1
            return True
        return False

    # -- Event handlers --

    @rx.event
    def on_spreadsheet_cell_edited(self, pos: tuple[int, int], cell: dict) -> None:
        if self._consume_post_delete_blank():
            return
        col, row_idx = pos
        if not (0 <= row_idx < len(self.rows_state)):
            return
        target = self.rows_state[row_idx]
        if not (0 <= col < len(target["data"])):
            return

        new_data = list(target["data"])
        new_data[col] = cell.get("data", "")
        new_state = (
            _DIRTY
            if target["state"] == _CLEAN and new_data != target["original"]
            else target["state"]
        )
        new_rows = list(self.rows_state)
        new_rows[row_idx] = {**target, "data": new_data, "state": new_state}
        self.rows_state = new_rows

    @rx.event
    def on_spreadsheet_delete(self, selection: dict) -> None:
        """Keyboard Delete - drop the currently-selected rows."""
        indices = _selection_to_indices(selection, len(self.rows_state))
        if not indices:
            return
        keep, deletes = [], list(self.pending_deletes)
        for i, r in enumerate(self.rows_state):
            if i in indices:
                if r["db_id"] is not None:
                    deletes.append(r["db_id"])
            else:
                keep.append(r)
        self.rows_state = keep
        self.pending_deletes = deletes
        # Glide will now fire on_cell_edited("") for every cell of every
        # deleted row plus its current.range cell. Pre-arm the skip counter
        # so those stale events don't blank the row that took the slot.
        cols = len(self.spreadsheet_columns or [])
        self._post_delete_skip += len(indices) * max(cols, 1) + cols

    @rx.event
    def on_spreadsheet_row_appended(self) -> None:
        """Append a blank in-memory row (persisted only on Save)."""
        self.rows_state = list(self.rows_state) + [
            _make_row(None, self._blank_row_data(), _DIRTY)
        ]

    @rx.event
    def discard_spreadsheet_changes(self) -> None:
        self._exit_spreadsheet_mode()

    def _exit_spreadsheet_mode(self) -> None:
        self.spreadsheet_mode = False
        self.rows_state = []
        self.pending_deletes = []
        self._post_delete_skip = 0

    # -- Override points for concrete states --

    def _load_spreadsheet_rows(self) -> tuple[list[list], list]:
        return [], []

    def _save_spreadsheet_row(self, row: list, index: int, rid, is_new: bool):
        return None

    def _delete_spreadsheet_row(self, rid) -> None:
        pass

    async def _after_spreadsheet_save(self) -> None:
        pass

    # -- Mode toggle / save --

    @rx.event
    def toggle_spreadsheet_mode(self) -> None:
        if self.spreadsheet_mode:
            self._exit_spreadsheet_mode()
            return
        data, ids = self._load_spreadsheet_rows()
        rows = [_make_row(rid, row) for row, rid in zip(data, ids)]
        # Glide-data-grid can hit a "Maximum update depth exceeded" loop when
        # the grid is mounted with zero rows (its column auto-sizer keeps
        # firing without any cell to measure against). Always start with at
        # least one row so the grid has something to render.
        if not rows:
            rows = [_make_row(None, self._blank_row_data(), _DIRTY)]
        self.rows_state = rows
        self.pending_deletes = []
        self._post_delete_skip = 0
        self.spreadsheet_mode = True

    @rx.event
    async def save_spreadsheet_changes(self):
        """Persist all pending changes. Stay in edit mode if anything fails."""
        errors: list[str] = []
        survivors: list[dict] = []
        deletes_left: list = []

        # 1. Apply queued deletes first so updates can't conflict with them.
        for rid in self.pending_deletes:
            try:
                self._delete_spreadsheet_row(rid)
            except Exception as e:
                errors.append(f"Delete: {e}")
                deletes_left.append(rid)

        # 2. Create or update each surviving row.
        for i, r in enumerate(self.rows_state):
            is_new = r["db_id"] is None
            if r["state"] == _CLEAN and not is_new:
                survivors.append(r)
                continue
            try:
                result = self._save_spreadsheet_row(r["data"], i, r["db_id"], is_new)
                if result == "skip":
                    if not is_new:
                        survivors.append(r)
                elif result:
                    errors.append(result)
                    survivors.append(r)
            except Exception as e:
                errors.append(f"Row {i + 1}: {e}")
                survivors.append(r)

        if errors:
            self.rows_state = survivors
            self.pending_deletes = deletes_left
            await self._after_spreadsheet_save()
            return rx.toast.error(
                f"Saved with {len(errors)} error(s) - fix and retry",
                position="top-center",
            )

        self._exit_spreadsheet_mode()
        await self._after_spreadsheet_save()
        return rx.toast.success("Changes saved", position="top-center")
