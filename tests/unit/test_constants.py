"""Tests for domain constants."""

from __future__ import annotations

import pytest

from patrimony.backend.domain.constants import (
    ASSET_TYPE_LABELS,
    DEFAULT_CURRENCY,
    DEFAULT_PERIOD,
    MIN_CHART_DAYS,
    PERIOD_CONFIG,
)


def test_period_config_keys():
    assert set(PERIOD_CONFIG) == {"1D", "5D", "1M", "6M", "1Y", "5Y"}


@pytest.mark.parametrize("period", list(PERIOD_CONFIG))
def test_period_config_entries_have_required_fields(period):
    cfg = PERIOD_CONFIG[period]
    assert {"days", "period", "interval", "format"} <= cfg.keys()
    assert isinstance(cfg["days"], int) and cfg["days"] > 0


def test_default_period_is_in_period_config():
    assert DEFAULT_PERIOD in PERIOD_CONFIG


def test_default_currency_is_eur():
    assert DEFAULT_CURRENCY == "EUR"


def test_min_chart_days_is_positive():
    assert MIN_CHART_DAYS >= 1


def test_asset_type_labels_cover_known_types():
    expected = {"STOCK", "ETF", "CRYPTO", "COMMODITY", "BOND", "CASH", "PROPERTY"}
    assert expected <= set(ASSET_TYPE_LABELS)
