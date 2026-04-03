"""The properties page."""

import reflex as rx

from ..components.empty_table import empty_table
from ..components.loading import loading_spinner
from ..dialogs import open_add_property_dialog
from ..templates import template, t
from ..views.tables.properties_table import properties_table
from ..states.properties_state import PropertiesState
from ..views.tables.spreadsheet_view import spreadsheet_or_table


@template(route="/properties", title="Properties", on_load=PropertiesState.on_page_load)
def properties() -> rx.Component:
    """The properties page."""
    return rx.vstack(
        rx.hstack(
            rx.heading(t("page.properties.title"), size="5"),
            rx.spacer(),
            align="center",
            width="100%",
        ),
        rx.cond(
            PropertiesState.is_loading,
            loading_spinner(),
            rx.cond(
                PropertiesState.total_items > 0,
                spreadsheet_or_table(PropertiesState, properties_table()),
                empty_table(
                    "empty.properties",
                    "house",
                    open_add_property_dialog(PropertiesState.add_property),
                ),
            ),
        ),
        spacing="5",
        width="100%",
    )
