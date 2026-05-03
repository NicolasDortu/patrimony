"""The connectors hub page — lists available connectors and import history."""

import reflex as rx

from ..components.card import link_card
from ..states.connector_history_state import ConnectorHistoryState
from ..templates import template, t


def _status_badge(status: str) -> rx.Component:
    """Color-coded status badge."""
    return rx.cond(
        status == "success",
        rx.badge(t("connector.status_success"), color_scheme="green", size="1"),
        rx.cond(
            status == "partial",
            rx.badge(t("connector.status_partial"), color_scheme="orange", size="1"),
            rx.badge(t("connector.status_failed"), color_scheme="red", size="1"),
        ),
    )


def _type_icon(connector_type: str) -> rx.Component:
    """Icon based on connector type."""
    return rx.cond(
        connector_type == "web",
        rx.icon("globe", size=16, color=rx.color("accent", 9)),
        rx.icon("file-spreadsheet", size=16, color=rx.color("accent", 9)),
    )


def _history_row(entry: dict) -> rx.Component:
    """A single history row."""
    return rx.card(
        rx.hstack(
            _type_icon(entry["connector_type"]),
            rx.vstack(
                rx.text(entry["source_name"], weight="bold", size="2"),
                rx.hstack(
                    rx.badge(entry["import_mode"], size="1"),
                    _status_badge(entry["status"]),
                    rx.text(
                        entry["created_at"],
                        size="1",
                        color=rx.color("gray", 9),
                    ),
                    spacing="2",
                    align="center",
                ),
                spacing="1",
            ),
            rx.spacer(),
            rx.hstack(
                rx.badge(
                    rx.text(
                        entry["imported"].to(str) + " " + t("connector.imported"),
                    ),
                    color_scheme="green",
                    size="1",
                ),
                rx.badge(
                    rx.text(entry["skipped"].to(str) + " " + t("connector.skipped")),
                    color_scheme="orange",
                    size="1",
                ),
                rx.cond(
                    entry["connector_type"] == "file",
                    rx.button(
                        rx.icon("settings", size=14),
                        variant="ghost",
                        size="1",
                        on_click=ConnectorHistoryState.open_detail(entry["id"]),
                    ),
                    rx.fragment(),
                ),
                rx.button(
                    rx.icon("refresh-cw", size=14),
                    variant="ghost",
                    size="1",
                    on_click=ConnectorHistoryState.refresh_entry(entry["id"]),
                    loading=ConnectorHistoryState.is_refreshing_id == entry["id"],
                ),
                rx.button(
                    rx.icon("trash-2", size=14),
                    variant="ghost",
                    color_scheme="red",
                    size="1",
                    on_click=ConnectorHistoryState.delete_entry(entry["id"]),
                ),
                spacing="2",
                align="center",
            ),
            align="center",
            spacing="3",
            width="100%",
        ),
        width="100%",
        size="1",
    )


def _detail_dialog() -> rx.Component:
    """Dialog to view/edit the source file path for a file connector entry."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(t("connector.connector_details")),
            rx.dialog.description(
                ConnectorHistoryState.detail_source_name,
                size="2",
                color=rx.color("gray", 9),
            ),
            rx.vstack(
                rx.text(t("connector.source_path"), size="2", weight="bold"),
                rx.input(
                    value=ConnectorHistoryState.detail_path_input,
                    on_change=ConnectorHistoryState.set_detail_path_input,
                    placeholder="/path/to/file.csv",
                    width="100%",
                ),
                spacing="2",
                width="100%",
                padding_top="12px",
            ),
            rx.hstack(
                rx.spacer(),
                rx.dialog.close(
                    rx.button(
                        t("btn.cancel"),
                        variant="outline",
                        on_click=ConnectorHistoryState.cancel_detail,
                    ),
                ),
                rx.button(
                    t("btn.save_short"),
                    on_click=ConnectorHistoryState.save_detail_path,
                ),
                spacing="3",
                padding_top="16px",
                width="100%",
            ),
        ),
        open=ConnectorHistoryState.show_detail_dialog,
    )


def _unlock_dialog() -> rx.Component:
    """Dialog to unlock the credential vault before refreshing a web connector."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(t("connector.unlock_credentials")),
            rx.dialog.description(
                t("connector.unlock_credentials_desc"),
                size="2",
            ),
            rx.vstack(
                rx.input(
                    value=ConnectorHistoryState.master_password_input,
                    on_change=ConnectorHistoryState.set_master_password_input,
                    type="password",
                    placeholder=t("connector.master_password"),
                    width="100%",
                ),
                spacing="2",
                width="100%",
                padding_top="12px",
            ),
            rx.hstack(
                rx.spacer(),
                rx.dialog.close(
                    rx.button(
                        t("btn.cancel"),
                        variant="outline",
                        on_click=ConnectorHistoryState.cancel_unlock,
                    ),
                ),
                rx.button(
                    t("connector.unlock_refresh"),
                    on_click=ConnectorHistoryState.submit_unlock_and_refresh,
                ),
                spacing="3",
                padding_top="16px",
                width="100%",
            ),
        ),
        open=ConnectorHistoryState.show_unlock_dialog,
    )


def _history_section() -> rx.Component:
    """History section showing past imports."""
    return rx.vstack(
        rx.hstack(
            rx.icon("history", size=20, color=rx.color("accent", 9)),
            rx.heading(t("connector.active_connectors"), size="4"),
            rx.spacer(),
            rx.button(
                rx.icon("refresh-cw", size=14),
                t("btn.refresh"),
                variant="outline",
                size="1",
                on_click=ConnectorHistoryState.load_history,
            ),
            align="center",
            width="100%",
        ),
        rx.cond(
            ConnectorHistoryState.has_history,
            rx.vstack(
                rx.foreach(ConnectorHistoryState.history_entries, _history_row),
                spacing="2",
                width="100%",
            ),
            rx.callout(
                rx.text(
                    t("connector.no_active"),
                    size="2",
                ),
                icon="info",
                color_scheme="blue",
                width="100%",
            ),
        ),
        spacing="3",
        width="100%",
    )


@template(
    route="/connectors",
    title="Connectors",
    on_load=ConnectorHistoryState.load_history,
)
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
        rx.hstack(
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
                href="/connectors/web",
                enabled=True,
            ),
            spacing="3",
            width="100%",
            max_width="800px",
        ),
        rx.separator(),
        _history_section(),
        _detail_dialog(),
        _unlock_dialog(),
        spacing="5",
        width="100%",
        align="center",
    )
