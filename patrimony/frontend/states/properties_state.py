"""State management for physical properties (real estate, valuables, etc.)."""

from typing import Union

import reflex as rx

from ..services import PropertyService, Property
from ..utils import export_csv, get_pie_color, parse_form_date
from .aggregation_helpers import add_percentages
from .mixins import (
    AddDialogMixin,
    PaginationMixin,
    SearchSortMixin,
    apply_sort_and_search,
)
from .spreadsheet_helpers import cell_date, cell_float, cell_str, fmt_date_cell
from .spreadsheet_mixin import SpreadsheetMixin


class PropertiesState(
    SpreadsheetMixin, SearchSortMixin, PaginationMixin, AddDialogMixin, rx.State
):
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
    def category_allocation_data(self) -> list[dict]:
        """Group property values by category for pie chart."""
        categories: dict[str, float] = {}
        for prop in self.items:
            cat = prop.get("category") or "Uncategorized"
            categories[cat] = categories.get(cat, 0.0) + float(prop.get("value", 0))
        rows = [
            {
                "name": k,
                "value": round(v, 2),
                "fill": get_pie_color(i),
            }
            for i, (k, v) in enumerate(
                sorted(categories.items(), key=lambda x: x[1], reverse=True)
            )
        ]
        return add_percentages(rows)

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
        purchase_date = parse_form_date(date_str)
        result = PropertyService.add_property(
            name=form_data.get("name", ""),
            value=float(form_data.get("value", 0)),
            purchase_date=purchase_date,
            description=form_data.get("description", ""),
            category=form_data.get("category", "").strip() or "Uncategorized",
            currency=form_data.get("currency", "EUR"),
        )
        if result.success:
            self.load_entries()
            self.add_dialog_open = False
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
            {"title": "Name", "type": "str", "grow": 1},
            {"title": "Description", "type": "str", "grow": 1},
            {"title": "Value", "type": "float", "grow": 1},
            {"title": "Category", "type": "str", "grow": 1},
            {"title": "Currency", "type": "str", "grow": 1},
            {"title": "Purchase Date", "type": "str", "grow": 1},
        ]

    def _load_spreadsheet_rows(self) -> tuple[list[list], list]:
        props = PropertyService.get_all_properties()
        data = [
            [
                p.get("name", ""),
                p.get("description", ""),
                p.get("value", 0.0),
                p.get("category", "Uncategorized"),
                p.get("currency", "EUR"),
                fmt_date_cell(p.get("purchase_date", "")),
            ]
            for p in props
        ]
        ids = [p.get("id") for p in props]
        return data, ids

    def _save_spreadsheet_row(self, row, index, rid, is_new):
        name = cell_str(row[0])
        if not name:
            return "skip"
        description = cell_str(row[1])
        value = cell_float(row[2])
        category = cell_str(row[3], default="Uncategorized")
        currency = cell_str(row[4], default="EUR")
        purchase_date = cell_date(row[5])
        if is_new:
            PropertyService.add_property(
                name=name,
                value=value,
                purchase_date=purchase_date,
                description=description,
                category=category,
                currency=currency,
            )
        else:
            PropertyService.update_property(
                id=rid,
                name=name,
                value=value,
                purchase_date=purchase_date,
                description=description,
                category=category,
                currency=currency,
            )
        return None

    def _delete_spreadsheet_row(self, rid):
        PropertyService.delete_property(rid)

    async def _after_spreadsheet_save(self):
        self.load_entries()
