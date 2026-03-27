"""Balance operations page for a specific cash account."""

import reflex as rx

from ..dialogs.cash_operation_dialog import open_add_operation_dialog
from ..states.cash_operations_state import CashOperationsState
from ..templates import template, t
from ..views.tables.cash_operations_table import cash_operations_table


@template(
    route="/cash_operations",
    title="Cash Operations",
    on_load=[CashOperationsState.on_page_load],
)
def cash_operations() -> rx.Component:
    """The cash operations page.

    Returns:
        The UI for the cash operations page.
    """
    return rx.vstack(
        rx.heading(
            t("cash_ops.title_prefix") + " " + CashOperationsState.account_number,
            size="5",
        ),
        rx.flex(
            open_add_operation_dialog(CashOperationsState.add_operation),
            rx.button(
                rx.icon("arrow-down-to-line", size=20),
                t("btn.export"),
                size="3",
                variant="surface",
                display=["none", "none", "none", "flex"],
                on_click=CashOperationsState.export_csv,
            ),
            rx.button(
                rx.icon("arrow-left", size=20),
                t("cash_ops.back"),
                size="3",
                variant="soft",
                on_click=rx.redirect("/cash"),
            ),
            justify="between",
            width="100%",
        ),
        cash_operations_table(),
        spacing="5",
        width="100%",
    )
