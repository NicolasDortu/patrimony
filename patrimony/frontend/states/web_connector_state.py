"""State for the web connector wizard (browser-based automated import)."""

import logging

import reflex as rx

from ..services import CredentialService, WebConnectorService
from ..templates.template import ThemeState

logger = logging.getLogger(__name__)


class WebConnectorState(rx.State):
    """Multi-step wizard state for web connector import.

    Steps:
        1. Select a connector profile
        2. Enter credentials (with optional master password unlock)
        3. Running (browser automation in progress)
        4. Result
    """

    # Wizard step: 1=profile, 2=credentials, 3=running, 4=result
    step: int = 1

    # Available profiles loaded from backend
    profiles: list[dict] = []

    # Selected profile
    selected_profile_id: str = ""
    selected_profile_name: str = ""
    selected_profile_description: str = ""
    selected_profile_import_mode: str = ""

    # Credentials (never persisted in state — held in memory only)
    username: str = ""
    password: str = ""

    # Master password / credential storage
    master_password_input: str = ""
    needs_master_setup: bool = False
    needs_master_unlock: bool = False
    has_saved_credentials: bool = False
    save_credentials_checked: bool = False

    # Running state
    is_running: bool = False
    status_messages: list[str] = []

    # Result
    result_message: str = ""
    result_success: bool = False
    result_errors: list[str] = []
    result_imported: int = 0
    result_skipped: int = 0
    result_status_log: list[str] = []

    @rx.var
    def has_profiles(self) -> bool:
        return len(self.profiles) > 0

    @rx.var
    def has_selection(self) -> bool:
        return self.selected_profile_id != ""

    @rx.var
    def credentials_valid(self) -> bool:
        return self.username.strip() != "" and self.password.strip() != ""

    @rx.var
    def show_credential_lock(self) -> bool:
        """Whether the master password lock overlay should be shown."""
        return self.needs_master_setup or self.needs_master_unlock

    @rx.event
    def load_profiles(self) -> None:
        """Load available connector profiles from the backend."""
        self.profiles = WebConnectorService.list_profiles()

    @rx.event
    def select_profile(self, profile_id: str) -> None:
        """Select a connector profile and advance to credentials step."""
        self.selected_profile_id = profile_id
        for p in self.profiles:
            if p["id"] == profile_id:
                self.selected_profile_name = p["name"]
                self.selected_profile_description = p.get("description", "")
                self.selected_profile_import_mode = p.get("import_mode", "positions")
                break

        # Check credential storage status
        self._check_credential_status(profile_id)
        self.step = 2

    def _check_credential_status(self, profile_id: str) -> None:
        """Determine master password / credential state for the selected profile."""
        if not CredentialService.has_master_password():
            self.needs_master_setup = True
            self.needs_master_unlock = False
            self.has_saved_credentials = False
        elif not CredentialService.is_unlocked():
            self.needs_master_setup = False
            self.needs_master_unlock = True
            self.has_saved_credentials = False
        else:
            self.needs_master_setup = False
            self.needs_master_unlock = False
            creds = CredentialService.get_credentials(profile_id)
            if creds:
                self.username, self.password = creds
                self.has_saved_credentials = True
            else:
                self.has_saved_credentials = False

    @rx.event
    def set_username(self, value: str) -> None:
        self.username = value

    @rx.event
    def set_password(self, value: str) -> None:
        self.password = value

    @rx.event
    def set_master_password_input(self, value: str) -> None:
        self.master_password_input = value

    @rx.event
    def toggle_save_credentials(self, checked: bool) -> None:
        self.save_credentials_checked = checked

    @rx.event
    def setup_master_password(self):
        """Create a new master password."""
        if len(self.master_password_input) < 4:
            yield rx.toast.error(
                "Master password must be at least 4 characters.",
                position="top-center",
            )
            return

        success = CredentialService.setup_master_password(self.master_password_input)
        self.master_password_input = ""

        if success:
            self.needs_master_setup = False
            self.needs_master_unlock = False
            yield rx.toast.success("Master password set!", position="top-center")
        else:
            yield rx.toast.error(
                "Failed to set master password.", position="top-center"
            )

    @rx.event
    def unlock_master_password(self):
        """Unlock credential storage with master password."""
        success = CredentialService.unlock(self.master_password_input)
        self.master_password_input = ""

        if success:
            self.needs_master_unlock = False
            # Try to load saved credentials for selected profile
            creds = CredentialService.get_credentials(self.selected_profile_id)
            if creds:
                self.username, self.password = creds
                self.has_saved_credentials = True
            yield rx.toast.success("Credentials unlocked!", position="top-center")
        else:
            yield rx.toast.error("Incorrect master password.", position="top-center")

    @rx.event
    def delete_saved_credentials(self):
        """Delete stored credentials for the selected profile."""
        CredentialService.delete_credentials(self.selected_profile_id)
        self.has_saved_credentials = False
        self.username = ""
        self.password = ""
        yield rx.toast.info("Saved credentials deleted.", position="top-center")

    @rx.event
    async def start_connector(self):
        """Validate credentials and start the browser automation."""
        if not self.credentials_valid:
            yield rx.toast.error(
                "Please enter both username and password.",
                position="top-center",
            )
            return

        # Save credentials if requested and vault is unlocked
        if self.save_credentials_checked and CredentialService.is_unlocked():
            CredentialService.store_credentials(
                self.selected_profile_id, self.username, self.password
            )
            self.has_saved_credentials = True

        self.step = 3
        self.is_running = True
        self.status_messages = ["Starting connector..."]
        yield

        theme = await self.get_state(ThemeState)

        result = WebConnectorService.run_connector(
            profile_id=self.selected_profile_id,
            credentials={
                "username": self.username,
                "password": self.password,
            },
            headless=not theme.show_browser,
        )

        # Clear credentials from memory immediately after use
        self.username = ""
        self.password = ""

        self.is_running = False
        self.result_message = result.message
        self.result_success = result.success

        data = result.data or {}
        self.result_errors = data.get("errors", [])
        self.result_imported = data.get("imported", 0)
        self.result_skipped = data.get("skipped", 0)
        self.result_status_log = data.get("status_log", [])
        self.status_messages = data.get("status_log", [])

        self.step = 4

        if result.success:
            yield rx.toast.success(result.message, position="top-center")
        else:
            yield rx.toast.error(result.message, position="top-center")

    @rx.event
    def reset_wizard(self) -> None:
        """Reset all state to start fresh."""
        self.step = 1
        self.selected_profile_id = ""
        self.selected_profile_name = ""
        self.selected_profile_description = ""
        self.selected_profile_import_mode = ""
        self.username = ""
        self.password = ""
        self.master_password_input = ""
        self.needs_master_setup = False
        self.needs_master_unlock = False
        self.has_saved_credentials = False
        self.save_credentials_checked = False
        self.is_running = False
        self.status_messages = []
        self.result_message = ""
        self.result_success = False
        self.result_errors = []
        self.result_imported = 0
        self.result_skipped = 0
        self.result_status_log = []

    @rx.event
    def go_back(self) -> None:
        """Go back one step."""
        if self.step == 2:
            self.step = 1
            self.selected_profile_id = ""
            self.selected_profile_name = ""
            self.username = ""
            self.password = ""
        elif self.step > 2:
            self.step -= 1
