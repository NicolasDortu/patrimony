"""Web connector wizard view components — profile selection, credentials, progress, and result."""

import reflex as rx

from ...states.web_connector_state import WebConnectorState
from ...templates import t


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
        rx.text(t("web_connector.select_profile"), weight="bold", size="3"),
        rx.text(
            t("web_connector.select_profile_desc"),
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
                    t("web_connector.no_profiles"),
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
                                t("web_connector.setup_master"), weight="bold", size="3"
                            ),
                            align="center",
                            spacing="2",
                        ),
                        rx.text(
                            t("web_connector.setup_master_desc"),
                            size="2",
                            color=rx.color("gray", 10),
                        ),
                        rx.input(
                            placeholder=t("web_connector.master_placeholder"),
                            type="password",
                            value=WebConnectorState.master_password_input,
                            on_change=WebConnectorState.set_master_password_input,
                            width="100%",
                            auto_complete=False,
                        ),
                        rx.button(
                            rx.icon("lock", size=16),
                            t("web_connector.set_master"),
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
                            rx.text(
                                t("web_connector.unlock_vault"), weight="bold", size="3"
                            ),
                            align="center",
                            spacing="2",
                        ),
                        rx.text(
                            t("web_connector.unlock_vault_desc"),
                            size="2",
                            color=rx.color("gray", 10),
                        ),
                        rx.input(
                            placeholder=t("connector.master_password"),
                            type="password",
                            value=WebConnectorState.master_password_input,
                            on_change=WebConnectorState.set_master_password_input,
                            width="100%",
                            auto_complete=False,
                        ),
                        rx.button(
                            rx.icon("lock-open", size=16),
                            t("btn.unlock"),
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


def _credential_field_input(field: dict, index: int) -> rx.Component:
    """Render a single credential input field dynamically."""
    return rx.vstack(
        rx.text(field["label"], weight="medium", size="2"),
        rx.cond(
            field["type"] == "select",
            rx.select(
                field["options"].to(list[str]),
                value=field["value"],
                on_change=WebConnectorState.set_credential_value(index),
                width="100%",
            ),
            rx.input(
                placeholder=field["label"],
                type=field["type"],
                value=field["value"],
                on_change=WebConnectorState.set_credential_value(index),
                width="100%",
                auto_complete=False,
            ),
        ),
        spacing="1",
        width="100%",
    )


def step_credentials() -> rx.Component:
    """Credentials input step."""
    return rx.vstack(
        rx.hstack(
            rx.icon("shield", size=20, color=rx.color("accent", 9)),
            rx.text(t("web_connector.enter_credentials"), weight="bold", size="3"),
            align="center",
            spacing="2",
        ),
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.text(t("web_connector.profile_label"), weight="bold", size="2"),
                    rx.text(WebConnectorState.selected_profile_name, size="2"),
                    spacing="2",
                ),
                rx.hstack(
                    rx.text(t("web_connector.mode_label"), weight="bold", size="2"),
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
                        t("web_connector.credentials_loaded"),
                        size="2",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon("trash-2", size=14),
                        t("btn.delete"),
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
                    t("web_connector.browser_notice"),
                    size="2",
                ),
                icon="info",
                color_scheme="blue",
                width="100%",
            ),
        ),
        rx.separator(),
        # Dynamic credential fields from the connector profile
        rx.foreach(
            WebConnectorState.credential_fields,
            _credential_field_input,
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
                rx.text(t("web_connector.save_credentials"), size="2"),
                align="center",
                spacing="2",
            ),
        ),
        rx.separator(),
        rx.hstack(
            rx.button(
                rx.icon("arrow-left", size=16),
                t("btn.back"),
                variant="outline",
                on_click=WebConnectorState.go_back,
                size="3",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("play", size=16),
                t("web_connector.start_import"),
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
# Step 3: Running (with OTP dialog overlay)
# ============================================================================


def _otp_dialog_overlay() -> rx.Component:
    """Overlay shown during browser automation when user input is needed (OTP, QR, etc.)."""
    return rx.cond(
        WebConnectorState.prompt_visible,
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.icon("smartphone", size=20, color=rx.color("accent", 9)),
                    rx.text(t("web_connector.otp_title"), weight="bold", size="3"),
                    align="center",
                    spacing="2",
                ),
                # QR code image (shown when prompt_type is "qr")
                rx.cond(
                    WebConnectorState.prompt_image != "",
                    rx.vstack(
                        rx.text(
                            t("web_connector.scan_qr"),
                            size="2",
                            color=rx.color("gray", 10),
                        ),
                        rx.image(
                            src=WebConnectorState.prompt_image,
                            width="220px",
                            height="220px",
                            border_radius="var(--radius-2)",
                        ),
                        align="center",
                        spacing="2",
                    ),
                ),
                # Text message (shown when there is no QR image)
                rx.cond(
                    (WebConnectorState.prompt_image == "")
                    & (WebConnectorState.prompt_message != ""),
                    rx.text(
                        WebConnectorState.prompt_message,
                        size="2",
                        color=rx.color("gray", 10),
                    ),
                ),
                rx.cond(
                    WebConnectorState.prompt_type == "text",
                    rx.input(
                        placeholder=t("web_connector.otp_placeholder"),
                        value=WebConnectorState.prompt_input,
                        on_change=WebConnectorState.set_prompt_input,
                        width="100%",
                        auto_complete=False,
                        auto_focus=True,
                    ),
                ),
                rx.button(
                    rx.icon("check", size=16),
                    t("btn.confirm"),
                    on_click=WebConnectorState.submit_prompt,
                    width="100%",
                    size="3",
                ),
                spacing="3",
                width="100%",
            ),
            width="100%",
        ),
    )


