"""The settings page."""

import reflex as rx

from ..services import CredentialService
from ..templates import template, t
from ..templates.template import ThemeState
from ..views.pickers.color_picker import primary_color_picker, secondary_color_picker
from ..views.pickers.radius_picker import radius_picker
from ..views.pickers.scaling_picker import scaling_picker
from ..views.pickers.currency_picker import currency_picker
from ..views.pickers.asset_color_picker import asset_color_picker
from ..views.pickers.language_picker import language_picker


class SettingsState(rx.State):
    """State for settings page actions."""

    show_reset_confirm: bool = False

    @rx.var
    def has_master_password(self) -> bool:
        return CredentialService.has_master_password()

    @rx.event
    def toggle_reset_confirm(self):
        self.show_reset_confirm = not self.show_reset_confirm

    @rx.event
    def reset_master_password(self):
        result = CredentialService.reset_master_password()
        self.show_reset_confirm = False
        if result.success:
            yield rx.toast.success(
                "Master password and all saved credentials have been deleted.",
                position="top-center",
            )
        else:
            yield rx.toast.error(
                "Failed to reset master password.",
                position="top-center",
            )


@template(route="/settings", title="Settings")
def settings() -> rx.Component:
    """The settings page.

    Returns:
        The UI for the settings page.

    """
    return rx.vstack(
        rx.heading(t("page.settings.title"), size="5"),
        # Language picker
        language_picker(),
        # Default currency picker
        currency_picker(),
        # Primary color picker
        rx.vstack(
            rx.hstack(
                rx.icon("palette", color=rx.color("accent", 10)),
                rx.heading(t("settings.primary_color"), size="6"),
                align="center",
            ),
            primary_color_picker(),
            spacing="4",
            width="100%",
        ),
        # Secondary color picker
        rx.vstack(
            rx.hstack(
                rx.icon("blend", color=rx.color("accent", 10)),
                rx.heading(t("settings.secondary_color"), size="6"),
                align="center",
            ),
            secondary_color_picker(),
            spacing="4",
            width="100%",
        ),
        # Asset color picker
        asset_color_picker(),
        # Radius and scaling
        rx.grid(
            radius_picker(),
            scaling_picker(),
            columns=rx.breakpoints(initial="1", sm="2"),
            gap="1.5rem",
            width="100%",
        ),
        # Connectors section
        rx.vstack(
            rx.hstack(
                rx.icon("globe", color=rx.color("accent", 10)),
                rx.heading(t("settings.connectors"), size="6"),
                align="center",
            ),
            rx.card(
                rx.hstack(
                    rx.vstack(
                        rx.text(
                            t("settings.show_browser"),
                            weight="medium",
                            size="2",
                        ),
                        rx.text(
                            t("settings.show_browser_desc"),
                            size="2",
                            color=rx.color("gray", 10),
                        ),
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.switch(
                        checked=ThemeState.show_browser,
                        on_change=ThemeState.set_show_browser,
                    ),
                    align="center",
                    width="100%",
                ),
                width="100%",
            ),
            rx.cond(
                SettingsState.has_master_password,
                rx.card(
                    rx.hstack(
                        rx.vstack(
                            rx.text(
                                t("settings.reset_password"),
                                weight="medium",
                                size="2",
                            ),
                            rx.text(
                                t("settings.reset_password_desc"),
                                size="2",
                                color=rx.color("gray", 10),
                            ),
                            spacing="1",
                        ),
                        rx.spacer(),
                        rx.cond(
                            SettingsState.show_reset_confirm,
                            rx.hstack(
                                rx.button(
                                    t("btn.cancel"),
                                    variant="outline",
                                    size="2",
                                    on_click=SettingsState.toggle_reset_confirm,
                                ),
                                rx.button(
                                    t("btn.confirm"),
                                    color_scheme="red",
                                    size="2",
                                    on_click=SettingsState.reset_master_password,
                                ),
                                spacing="2",
                            ),
                            rx.button(
                                rx.icon("trash-2", size=14),
                                t("btn.reset"),
                                color_scheme="red",
                                variant="outline",
                                size="2",
                                on_click=SettingsState.toggle_reset_confirm,
                            ),
                        ),
                        align="center",
                        width="100%",
                    ),
                    width="100%",
                ),
            ),
            spacing="4",
            width="100%",
        ),
        spacing="7",
        width="100%",
    )
