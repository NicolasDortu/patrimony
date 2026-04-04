"""Charts for the properties page."""

import reflex as rx

from ...components.card import card
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
                    rx.recharts.pie_chart(
                        rx.recharts.pie(
                            data=PropertiesState.category_allocation_data,
                            data_key="value",
                            name_key="name",
                            cx="50%",
                            cy="50%",
                            label=True,
                            inner_radius="80",
                            outer_radius="110",
                            stroke="none",
                            fill_opacity=0.8,
                        ),
                        rx.recharts.legend(),
                        rx.recharts.graphing_tooltip(),
                        width="100%",
                        height=300,
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),
        ),
        spacing="5",
        width="100%",
    )
