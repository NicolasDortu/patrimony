"""Tests for domain exception formatting."""

from __future__ import annotations

import pytest

from patrimony.backend.domain.exceptions import (
    AssetTypeResolutionError,
    CurrencyConversionError,
    DataFetchError,
    DateParsingError,
    DividendSyncError,
    DomainError,
    ImportError as DomainImportError,
    MissingColumnError,
    MissingMappingError,
    PriceSyncError,
    SyncError,
)


def test_missing_mapping_error_lists_fields_sorted():
    err = MissingMappingError({"ticker", "amount", "date"})
    assert isinstance(err, DomainImportError)
    assert "amount" in str(err)
    assert "date" in str(err)
    assert "ticker" in str(err)
    # Sorted alphabetically.
    assert str(err).index("amount") < str(err).index("date") < str(err).index("ticker")


def test_missing_column_error_lists_columns():
    err = MissingColumnError({"col_a"})
    assert "col_a" in str(err)


def test_asset_type_resolution_error_with_row():
    err = AssetTypeResolutionError("AAPL", row=3)
    msg = str(err)
    assert "Row 3" in msg
    assert "AAPL" in msg


def test_asset_type_resolution_error_without_row():
    err = AssetTypeResolutionError("AAPL")
    assert "Row" not in str(err)
    assert "AAPL" in str(err)


def test_date_parsing_error_includes_value():
    err = DateParsingError("not-a-date")
    assert "not-a-date" in str(err)


def test_price_sync_error_chains_cause():
    inner = ValueError("rate limited")
    err = PriceSyncError("AAPL", cause=inner)
    assert isinstance(err, SyncError)
    assert "AAPL" in str(err)
    assert "rate limited" in str(err)


def test_dividend_sync_error_without_cause():
    err = DividendSyncError("MSFT")
    assert "MSFT" in str(err)


def test_data_fetch_error_chains_cause():
    err = DataFetchError("revolut", cause=RuntimeError("login failed"))
    assert "revolut" in str(err)
    assert "login failed" in str(err)


def test_currency_conversion_error_extends_domain_error():
    err = CurrencyConversionError("USD", "EUR")
    assert isinstance(err, DomainError)
    assert err.from_currency == "USD"
    assert err.to_currency == "EUR"


@pytest.mark.parametrize(
    "exc_cls",
    [
        MissingMappingError,
        MissingColumnError,
        AssetTypeResolutionError,
        DateParsingError,
        PriceSyncError,
        DividendSyncError,
        DataFetchError,
    ],
)
def test_all_import_and_sync_errors_inherit_domain_error(exc_cls):
    assert issubclass(exc_cls, DomainError)
