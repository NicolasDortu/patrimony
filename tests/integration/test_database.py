"""Integration tests against a real (temporary) DuckDB instance.

These tests exercise the schema and the SQL contracts of the repositories
to catch regressions in DDL and the cash balance recomputation trigger.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from patrimony.backend.domain.entities import Currency, EntryType
from patrimony.backend.infrastructure.repositories.cash_repository import (
    CashRepositoryImpl,
)
from patrimony.backend.infrastructure.repositories.dividend_repository import (
    DividendRepositoryImpl,
)
from patrimony.backend.infrastructure.repositories.property_repository import (
    PropertyRepositoryImpl,
)


pytestmark = pytest.mark.integration


# ── Schema ──────────────────────────────────────────────────────────


EXPECTED_TABLES = {
    "positions",
    "positions_closed",
    "dividends",
    "cash",
    "balance_operations",
    "price_cache",
    "price_history",
    "intraday_prices",
    "ticker_currency",
    "exchange_rate_cache",
    "tickers_reference",
    "ticker_info",
    "properties",
    "connector_master_key",
    "connector_credentials",
    "connector_history",
    "import_hashes",
    "event_log",
}


def test_init_db_creates_all_expected_tables(tmp_db):
    rows = tmp_db.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()
    table_names = {row[0] for row in rows}
    missing = EXPECTED_TABLES - table_names
    assert not missing, f"Missing tables: {missing}"


def test_init_db_creates_helper_views(tmp_db):
    rows = tmp_db.execute(
        "SELECT table_name FROM information_schema.views WHERE table_schema='main'"
    ).fetchall()
    views = {row[0] for row in rows}
    assert {"positions_total", "cash_balance", "user_asset_types"} <= views


# ── Cash repository ────────────────────────────────────────────────


def _add_account(repo: CashRepositoryImpl, account_number: str = "ACC-1") -> str:
    repo.add_cash(
        bank="Test Bank",
        account_number=account_number,
        currency=Currency.EUR,
        last_updated=datetime(2024, 1, 1, 12, 0),
    )
    return account_number


def test_cash_account_round_trip(tmp_db):
    repo = CashRepositoryImpl(tmp_db)
    account = _add_account(repo)
    assert repo.get_balance(account) == pytest.approx(0.0)

    repo.add_operation_balance(
        account_number=account,
        amount=100.0,
        title="Initial deposit",
        operation_date=datetime(2024, 1, 2),
        entry_type=EntryType.MANUAL,
    )
    repo.add_operation_balance(
        account_number=account,
        amount=-25.0,
        title="Coffee",
        operation_date=datetime(2024, 1, 3),
        entry_type=EntryType.MANUAL,
    )

    assert repo.get_balance(account) == pytest.approx(75.0)
    assert repo.get_total_balance() == pytest.approx(75.0)


def test_cash_total_balance_sums_across_accounts(tmp_db):
    repo = CashRepositoryImpl(tmp_db)
    _add_account(repo, "ACC-A")
    _add_account(repo, "ACC-B")

    repo.add_operation_balance(
        "ACC-A", 50.0, "x", datetime(2024, 1, 1), EntryType.MANUAL
    )
    repo.add_operation_balance(
        "ACC-B", 30.0, "y", datetime(2024, 1, 1), EntryType.MANUAL
    )

    assert repo.get_total_balance() == pytest.approx(80.0)


def test_cash_delete_account_removes_balance(tmp_db):
    repo = CashRepositoryImpl(tmp_db)
    _add_account(repo)
    repo.add_operation_balance(
        "ACC-1", 10.0, "t", datetime(2024, 1, 1), EntryType.MANUAL
    )
    assert repo.get_balance("ACC-1") == pytest.approx(10.0)

    repo.delete("ACC-1")

    assert repo.get_total_balance() == pytest.approx(0.0)
    rows = tmp_db.execute(
        "SELECT 1 FROM cash WHERE account_number = ?", ["ACC-1"]
    ).fetchall()
    assert rows == []


# ── Property repository ────────────────────────────────────────────


def test_property_add_and_aggregate(tmp_db):
    repo = PropertyRepositoryImpl(tmp_db)
    repo.add_property(
        name="Apartment",
        value=200_000.0,
        purchase_date=datetime(2020, 1, 1),
        category="Real Estate",
        currency="EUR",
    )
    repo.add_property(
        name="Garage",
        value=20_000.0,
        purchase_date=datetime(2021, 1, 1),
        category="Real Estate",
        currency="EUR",
    )

    df = repo.get_total_value_by_currency()
    rows = {row["currency"]: row["total_value"] for row in df.to_dicts()}
    assert rows["EUR"] == pytest.approx(220_000.0)


def test_property_delete(tmp_db):
    repo = PropertyRepositoryImpl(tmp_db)
    repo.add_property(name="House", value=1.0, purchase_date=datetime(2024, 1, 1))
    row = repo.get_all().to_dicts()[0]
    repo.delete(row["id"])
    assert repo.get_all().is_empty()


# ── Dividend repository ────────────────────────────────────────────


def test_dividend_totals(tmp_db):
    repo = DividendRepositoryImpl(tmp_db)
    repo.add_dividend("AAPL", 1.50, datetime(2024, 3, 1))
    repo.add_dividend("AAPL", 1.75, datetime(2024, 6, 1))
    repo.add_dividend("MSFT", 0.75, datetime(2024, 4, 1))

    assert repo.get_total_amount() == pytest.approx(4.0)
    totals = repo.get_totals_by_ticker()
    assert totals["AAPL"] == pytest.approx(3.25)
    assert totals["MSFT"] == pytest.approx(0.75)


def test_dividend_get_by_ticker_orders_desc(tmp_db):
    repo = DividendRepositoryImpl(tmp_db)
    repo.add_dividend("AAPL", 1.0, datetime(2024, 1, 1))
    repo.add_dividend("AAPL", 2.0, datetime(2024, 6, 1))

    rows = repo.get_by_ticker("AAPL").to_dicts()
    assert [r["amount"] for r in rows] == [2.0, 1.0]


# ── Tickers reference ──────────────────────────────────────────────


def test_tickers_reference_loaded_at_init(tmp_db):
    count = tmp_db.execute("SELECT COUNT(*) FROM tickers_reference").fetchone()[0]
    # The CSV ships with the project; if it's empty something is wrong with
    # the bundled data. We accept zero only if the CSV file is also absent.
    from pathlib import Path

    csv_path = Path(
        "patrimony/backend/infrastructure/database/data/tickers.csv"
    ).resolve()
    if csv_path.exists():
        assert count > 0
