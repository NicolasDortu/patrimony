"""The connectors hub page — lists available connectors."""

import reflex as rx

from ..components.card import link_card
from ..templates import template, t


@template(route="/connectors", title="Connectors")
def connectors() -> rx.Component:
    """The connectors hub page listing available data connectors."""
    return rx.vstack(
        rx.heading(t("page.connectors.title"), size="5"),
        rx.text(
            t("page.connectors.desc"),
            size="2",
            color=rx.color("gray", 10),
        ),
        rx.separator(),
        rx.vstack(
            link_card(
                title=t("page.connectors.csv_excel"),
                description=t("page.connectors.csv_excel_desc"),
                icon_name="file-spreadsheet",
                href="/connectors/file",
            ),
            link_card(
                title=t("page.connectors.broker_scraping"),
                description=t("page.connectors.broker_scraping_desc"),
                icon_name="globe",
                href="/connectors",
                enabled=False,
            ),
            spacing="3",
            width="100%",
            max_width="600px",
        ),
        spacing="5",
        width="100%",
        align="center",
    )
