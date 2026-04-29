import reflex as rx

from ...templates import t


def header_cell(text, icon: str) -> rx.Component:
    return rx.table.column_header_cell(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(text),
            align="center",
            spacing="2",
        ),
    )


def table_row(*cells: rx.Component, index: int) -> rx.Component:
    bg_color = rx.cond(
        index % 2 == 0,
        rx.color("gray", 1),
        rx.color("accent", 2),
    )
    hover_color = rx.cond(
        index % 2 == 0,
        rx.color("gray", 3),
        rx.color("accent", 3),
    )
    return rx.table.row(
        *cells,
        style={"_hover": {"bg": hover_color}, "bg": bg_color},
        align="center",
    )


def table_toolbar(
    state,
    sort_fields: list,
    *,
    add_button: rx.Component | None = None,
    extra_left: list[rx.Component] | None = None,
    default_sort_placeholder=None,
    search_placeholder=None,
) -> rx.Component:
    """Reusable toolbar for data tables.

    Renders a left section (add button, spreadsheet toggle, CSV export)
    and a right section (sort toggle, sort select, search input).
    """
    from .spreadsheet_view import spreadsheet_toggle_button

    if default_sort_placeholder is None:
        default_sort_placeholder = t("label.sort_by")
    if search_placeholder is None:
        search_placeholder = t("label.search")

    left_items: list[rx.Component] = []
    if add_button is not None:
        left_items.append(add_button)
    left_items.append(spreadsheet_toggle_button(state))
    left_items.append(
        rx.icon_button(
            rx.icon("arrow-down-to-line", size=20),
            variant="surface",
            size="3",
            on_click=state.export_csv,
        )
    )
    if extra_left:
        left_items.extend(extra_left)

    return rx.flex(
        rx.flex(
            *left_items,
            align="center",
            spacing="3",
        ),
        rx.flex(
            rx.cond(
                state.sort_reverse,
                rx.icon(
                    "arrow-down-z-a",
                    size=28,
                    stroke_width=1.5,
                    cursor="pointer",
                    flex_shrink="0",
                    on_click=state.toggle_sort,
                ),
                rx.icon(
                    "arrow-down-a-z",
                    size=28,
                    stroke_width=1.5,
                    cursor="pointer",
                    flex_shrink="0",
                    on_click=state.toggle_sort,
                ),
            ),
            rx.select.root(
                rx.select.trigger(
                    placeholder=default_sort_placeholder, variant="surface"
                ),
                rx.select.content(
                    *[
                        rx.select.item(label, value=value)
                        for label, value in sort_fields
                    ],
                ),
                size="3",
                on_change=state.set_sort_value,
            ),
            rx.input(
                rx.input.slot(rx.icon("search")),
                rx.input.slot(
                    rx.icon("x"),
                    justify="end",
                    cursor="pointer",
                    on_click=state.set_search_value(""),
                    display=rx.cond(state.search_value, "flex", "none"),
                ),
                value=state.search_value,
                placeholder=search_placeholder,
                size="3",
                max_width=["150px", "150px", "200px", "250px"],
                width="100%",
                variant="surface",
                color_scheme="gray",
                on_change=state.set_search_value,
            ),
            align="center",
            justify="end",
            spacing="3",
        ),
        spacing="3",
        justify="between",
        wrap="wrap",
        width="100%",
        padding_bottom="1em",
    )
