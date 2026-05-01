"""Tests for the generic search/sort/pagination helpers used by every table state."""

from __future__ import annotations

import math

import pytest

from patrimony.frontend.states.mixins import apply_sort_and_search


ITEMS = [
    {"name": "Alpha", "value": 30},
    {"name": "beta", "value": 10},
    {"name": "Gamma", "value": 20},
]


def test_sort_alphabetical_case_insensitive():
    result = apply_sort_and_search(
        ITEMS,
        sort_value="name",
        sort_reverse=False,
        search_value="",
        numeric_sort_fields=[],
        search_fields=[],
    )
    assert [r["name"] for r in result] == ["Alpha", "beta", "Gamma"]


def test_sort_numeric_descending():
    result = apply_sort_and_search(
        ITEMS,
        sort_value="value",
        sort_reverse=True,
        search_value="",
        numeric_sort_fields=["value"],
        search_fields=[],
    )
    assert [r["value"] for r in result] == [30, 20, 10]


def test_search_filters_case_insensitively():
    result = apply_sort_and_search(
        ITEMS,
        sort_value="",
        sort_reverse=False,
        search_value="GA",
        numeric_sort_fields=[],
        search_fields=["name"],
    )
    assert [r["name"] for r in result] == ["Gamma"]


def test_search_returns_empty_when_no_match():
    result = apply_sort_and_search(
        ITEMS,
        sort_value="",
        sort_reverse=False,
        search_value="zzz",
        numeric_sort_fields=[],
        search_fields=["name"],
    )
    assert result == []


def test_search_works_with_attribute_accessor():
    class Item:
        def __init__(self, name):
            self.name = name

    items = [Item("Alpha"), Item("Beta")]
    result = apply_sort_and_search(
        items,
        sort_value="",
        sort_reverse=False,
        search_value="alp",
        numeric_sort_fields=[],
        search_fields=["name"],
        accessor="attr",
    )
    assert [i.name for i in result] == ["Alpha"]


def test_no_sort_no_search_preserves_order():
    result = apply_sort_and_search(
        ITEMS,
        sort_value="",
        sort_reverse=False,
        search_value="",
        numeric_sort_fields=[],
        search_fields=[],
    )
    assert result == ITEMS


def test_sort_falls_back_to_zero_for_missing_numeric_field():
    items = [{"value": 5}, {}, {"value": 1}]
    result = apply_sort_and_search(
        items,
        sort_value="value",
        sort_reverse=False,
        search_value="",
        numeric_sort_fields=["value"],
        search_fields=[],
    )
    assert [r.get("value") for r in result] == [None, 1, 5]


# ── Sanity checks on the pagination math used by PaginationMixin ──────────


@pytest.mark.parametrize(
    "total, limit, offset, expected_page, expected_pages",
    [
        (0, 12, 0, 1, 1),
        (5, 12, 0, 1, 1),
        (12, 12, 0, 1, 1),
        (13, 12, 0, 1, 2),
        (24, 12, 12, 2, 2),
        (25, 12, 24, 3, 3),
    ],
)
def test_pagination_math(total, limit, offset, expected_page, expected_pages):
    page = (offset // limit) + 1
    pages = max(1, math.ceil(total / limit))
    assert page == expected_page
    assert pages == expected_pages
