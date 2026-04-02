"""State for connector history display and refresh operations."""

import reflex as rx

from ..config.file_connector_config import file_connector_paths
from ..services import (
    ConnectorHistoryService,
    CredentialService,
    FileConnectorService,
    WebConnectorService,
)
from ..templates.template import ThemeState


class ConnectorHistoryState(rx.State):
    """State for the connector history section on the connectors page."""

    history_entries: list[dict] = []
    is_refreshing_id: int = 0  # ID of the entry currently being refreshed (0=none)

    # Master password unlock dialog for refresh
    show_unlock_dialog: bool = False
    _pending_refresh_id: int = 0
    master_password_input: str = ""

    # Detail dialog for file connector entries
    show_detail_dialog: bool = False
    detail_entry_id: int = 0
    detail_source_name: str = ""
    detail_source_path: str = ""
    detail_path_input: str = ""

    @rx.var
    def has_history(self) -> bool:
        return len(self.history_entries) > 0

    @rx.event
    def load_history(self) -> None:
        """Load all connector history entries."""
        self.history_entries = ConnectorHistoryService.get_all()

    @rx.event
    def delete_entry(self, entry_id: int):
        """Delete a history entry."""
        success = ConnectorHistoryService.delete(entry_id)
        if success:
            self.history_entries = [
                e for e in self.history_entries if e["id"] != entry_id
            ]
            yield rx.toast.success("History entry deleted.", position="top-center")
        else:
            yield rx.toast.error(
                "Failed to delete history entry.", position="top-center"
            )

    @rx.event
    def set_master_password_input(self, value: str):
        self.master_password_input = value

    @rx.event
    def cancel_unlock(self):
        self.show_unlock_dialog = False
        self._pending_refresh_id = 0
        self.master_password_input = ""

    @rx.event
    def open_detail(self, entry_id: int):
        """Open the detail dialog for a file connector entry."""
        for e in self.history_entries:
            if e["id"] == entry_id:
                stored_path = file_connector_paths.get(entry_id)
                path = stored_path or e.get("source_path", "")
                self.detail_entry_id = entry_id
                self.detail_source_name = e.get("source_name", "")
                self.detail_source_path = path
                self.detail_path_input = path
                self.show_detail_dialog = True
                return

    @rx.event
    def set_detail_path_input(self, value: str):
        self.detail_path_input = value

    @rx.event
    def save_detail_path(self):
        """Save the edited path to the JSON config."""
        file_connector_paths.set(self.detail_entry_id, self.detail_path_input)
        self.detail_source_path = self.detail_path_input
        self.show_detail_dialog = False
        yield rx.toast.success("Source path updated.", position="top-center")

    @rx.event
    def cancel_detail(self):
        self.show_detail_dialog = False

    @rx.event
    def submit_unlock_and_refresh(self):
        """Unlock credentials and retry the pending refresh."""
        success = CredentialService.unlock(self.master_password_input)
        self.master_password_input = ""
        self.show_unlock_dialog = False

        if success:
            yield rx.toast.success("Credentials unlocked!", position="top-center")
            yield ConnectorHistoryState.refresh_entry(self._pending_refresh_id)
        else:
            self._pending_refresh_id = 0
            yield rx.toast.error("Incorrect master password.", position="top-center")

    @rx.event
    async def refresh_entry(self, entry_id: int):
        """Re-run a specific connector from history."""
        entry = None
        for e in self.history_entries:
            if e["id"] == entry_id:
                entry = e
                break

        if not entry:
            yield rx.toast.error("History entry not found.", position="top-center")
            return

        if entry["connector_type"] == "file":
            self.is_refreshing_id = entry_id
            yield rx.toast.info("Re-importing file...", position="top-center")
            yield

            result = FileConnectorService.reimport_from_history(entry)

            self.is_refreshing_id = 0
            self.history_entries = ConnectorHistoryService.get_all()

            if result.success:
                yield rx.toast.success(result.message, position="top-center")
            else:
                yield rx.toast.error(result.message, position="top-center")
            return

        # Web connector refresh — need credentials
        profile_id = entry["profile_id"]
        if not profile_id:
            yield rx.toast.error(
                "No profile associated with this entry.", position="top-center"
            )
            return

        # Try to get stored credentials
        creds = CredentialService.get_credentials(profile_id)
        if not creds:
            # Check if credentials exist but vault is locked
            if (
                CredentialService.has_master_password()
                and not CredentialService.is_unlocked()
            ):
                self._pending_refresh_id = entry_id
                self.show_unlock_dialog = True
                return

            yield rx.toast.error(
                "No saved credentials found. Please run the web connector "
                "wizard to save credentials first.",
                position="top-center",
            )
            return

        self.is_refreshing_id = entry_id
        yield rx.toast.info("Refreshing connector...", position="top-center")
        yield

        theme = await self.get_state(ThemeState)

        result = WebConnectorService.run_connector(
            profile_id=profile_id,
            credentials={"username": creds[0], "password": creds[1]},
            headless=not theme.show_browser,
        )

        self.is_refreshing_id = 0
        self.history_entries = ConnectorHistoryService.get_all()

        if result.success:
            yield rx.toast.success(result.message, position="top-center")
        else:
            yield rx.toast.error(result.message, position="top-center")
