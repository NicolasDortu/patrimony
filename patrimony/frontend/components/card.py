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
    return_pct: float,
    icon: str,
    currency_symbol: str = "$",
) -> rx.Component:
    """Card with value, return percentage and icon"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(
                    rx.icon(tag=icon, size=34),
                    radius="full",
                    padding="0.7rem",
                ),
                rx.vstack(
                    rx.heading(
                        currency_symbol + f"{value:,.2f}",
                        size="6",
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
            rx.hstack(
                rx.hstack(
                    rx.cond(
                        return_pct >= 0,
                        rx.icon(
                            tag="trending-up",
                            size=24,
                            color=rx.color("grass", 9),
                        ),
                        rx.icon(
                            tag="trending-down",
                            size=24,
                            color=rx.color("tomato", 9),
                        ),
                    ),
                    rx.cond(
                        return_pct >= 0,
                        rx.text(
                            f"{return_pct:.2f}%",
                            size="3",
                            color=rx.color("grass", 9),
                            weight="medium",
                        ),
                        rx.text(
                            f"{return_pct:.2f}%",
                            size="3",
                            color=rx.color("tomato", 9),
                            weight="medium",
                        ),
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.text(
                    "total return",
                    size="2",
                    color=rx.color("gray", 10),
                ),
                align="center",
                width="100%",
            ),
            spacing="3",
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
