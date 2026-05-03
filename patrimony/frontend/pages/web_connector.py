"""The web connector page — browser-based automated import wizard."""

import reflex as rx

from ..states.web_connector_state import WebConnectorState
from ..templates import template
from ..views.connectors.web_connector_wizard import (
    step_credentials,
    step_indicator,
    step_matching,
    step_result,
    step_running,
    step_select_profile,
)


@template(
    route="/connectors/web",
    title="Web Connector",
    on_load=WebConnectorState.load_profiles,
)
def web_connector() -> rx.Component:
    """The web connector page with a browser automation wizard."""
    return rx.vstack(
        rx.hstack(
            rx.link(
                rx.icon("arrow-left", size=20),
                href="/connectors",
            ),
            rx.heading("Web Connector", size="5"),
            align="center",
            spacing="3",
        ),
        rx.text(
            "Automatically import data from your broker or bank website.",
            size="2",
            color=rx.color("gray", 10),
        ),
        step_indicator(),
        rx.card(
            rx.cond(
                WebConnectorState.step == 1,
                step_select_profile(),
                rx.cond(
                    WebConnectorState.step == 2,
                    step_credentials(),
                    rx.cond(
                        WebConnectorState.step == 3,
                        step_running(),
                        rx.cond(
                            WebConnectorState.step == 4,
                            step_matching(),
                            step_result(),
                        ),
                    ),
                ),
            ),
            width="100%",
            max_width="800px",
        ),
        spacing="5",
        width="100%",
        align="center",
    )
