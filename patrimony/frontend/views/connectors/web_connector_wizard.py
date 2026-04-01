"""Web connector wizard view components — profile selection, credentials, progress, and result."""

import reflex as rx

from ...states.web_connector_state import WebConnectorState


# ============================================================================
# Step 1: Select Profile
# ============================================================================


def _profile_card(profile: dict) -> rx.Component:
    """A clickable card for a single connector profile."""
    return rx.card(
        rx.hstack(
            rx.icon("globe", size=24, color=rx.color("accent", 9)),
            rx.vstack(
                rx.text(profile["name"], weight="bold", size="3"),
                rx.text(
                    profile["description"],
                    size="2",
                    color=rx.color("gray", 10),
                ),
                rx.badge(profile["import_mode"], size="1"),
                spacing="1",
            ),
            align="start",
            spacing="3",
            width="100%",
        ),
        cursor="pointer",
        _hover={
            "border_color": rx.color("accent", 9),
            "box_shadow": "0 2px 8px rgba(0,0,0,0.08)",
        },
        on_click=WebConnectorState.select_profile(profile["id"]),
        width="100%",
    )


def step_select_profile() -> rx.Component:
    """Profile selection step."""
    return rx.vstack(
        rx.text("Select a connector profile:", weight="bold", size="3"),
        rx.text(
            "Choose the broker or bank you want to import data from.",
            size="2",
            color=rx.color("gray", 10),
        ),
        rx.separator(),
        rx.cond(
            WebConnectorState.has_profiles,
            rx.vstack(
                rx.foreach(WebConnectorState.profiles, _profile_card),
                spacing="3",
                width="100%",
            ),
            rx.callout(
                rx.text(
                    "No connector profiles available. "
                    "Add profile JSON files to the connector_profiles directory.",
                    size="2",
                ),
                icon="info",
                color_scheme="blue",
                width="100%",
            ),
        ),
        spacing="4",
        width="100%",
    )


# ============================================================================
# Step 2: Credentials
# ============================================================================


