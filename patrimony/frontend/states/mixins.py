"""Reusable state mixins for frontend components."""

import math

import reflex as rx


def apply_sort_and_search(
    items: list,
    sort_value: str,
    sort_reverse: bool,
    search_value: str,
    numeric_sort_fields: list[str],
    search_fields: list[str],
    accessor: str = "dict",
) -> list:
    """Generic sort + search for table state items.

    Args:
        accessor: "dict" for dict items (item.get), "attr" for dataclass/object items (getattr).
    """

    def _get(item, key, default=""):
        return (
            item.get(key, default)
            if accessor == "dict"
            else getattr(item, key, default)
        )

    if sort_value:
        numeric = sort_value in numeric_sort_fields
        items = sorted(
            items,
            key=lambda item: float(_get(item, sort_value, 0))
            if numeric
            else str(_get(item, sort_value, "")).lower(),
            reverse=sort_reverse,
        )

    if search_value:
        sv = search_value.lower()
        items = [
            item
            for item in items
            if any(sv in str(_get(item, attr, "")).lower() for attr in search_fields)
        ]

    return items


class PaginationMixin(rx.State, mixin=True):
    """Mixin providing pagination state and navigation for table views."""

    total_items: int = 0
    offset: int = 0
    limit: int = 12

    @rx.var
    def page_number(self) -> int:
        return (self.offset // self.limit) + 1

    @rx.var
    def total_pages(self) -> int:
        return max(1, math.ceil(self.total_items / self.limit))

    def prev_page(self) -> None:
        if self.page_number > 1:
            self.offset -= self.limit

    def next_page(self) -> None:
        if self.page_number < self.total_pages:
            self.offset += self.limit

    def first_page(self) -> None:
        self.offset = 0

    def last_page(self) -> None:
        self.offset = (self.total_pages - 1) * self.limit


class SearchSortMixin(rx.State, mixin=True):
    """Mixin providing search, sort, and chart-view toggle for table states."""

    search_value: str = ""
    sort_value: str = ""
    sort_reverse: bool = False
    chart_view: bool = False

    @rx.event
    def set_search_value(self, value: str) -> None:
        self.search_value = value

    @rx.event
    def set_sort_value(self, value: str) -> None:
        self.sort_value = value

    @rx.event
    def toggle_chart_view(self) -> None:
        self.chart_view = not self.chart_view
