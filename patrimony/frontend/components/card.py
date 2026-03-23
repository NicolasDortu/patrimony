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
