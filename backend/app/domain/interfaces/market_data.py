"""Port interface for market data providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

import pandas as pd

from app.domain.models.company import Company, MarketPrice


@dataclass
class OHLCVBar:
    """A single OHLCV candlestick bar."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class IMarketDataProvider(Protocol):
    """Interface for any market data adapter (yfinance, NSE direct, etc.)."""

    async def get_price(self, ticker: str) -> MarketPrice:
        """Return the latest price snapshot for a ticker."""
        ...

    async def get_prices(self, tickers: list[str]) -> dict[str, MarketPrice]:
        """Batch price fetch for multiple tickers."""
        ...

    async def get_history(
        self,
        ticker: str,
        *,
        period: str = "1y",
        interval: str = "1d",
    ) -> list[OHLCVBar]:
        """
        Fetch historical OHLCV data.

        Args:
            ticker: Instrument symbol.
            period: Time period string (e.g., "1d", "5d", "1mo", "1y").
            interval: Bar interval (e.g., "1m", "1h", "1d").
        """
        ...

    async def get_company_info(self, ticker: str) -> Company:
        """Fetch fundamental company information."""
        ...

    async def get_index_constituents(self, index: str) -> list[str]:
        """Return tickers for an index (e.g., NIFTY 50)."""
        ...
