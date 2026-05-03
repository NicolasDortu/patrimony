"""State for the web connector wizard (browser-based automated import)."""

import asyncio
import threading

import reflex as rx

from ..services import CredentialService, WebConnectorService
from ..templates.template import ThemeState


# Module-level bridge for OTP prompt between Playwright thread and Reflex state.
class _BridgeContext:
    """Inter-thread communication for OTP prompts between Playwright and Reflex."""

    __slots__ = (
        "need_input",
        "got_response",
        "prompt_type",
        "prompt_message",
        "prompt_image",
        "response",
    )

    def __init__(self):
        self.need_input = threading.Event()
        self.got_response = threading.Event()
        self.prompt_type = ""
        self.prompt_message = ""
        self.prompt_image = ""
        self.response = ""


_bridge = _BridgeContext()


class WebConnectorState(rx.State):
    """Multi-step wizard state for web connector import.

    Steps:
        1. Select a connector profile
        2. Enter credentials (with optional master password unlock)
        3. Running (browser automation in progress)
        4. Matching (user maps names→tickers, only for needs_matching profiles)
        5. Result
    """

    # Wizard step: 1=profile, 2=credentials, 3=running, 4=matching, 5=result
    step: int = 1

    # Available profiles loaded from backend
    profiles: list[dict] = []

    # Selected profile
    selected_profile_id: str = ""
    selected_profile_name: str = ""
    selected_profile_description: str = ""
    selected_profile_import_mode: str = ""
    selected_profile_needs_matching: bool = False

    # Dynamic credential fields from the selected profile
    # Each entry: {"placeholder": "$user$", "label": "Username", "type": "text", "value": ""}
    credential_fields: list[dict] = []

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

    # OTP / interactive prompt dialog (shown during step 3)
    prompt_visible: bool = False
    prompt_message: str = ""
    prompt_type: str = ""  # "text", "action", or "qr"
    prompt_input: str = ""
    prompt_image: str = ""  # base64 data URL for QR code display

    # Matching step (step 4, conditional)
    unmatched_positions: list[dict] = []

    @rx.var
    def has_profiles(self) -> bool:
        return len(self.profiles) > 0

    @rx.var
    def has_selection(self) -> bool:
        return self.selected_profile_id != ""

    @rx.var
    def credentials_valid(self) -> bool:
        if not self.credential_fields:
            return True  # No credentials needed (e.g. QR-code login)
        return all(f.get("value", "").strip() != "" for f in self.credential_fields)

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
                self.selected_profile_needs_matching = p.get("needs_matching", False)
                self.credential_fields = [
                    {**f, "value": ""} for f in p.get("credential_fields", [])
                ]
                break

        # Check credential storage status (skip for connectors with no credentials)
        if self.credential_fields:
            self._check_credential_status(profile_id)
        else:
            self.needs_master_setup = False
            self.needs_master_unlock = False
            self.has_saved_credentials = False
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
                for f in self.credential_fields:
                    f["value"] = creds.get(f["placeholder"], "")
                self.has_saved_credentials = True
            else:
                self.has_saved_credentials = False

    @rx.event
    def set_credential_value(self, index: int, value: str) -> None:
        self.credential_fields[index]["value"] = value

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

        result = CredentialService.setup_master_password(self.master_password_input)
        self.master_password_input = ""

        if result.success:
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
        result = CredentialService.unlock(self.master_password_input)
        self.master_password_input = ""

        if result.success:
            self.needs_master_unlock = False
            # Try to load saved credentials for selected profile
            creds = CredentialService.get_credentials(self.selected_profile_id)
            if creds:
                for f in self.credential_fields:
                    f["value"] = creds.get(f["placeholder"], "")
                self.has_saved_credentials = True
            yield rx.toast.success("Credentials unlocked!", position="top-center")
        else:
            yield rx.toast.error("Incorrect master password.", position="top-center")

    @rx.event
    def delete_saved_credentials(self):
        """Delete stored credentials for the selected profile."""
        CredentialService.delete_credentials(self.selected_profile_id)
        self.has_saved_credentials = False
        for f in self.credential_fields:
            f["value"] = ""
        yield rx.toast.info("Saved credentials deleted.", position="top-center")

    @rx.event
    def set_prompt_input(self, value: str) -> None:
        self.prompt_input = value

    @rx.event
    def submit_prompt(self) -> None:
        """User submitted the OTP / prompt dialog — unblock the connector thread."""
        _bridge.response = self.prompt_input
        self.prompt_input = ""
        self.prompt_image = ""
        self.prompt_visible = False
        _bridge.got_response.set()

    @rx.event(background=True)
    async def start_connector(self):
        """Validate credentials and start the browser automation.

        Runs as a background task so we can push OTP dialog state changes
        to the frontend while the connector is still running.
        """
        async with self:
            if not self.credentials_valid:
                yield rx.toast.error(
                    "Please fill in all credential fields.",
                    position="top-center",
                )
                return

            # Save credentials if requested and vault is unlocked
            if self.save_credentials_checked and CredentialService.is_unlocked():
                creds = {f["placeholder"]: f["value"] for f in self.credential_fields}
                CredentialService.store_credentials(self.selected_profile_id, creds)
                self.has_saved_credentials = True

            self.step = 3
            self.is_running = True
            self.status_messages = ["Starting connector..."]

            theme = await self.get_state(ThemeState)
            show_browser = theme.show_browser

            credentials = {f["placeholder"]: f["value"] for f in self.credential_fields}
            profile_id = self.selected_profile_id

        # Reset bridge events
        _bridge.need_input.clear()
        _bridge.got_response.clear()

        # Build on_user_input callback — runs in Playwright's thread,
        # signals the bridge, blocks until user responds.
        def on_user_input(prompt_type: str, message: str) -> str:
            _bridge.prompt_type = prompt_type
            # For QR prompts, message contains the base64 data URL image
            if prompt_type == "qr":
                _bridge.prompt_image = message
                _bridge.prompt_message = ""
            else:
                _bridge.prompt_message = message
                _bridge.prompt_image = ""
            _bridge.need_input.set()
            # Block Playwright thread until submit_prompt fires
            _bridge.got_response.wait()
            _bridge.got_response.clear()
            return _bridge.response

        # Run connector in a thread so we can poll for prompt requests
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            None,
            lambda: WebConnectorService.run_connector(
                profile_id=profile_id,
                credentials=credentials,
                on_user_input=on_user_input,
                headless=not show_browser,
            ),
        )

        # Poll: detect prompt requests and push state to frontend
        while not future.done():
            if _bridge.need_input.is_set():
                async with self:
                    self.prompt_type = _bridge.prompt_type
                    self.prompt_message = _bridge.prompt_message
                    self.prompt_image = _bridge.prompt_image
                    self.prompt_visible = True
                _bridge.need_input.clear()
            await asyncio.sleep(0.2)

        result = await future

        async with self:
            # Clear credentials from memory immediately after use
            for f in self.credential_fields:
                f["value"] = ""

            self.is_running = False
            self.prompt_visible = False

            data = result.data or {}
            self.status_messages = data.get("status_log", [])

            # If matching is needed, go to matching step instead of result
            if data.get("needs_matching"):
                self.unmatched_positions = data.get("unmatched_positions", [])
                self.step = 4
                return

            self.result_message = result.message
            self.result_success = result.success
            self.result_errors = data.get("errors", [])
            self.result_imported = data.get("imported", 0)
            self.result_skipped = data.get("skipped", 0)
            self.result_status_log = data.get("status_log", [])

            self.step = 5

        if result.success:
            yield rx.toast.success(result.message, position="top-center")
        else:
            yield rx.toast.error(result.message, position="top-center")

    # ------------------------------------------------------------------
    # Matching step events (step 4)
    # ------------------------------------------------------------------

    @rx.event
    def set_match_ticker(self, index: int, value: str) -> None:
        """Update the ticker for an unmatched position."""
        self.unmatched_positions[index]["ticker"] = value

    @rx.event
    def set_match_currency(self, index: int, value: str) -> None:
        """Update the currency for an unmatched position."""
        self.unmatched_positions[index]["currency"] = value

    @rx.event
    def confirm_matching(self):
        """Import the matched positions and advance to result step."""
        result = WebConnectorService.import_matched_positions(self.unmatched_positions)

        data = result.data or {}
        self.result_message = result.message
        self.result_success = result.success
        self.result_errors = data.get("errors", [])
        self.result_imported = data.get("imported", 0)
        self.result_skipped = data.get("skipped", 0)
        self.result_status_log = self.status_messages

        self.step = 5

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
        self.selected_profile_needs_matching = False
        self.credential_fields = []
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
        self.prompt_visible = False
        self.prompt_message = ""
        self.prompt_type = ""
        self.prompt_input = ""
        self.prompt_image = ""
        self.unmatched_positions = []

    @rx.event
    def go_back(self) -> None:
        """Go back one step."""
        if self.step == 2:
            self.step = 1
            self.selected_profile_id = ""
            self.selected_profile_name = ""
            self.credential_fields = []
        elif self.step > 2:
            self.step -= 1
