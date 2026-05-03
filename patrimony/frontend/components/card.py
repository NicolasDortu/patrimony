import reflex as rx

from ..styles import styles


def card(*children, **props) -> rx.Component:
    """Basic card component"""
    return rx.card(
        *children,
        box_shadow=styles.box_shadow_style,
        size="3",
        width="100%",
        **props,
    )


def stats_card(
    stat_name: str,
    value: float,
    icon: str,
    currency_symbol: str = "$",
) -> rx.Component:
    """Card with value and icon."""
    return rx.card(
        rx.hstack(
            rx.badge(
                rx.icon(tag=icon, size=34),
                radius="full",
                padding="0.7rem",
            ),
            rx.vstack(
                rx.heading(
                    currency_symbol + f"{value:,.2f}",
                    size="7",
                    weight="bold",
                ),
                rx.text(stat_name, size="4", weight="medium"),
                spacing="1",
                height="100%",
                align_items="start",
                width="100%",
            ),
            height="100%",
            spacing="4",
            align="center",
            width="100%",
        ),
        size="3",
        width="100%",
        box_shadow=styles.box_shadow_style,
    )


def link_card(
    title: str,
    description: str,
    icon_name: str,
    href: str,
    enabled: bool = True,
) -> rx.Component:
    """A card linking to a destination with icon, title, and description."""
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
