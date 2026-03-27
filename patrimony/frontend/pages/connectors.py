"""The connectors hub page — lists available connectors."""

import reflex as rx

from ..templates import template, t


def _connector_card(
    title: str,
    description: str,
    icon_name: str,
    href: str,
    enabled: bool = True,
) -> rx.Component:
    """A card representing a single connector."""
    return rx.card(
        rx.link(
            rx.hstack(
                rx.box(
                    rx.icon(icon_name, size=28, color=rx.color("accent", 9)),
                    padding="12px",
                    border_radius="var(--radius-3)",
                    background=rx.color("accent", 3),
                ),
                rx.vstack(
                    rx.text(title, weight="bold", size="3"),
                    rx.text(
                        description,
                        size="2",
                        color=rx.color("gray", 10),
                    ),
                    spacing="1",
                ),
                rx.spacer(),
                rx.icon(
                    "chevron-right",
                    size=20,
                    color=rx.color("gray", 9),
                ),
                align="center",
                spacing="4",
                width="100%",
                padding="4px",
            ),
            href=href,
            underline="none",
            width="100%",
            _hover={"opacity": "0.85"} if enabled else {},
        ),
        width="100%",
        opacity="1" if enabled else "0.5",
        cursor="pointer" if enabled else "not-allowed",
    )


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
            _connector_card(
                title=t("page.connectors.csv_excel"),
                description=t("page.connectors.csv_excel_desc"),
                icon_name="file-spreadsheet",
                href="/connectors/file",
            ),
            _connector_card(
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
