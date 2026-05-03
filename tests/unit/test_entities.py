"""Tests for the domain entity helpers."""

from __future__ import annotations

from patrimony.backend.domain.entities import (
    AssetType,
    Currency,
    EntryType,
    PortfolioOverview,
)


def test_asset_type_enum_values():
    assert AssetType.STOCK.value == "STOCK"
    assert {at.value for at in AssetType} >= {
        "STOCK",
        "CRYPTO",
        "CASH",
        "BOND",
        "ETF",
        "COMMODITY",
        "PROPERTY",
    }


def test_entry_type_enum_values():
    assert {et.value for et in EntryType} == {"MANUAL", "WEB", "CSV", "EXCEL", "API"}


def test_currency_label_and_symbol_are_populated():
    assert Currency.EUR.symbols == "€"
    assert Currency.USD.symbols == "$"
    assert Currency.EUR.label.startswith("EUR")
    assert Currency.USD.label.startswith("USD")


def test_currency_handles_every_member():
    for c in Currency:
        assert c.symbols
        assert c.label


def test_portfolio_overview_defaults_dividends_to_zero():
    o = PortfolioOverview(
        total_value=100.0,
        total_invested=80.0,
        total_return=20.0,
        securities_value=70.0,
        cash_value=20.0,
        properties_value=10.0,
    )
    assert o.total_dividends == 0.0
    assert o.total_return_with_dividends == 0.0
