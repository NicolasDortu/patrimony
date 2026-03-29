"""The file connector page — CSV/Excel import wizard."""

import reflex as rx

from ..states.connector_state import ConnectorState
from ..templates import template
from ..views.connectors.file_import_wizard import (
    step_indicator,
    step_mapping,
    step_result,
    step_review,
    step_upload,
)


@template(route="/connectors/file", title="File Import")
def file_connector() -> rx.Component:
    """The file connector page with a CSV/Excel import wizard."""
    return rx.vstack(
        rx.hstack(
            rx.link(
                rx.icon("arrow-left", size=20),
                href="/connectors",
            ),
            rx.heading("File Import", size="5"),
            align="center",
            spacing="3",
        ),
        rx.text(
            "Import positions or cash operations from CSV or Excel files.",
            size="2",
            color=rx.color("gray", 10),
        ),
        step_indicator(),
        rx.card(
            rx.cond(
                ConnectorState.step == 1,
                step_upload(),
                rx.cond(
                    ConnectorState.step == 2,
                    step_mapping(),
                    rx.cond(
                        ConnectorState.step == 3,
                        step_review(),
                        step_result(),
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
