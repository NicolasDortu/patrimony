"""Reusable state mixins for frontend components."""

import reflex as rx


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
        return max(
            1,
            (self.total_items // self.limit)
            + (1 if self.total_items % self.limit else 0),
        )

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
