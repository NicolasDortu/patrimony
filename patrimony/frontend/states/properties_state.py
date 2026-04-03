"""State management for physical properties (real estate, valuables, etc.)."""

from datetime import datetime
from typing import Union

import reflex as rx

from ..services import PropertyService, Property
from ..utils import export_csv
from .mixins import PaginationMixin, SearchSortMixin, apply_sort_and_search
from .spreadsheet_mixin import SpreadsheetMixin

PROPERTY_CATEGORIES = [
    "Real Estate",
    "Watch",
    "Vehicle",
    "Art",
    "Jewelry",
    "Other",
]


class PropertiesState(SpreadsheetMixin, SearchSortMixin, PaginationMixin, rx.State):
    """State for the properties table."""

    items: list[dict] = []
    is_loading: bool = False

    @rx.var
    def filtered_sorted_items(self) -> list[dict]:
        return apply_sort_and_search(
            self.items,
            self.sort_value,
            self.sort_reverse,
            self.search_value,
            numeric_sort_fields=["value"],
            search_fields=["name", "description", "category"],
        )

    @rx.var(initial_value=[])
    def get_current_page(self) -> list[dict]:
        return self.filtered_sorted_items[self.offset : self.offset + self.limit]

    @rx.event
    async def on_page_load(self):
        self.is_loading = True
        yield
        self.load_entries()
        self.is_loading = False

    @rx.event
    def load_entries(self) -> None:
        items = PropertyService.get_all_properties()
        for p in items:
            raw = p.get("purchase_date", "")
            p["purchase_date"] = str(raw)[:10] if raw else ""
        self.items = items
        self.total_items = len(self.items)

    def toggle_sort(self) -> None:
        self.sort_reverse = not self.sort_reverse
        self.load_entries()

    @rx.event
    def add_property(self, form_data: dict) -> None:
        date_str = form_data.get("purchase_date", "")
        purchase_date = (
            datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
        )
        result = PropertyService.add_property(
            name=form_data.get("name", ""),
            value=float(form_data.get("value", 0)),
            purchase_date=purchase_date,
            description=form_data.get("description", ""),
            category=form_data.get("category", "Other"),
        )
        if result.success:
            self.load_entries()
            return rx.toast.success(result.message, position="top-center")
        else:
            return rx.toast.error(result.message, position="top-center")

    @rx.event
    def delete_property(self, id: Union[int, dict]) -> None:
        if isinstance(id, dict):
            id = id.get("id", 0)
        result = PropertyService.delete_property(id)
        if result.success:
            self.load_entries()
            return rx.toast.success(result.message, position="top-center")
        else:
            return rx.toast.error(result.message, position="top-center")

    @rx.event
    def export_csv(self):
        properties = PropertyService.get_all_properties()
        columns = list(Property.__dataclass_fields__.keys())
        return export_csv(properties, columns, "properties.csv")

    # ── Spreadsheet mode ──

    @rx.var
    def spreadsheet_columns(self) -> list[dict]:
        return [
            {"title": "Name", "type": "str"},
            {"title": "Description", "type": "str"},
            {"title": "Value", "type": "float"},
            {"title": "Category", "type": "str"},
            {"title": "Purchase Date", "type": "str"},
        ]

    def _load_spreadsheet_rows(self) -> tuple[list[list], list]:
        props = PropertyService.get_all_properties()
        data = [
            [
                p.get("name", ""),
                p.get("description", ""),
                p.get("value", 0.0),
                p.get("category", "Other"),
                str(p.get("purchase_date", ""))[:10],
            ]
            for p in props
        ]
        ids = [p.get("id") for p in props]
        return data, ids

    def _save_spreadsheet_row(self, row, index, rid, is_new):
        name = str(row[0]).strip()
        if not name:
            return "skip"
        description = str(row[1]).strip()
        value = float(row[2]) if row[2] != "" else 0.0
        category = str(row[3]).strip() or "Other"
        date_str = str(row[4]).strip()
        purchase_date = (
            datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
        )
        if is_new:
            PropertyService.add_property(
                name=name,
                value=value,
                purchase_date=purchase_date,
                description=description,
                category=category,
            )
        else:
            PropertyService.update_property(
                id=rid,
                name=name,
                value=value,
                purchase_date=purchase_date,
                description=description,
                category=category,
            )
        return None

    def _delete_spreadsheet_row(self, rid):
        PropertyService.delete_property(rid)

    async def _after_spreadsheet_save(self):
        self.load_entries()
