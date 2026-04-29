"""Ticker resolution logic — ISIN-to-ticker and asset type resolution.

Handles the resolution cascade:
1. ticker_info table (cached enriched metadata)
2. tickers_reference table (static reference data)
3. yfinance API (live lookup, results cached to ticker_info)
"""

import logging
from datetime import datetime

from ...entities import TickerInfo
from ...interfaces import MarketDataProvider
from ...repositories import ReferenceRepository, TickerInfoRepository
from .helpers import ISIN_RE, ResolvedTicker

logger = logging.getLogger(__name__)


def resolve_ticker_aliases(
    raw_values: list[str],
    info_repo: TickerInfoRepository | None,
    reference_repo: ReferenceRepository,
    market_data: MarketDataProvider | None,
) -> dict[str, ResolvedTicker]:
    """Resolve raw ticker column values (ISINs, tickers, names) to real tickers.

    Resolution cascade for each value:
    1. Check ticker_info table by ISIN (batch) → cached info hit
    2. Check tickers_reference exact match → already a valid ticker
    3. If ISIN pattern → yfinance lookup → cache on success
    4. None → needs manual matching

    Returns dict mapping raw_value → ResolvedTicker.
    """
    if not raw_values:
        return {}

    upper_values = [v.strip().upper() for v in raw_values if v.strip()]
    result: dict[str, ResolvedTicker] = {}

    # Step 1: Batch lookup in ticker_info table by ISIN
    cached: dict[str, TickerInfo] = {}
    if info_repo:
        isin_candidates = [v for v in upper_values if ISIN_RE.match(v)]
        if isin_candidates:
            cached = info_repo.get_by_isin(isin_candidates)

    for val in upper_values:
        if val in cached:
            info = cached[val]
            result[val] = ResolvedTicker(
                ticker=info.ticker,
                asset_type=info.asset_type,
                source="ticker_info",
            )

    remaining = [v for v in upper_values if v not in result]

    # Step 2: Check reference table for exact ticker match
    for val in remaining:
        matches = reference_repo.search(val, limit=1)
        if matches and matches[0]["ticker"].upper() == val:
            result[val] = ResolvedTicker(ticker=val, source="reference")

    remaining = [v for v in remaining if v not in result]

    # Step 3: ISIN resolution via yfinance (only for ISIN-shaped values)
    if market_data:
        for val in remaining:
            if ISIN_RE.match(val):
                ticker_info = market_data.resolve_ticker_info(val)
                if ticker_info and ticker_info.ticker:
                    symbol = ticker_info.ticker
                    # Only accept if resolved symbol differs from the ISIN
                    if symbol.upper() != val:
                        result[val] = ResolvedTicker(
                            ticker=symbol,
                            asset_type=ticker_info.asset_type,
                            source="yfinance",
                        )
                        # Cache for future imports
                        if info_repo:
                            ticker_info.isin = val
                            ticker_info.source = "yfinance"
                            ticker_info.last_updated = datetime.now().isoformat()
                            info_repo.upsert(ticker_info)

    # Step 4: Anything still remaining is unresolved
    for val in upper_values:
        if val not in result:
            result[val] = ResolvedTicker(ticker=None, source=None)

    return result


def resolve_asset_types(
    tickers: list[str],
    info_repo: TickerInfoRepository | None,
    reference_repo: ReferenceRepository,
    market_data: MarketDataProvider | None,
) -> dict[str, str | None]:
    """Look up asset type for each ticker: ticker_info → reference → yfinance.

    Returns a dict mapping ticker -> asset_type (or None if not found).
    """
    result: dict[str, str | None] = {}
    for ticker in tickers:
        upper = ticker.upper()

        # 1. Check ticker_info table
        if info_repo:
            info = info_repo.get_by_ticker([upper]).get(upper)
            if info and info.asset_type:
                result[upper] = info.asset_type.upper()
                continue

        # 2. Check reference table
        matches = reference_repo.search(ticker, limit=1)
        if matches and matches[0]["ticker"].upper() == upper:
            raw = matches[0].get("asset_type")
            if raw:
                result[upper] = raw.upper()
                continue

        # 3. Try yfinance as fallback (single API call gets both asset_type and more)
        if market_data:
            ticker_info = market_data.resolve_ticker_info(ticker)
            if ticker_info:
                asset_type = ticker_info.asset_type
                if asset_type:
                    result[upper] = asset_type
                    # Cache the result
                    if info_repo:
                        ticker_info.ticker = upper
                        ticker_info.source = "yfinance"
                        ticker_info.last_updated = datetime.now().isoformat()
                        info_repo.upsert(ticker_info)
                    continue

        result[upper] = None
    return result