def _master_password_overlay() -> rx.Component:
    """Overlay shown when master password needs setup or unlock."""
    return rx.cond(
        WebConnectorState.show_credential_lock,
        rx.card(
            rx.vstack(
                rx.cond(
                    WebConnectorState.needs_master_setup,
                    # --- Setup new master password ---
                    rx.vstack(
                        rx.hstack(
                            rx.icon("key-round", size=20, color=rx.color("accent", 9)),
                            rx.text(
                                "Set up a master password", weight="bold", size="3"
                            ),
                            align="center",
                            spacing="2",
                        ),
                        rx.text(
                            "Create a master password to securely store your broker "
                            "credentials. You can skip this if you prefer to enter "
                            "credentials each time.",
                            size="2",
                            color=rx.color("gray", 10),
                        ),
                        rx.input(
                            placeholder="Choose a master password (min 4 chars)",
                            type="password",
                            value=WebConnectorState.master_password_input,
                            on_change=WebConnectorState.set_master_password_input,
                            width="100%",
                            auto_complete=False,
                        ),
                        rx.button(
                            rx.icon("lock", size=16),
                            "Set Master Password",
                            on_click=WebConnectorState.setup_master_password,
                            width="100%",
                            size="3",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    # --- Unlock existing master password ---
                    rx.vstack(
                        rx.hstack(
                            rx.icon("lock", size=20, color=rx.color("accent", 9)),
                            rx.text("Unlock credential vault", weight="bold", size="3"),
                            align="center",
                            spacing="2",
                        ),
                        rx.text(
                            "Enter your master password to access saved credentials.",
                            size="2",
                            color=rx.color("gray", 10),
                        ),
                        rx.input(
                            placeholder="Master password",
                            type="password",
                            value=WebConnectorState.master_password_input,
                            on_change=WebConnectorState.set_master_password_input,
                            width="100%",
                            auto_complete=False,
                        ),
                        rx.button(
                            rx.icon("lock-open", size=16),
                            "Unlock",
                            on_click=WebConnectorState.unlock_master_password,
                            width="100%",
                            size="3",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                ),
                spacing="3",
                width="100%",
            ),
            width="100%",
        ),
    )


def step_credentials() -> rx.Component:
    """Credentials input step."""
    return rx.vstack(
        rx.hstack(
            rx.icon("shield", size=20, color=rx.color("accent", 9)),
            rx.text("Enter your credentials", weight="bold", size="3"),
            align="center",
            spacing="2",
        ),
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.text("Profile:", weight="bold", size="2"),
                    rx.text(WebConnectorState.selected_profile_name, size="2"),
                    spacing="2",
                ),
                rx.hstack(
                    rx.text("Mode:", weight="bold", size="2"),
                    rx.badge(WebConnectorState.selected_profile_import_mode),
                    spacing="2",
                ),
                spacing="2",
            ),
            width="100%",
        ),
        # Master password overlay (setup or unlock)
        _master_password_overlay(),
        # Saved credentials notice
        rx.cond(
            WebConnectorState.has_saved_credentials,
            rx.callout(
                rx.hstack(
                    rx.text(
                        "Credentials loaded from vault.",
                        size="2",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon("trash-2", size=14),
                        "Delete",
                        variant="ghost",
                        color_scheme="red",
                        size="1",
                        on_click=WebConnectorState.delete_saved_credentials,
                    ),
                    align="center",
                    width="100%",
                ),
                icon="shield-check",
                color_scheme="green",
                width="100%",
            ),
            rx.callout(
                rx.text(
                    "A browser window will open so you can monitor the process "
                    "and complete any 2FA verification if needed.",
                    size="2",
                ),
                icon="info",
                color_scheme="blue",
                width="100%",
            ),
        ),
        rx.separator(),
        rx.vstack(
            rx.text("Username", weight="medium", size="2"),
            rx.input(
                placeholder="Enter your username",
                value=WebConnectorState.username,
                on_change=WebConnectorState.set_username,
                width="100%",
                auto_complete=False,
            ),
            spacing="1",
            width="100%",
        ),
        rx.vstack(
            rx.text("Password", weight="medium", size="2"),
            rx.input(
                placeholder="Enter your password",
                type="password",
                value=WebConnectorState.password,
                on_change=WebConnectorState.set_password,
                width="100%",
                auto_complete=False,
            ),
            spacing="1",
            width="100%",
        ),
        # Save credentials checkbox (only visible when vault is unlocked)
        rx.cond(
            ~WebConnectorState.show_credential_lock
            & ~WebConnectorState.has_saved_credentials,
            rx.hstack(
                rx.checkbox(
                    checked=WebConnectorState.save_credentials_checked,
                    on_change=WebConnectorState.toggle_save_credentials,
                ),
                rx.text("Save credentials to vault", size="2"),
                align="center",
                spacing="2",
            ),
        ),
        rx.separator(),
        rx.hstack(
            rx.button(
                rx.icon("arrow-left", size=16),
                "Back",
                variant="outline",
                on_click=WebConnectorState.go_back,
                size="3",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("play", size=16),
                "Start Import",
                on_click=WebConnectorState.start_connector,
                disabled=~WebConnectorState.credentials_valid,
                size="3",
            ),
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


# ============================================================================
# Step 3: Running
# ============================================================================


def step_running() -> rx.Component:
    """Running step — shows progress while browser automation executes."""
    return rx.vstack(
        rx.vstack(
            rx.spinner(size="3"),
            rx.text("Browser automation in progress...", weight="bold", size="3"),
            rx.text(
                "A browser window should be open. "
                "Please complete any 2FA verification if prompted.",
                size="2",
                color=rx.color("gray", 10),
                text_align="center",
            ),
            align="center",
            spacing="3",
        ),
        rx.separator(),
        rx.text("Status Log:", weight="bold", size="2"),
        rx.box(
            rx.foreach(
                WebConnectorState.status_messages,
                lambda msg: rx.hstack(
                    rx.icon("chevron-right", size=12, color=rx.color("gray", 9)),
                    rx.text(msg, size="1", color=rx.color("gray", 11)),
                    spacing="1",
                ),
            ),
            max_height="200px",
            overflow_y="auto",
            width="100%",
            padding="3",
            border=f"1px solid {rx.color('gray', 6)}",
            border_radius="var(--radius-2)",
            min_height="60px",
        ),
        spacing="4",
        width="100%",
        align="center",
    )


# ============================================================================
# Step 4: Result
# ============================================================================


def step_result() -> rx.Component:
    """Import result step."""
    return rx.vstack(
        rx.cond(
            WebConnectorState.result_success,
            rx.vstack(
                rx.icon("circle-check", size=48, color=rx.color("green", 9)),
                rx.text("Import Successful!", weight="bold", size="4"),
                rx.text(WebConnectorState.result_message, size="2"),
                rx.hstack(
                    rx.badge(
                        rx.text(f"{WebConnectorState.result_imported} imported"),
                        color_scheme="green",
                    ),
                    rx.cond(
                        WebConnectorState.result_skipped > 0,
                        rx.badge(
                            rx.text(f"{WebConnectorState.result_skipped} skipped"),
                            color_scheme="orange",
                        ),
                    ),
                    spacing="2",
                ),
                align="center",
                spacing="3",
            ),
            rx.vstack(
                rx.icon("circle-x", size=48, color=rx.color("red", 9)),
                rx.text("Import Failed", weight="bold", size="4"),
                rx.text(WebConnectorState.result_message, size="2"),
                align="center",
                spacing="3",
            ),
        ),
        # Status log
        rx.cond(
            WebConnectorState.result_status_log.length() > 0,
            rx.vstack(
                rx.separator(),
                rx.text("Status Log:", weight="bold", size="3"),
                rx.box(
                    rx.foreach(
                        WebConnectorState.result_status_log,
                        lambda msg: rx.hstack(
                            rx.icon(
                                "chevron-right", size=12, color=rx.color("gray", 9)
                            ),
                            rx.text(msg, size="1"),
                            spacing="1",
                        ),
                    ),
                    max_height="150px",
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
        # Error details
        rx.cond(
            WebConnectorState.result_errors.length() > 0,
            rx.vstack(
                rx.separator(),
                rx.text("Errors:", weight="bold", size="3"),
                rx.box(
                    rx.foreach(
                        WebConnectorState.result_errors,
                        lambda err: rx.text(err, size="1", color=rx.color("red", 11)),
                    ),
                    max_height="150px",
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
            "Run Another Import",
            on_click=WebConnectorState.reset_wizard,
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
                WebConnectorState.step >= int(num),
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
        _dot("1", "Profile"),
        rx.box(width="40px", height="2px", background=rx.color("gray", 6)),
        _dot("2", "Credentials"),
        rx.box(width="40px", height="2px", background=rx.color("gray", 6)),
        _dot("3", "Running"),
        rx.box(width="40px", height="2px", background=rx.color("gray", 6)),
        _dot("4", "Result"),
        justify="center",
        align="center",
        spacing="3",
        width="100%",
        padding_y="1em",
    )