def step_running() -> rx.Component:
    """Running step — shows progress while browser automation executes."""
    return rx.vstack(
        rx.vstack(
            rx.spinner(size="3"),
            rx.text(t("web_connector.running"), weight="bold", size="3"),
            rx.text(
                t("web_connector.running_desc"),
                size="2",
                color=rx.color("gray", 10),
                text_align="center",
            ),
            align="center",
            spacing="3",
        ),
        # OTP / interactive prompt overlay
        _otp_dialog_overlay(),
        rx.separator(),
        rx.text(t("web_connector.status_log"), weight="bold", size="2"),
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
# Step 4: Matching (name → ticker)
# ============================================================================


def _matching_row(item: dict, index: int) -> rx.Component:
    """A row in the matching table: position name + ticker input + currency select."""
    return rx.hstack(
        rx.vstack(
            rx.text(item["name"], weight="medium", size="2"),
            rx.text(
                f"Qty: {item['quantity']}  |  Val: {item['value']}",
                size="1",
                color=rx.color("gray", 10),
            ),
            spacing="1",
            flex="1",
        ),
        rx.input(
            placeholder=t("web_connector.ticker_placeholder"),
            value=item["ticker"],
            on_change=WebConnectorState.set_match_ticker(index),
            width="150px",
            size="2",
        ),
        rx.input(
            placeholder=t("web_connector.currency_placeholder"),
            value=item["currency"],
            on_change=WebConnectorState.set_match_currency(index),
            width="100px",
            size="2",
        ),
        align="center",
        spacing="3",
        width="100%",
        padding_y="2",
    )


def step_matching() -> rx.Component:
    """Matching step — user maps position names to tickers and currencies."""
    return rx.vstack(
        rx.hstack(
            rx.icon("link", size=20, color=rx.color("accent", 9)),
            rx.text(t("web_connector.matching_title"), weight="bold", size="3"),
            align="center",
            spacing="2",
        ),
        rx.text(
            t("web_connector.matching_desc"),
            size="2",
            color=rx.color("gray", 10),
        ),
        rx.separator(),
        # Header
        rx.hstack(
            rx.text(t("web_connector.col_position"), weight="bold", size="2", flex="1"),
            rx.text(t("label.ticker"), weight="bold", size="2", width="150px"),
            rx.text(t("label.currency"), weight="bold", size="2", width="100px"),
            spacing="3",
            width="100%",
            padding_x="2",
        ),
        rx.box(
            rx.foreach(
                WebConnectorState.unmatched_positions,
                _matching_row,
            ),
            max_height="400px",
            overflow_y="auto",
            width="100%",
        ),
        rx.separator(),
        rx.hstack(
            rx.button(
                rx.icon("arrow-left", size=16),
                t("btn.back"),
                variant="outline",
                on_click=WebConnectorState.reset_wizard,
                size="3",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("check", size=16),
                t("web_connector.confirm_import"),
                on_click=WebConnectorState.confirm_matching,
                size="3",
            ),
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


# ============================================================================
# Step 5: Result
# ============================================================================


def step_result() -> rx.Component:
    """Import result step."""
    return rx.vstack(
        rx.cond(
            WebConnectorState.result_success,
            rx.vstack(
                rx.icon("circle-check", size=48, color=rx.color("green", 9)),
                rx.text(t("web_connector.import_successful"), weight="bold", size="4"),
                rx.text(WebConnectorState.result_message, size="2"),
                rx.hstack(
                    rx.badge(
                        rx.text(
                            f"{WebConnectorState.result_imported} "
                            + t("connector.imported")
                        ),
                        color_scheme="green",
                    ),
                    rx.cond(
                        WebConnectorState.result_skipped > 0,
                        rx.badge(
                            rx.text(
                                f"{WebConnectorState.result_skipped} "
                                + t("connector.skipped")
                            ),
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
                rx.text(t("web_connector.import_failed"), weight="bold", size="4"),
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
                rx.text(t("web_connector.status_log"), weight="bold", size="3"),
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
                rx.text(t("web_connector.errors"), weight="bold", size="3"),
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
            t("web_connector.run_another"),
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
        _dot("1", t("web_connector.step_profile")),
        rx.box(width="30px", height="2px", background=rx.color("gray", 6)),
        _dot("2", t("web_connector.step_credentials")),
        rx.box(width="30px", height="2px", background=rx.color("gray", 6)),
        _dot("3", t("web_connector.step_running")),
        rx.box(width="30px", height="2px", background=rx.color("gray", 6)),
        rx.cond(
            WebConnectorState.selected_profile_needs_matching,
            rx.fragment(
                _dot("4", t("web_connector.step_matching")),
                rx.box(width="30px", height="2px", background=rx.color("gray", 6)),
                _dot("5", t("web_connector.step_result")),
            ),
            _dot("4", t("web_connector.step_result")),
        ),
        justify="center",
        align="center",
        spacing="3",
        width="100%",
        padding_y="1em",
    )
