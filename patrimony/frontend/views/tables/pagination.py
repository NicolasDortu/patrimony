"""Reusable pagination controls for table views."""

import reflex as rx

from ...templates import t


def pagination_view(state_cls) -> rx.Component:
    """Generic pagination controls that bind to any state with PaginationMixin.

    Args:
        state_cls: A Reflex state class that includes PaginationMixin
                   (must have page_number, total_pages, first_page, prev_page,
                   next_page, last_page).
    """
    is_first = state_cls.page_number == 1
    is_last = state_cls.page_number == state_cls.total_pages

    return rx.hstack(
        rx.text(
            t("label.page"),
            " ",
            rx.code(state_cls.page_number),
            " ",
            t("label.of"),
            " ",
            state_cls.total_pages,
            justify="end",
        ),
        rx.hstack(
            rx.icon_button(
                rx.icon("chevrons-left", size=18),
                on_click=state_cls.first_page,
                opacity=rx.cond(is_first, 0.6, 1),
                color_scheme=rx.cond(is_first, "gray", "accent"),
                variant="soft",
            ),
            rx.icon_button(
                rx.icon("chevron-left", size=18),
                on_click=state_cls.prev_page,
                opacity=rx.cond(is_first, 0.6, 1),
                color_scheme=rx.cond(is_first, "gray", "accent"),
                variant="soft",
            ),
            rx.icon_button(
                rx.icon("chevron-right", size=18),
                on_click=state_cls.next_page,
                opacity=rx.cond(is_last, 0.6, 1),
                color_scheme=rx.cond(is_last, "gray", "accent"),
                variant="soft",
            ),
            rx.icon_button(
                rx.icon("chevrons-right", size=18),
                on_click=state_cls.last_page,
                opacity=rx.cond(is_last, 0.6, 1),
                color_scheme=rx.cond(is_last, "gray", "accent"),
                variant="soft",
            ),
            align="center",
            spacing="2",
            justify="end",
        ),
        spacing="5",
        margin_top="1em",
        align="center",
        width="100%",
        justify="end",
    )
