"""Charts for the properties page."""

import reflex as rx

from ...components.card import card
from ...components.donut_chart import donut_pie_chart
from ...states.properties_state import PropertiesState
from ...templates import t


def properties_charts() -> rx.Component:
    """Pie chart showing property value distribution by category."""
    return rx.vstack(
        rx.cond(
            PropertiesState.category_allocation_data.length() > 0,
            card(
                rx.vstack(
                    rx.text(
                        t("chart.properties_by_category"), size="3", weight="medium"
                    ),
                    donut_pie_chart(PropertiesState.category_allocation_data),
                    spacing="3",
                    width="100%",
                ),
            ),
        ),
        spacing="5",
        width="100%",
    )
