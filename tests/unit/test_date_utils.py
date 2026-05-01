"""Tests for date_utils.normalize_date."""

from __future__ import annotations

from datetime import date, datetime

from patrimony.backend.domain.services.date_utils import normalize_date


def test_datetime_is_normalised_to_date():
    assert normalize_date(datetime(2024, 6, 1, 14, 30)) == date(2024, 6, 1)


def test_date_is_returned_as_is():
    d = date(2024, 6, 1)
    assert normalize_date(d) == d
