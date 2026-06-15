"""Domain models for companies, sectors, and industries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Industry:
    name: str
    sector: str
    description: str = ""


@dataclass
class Sector:
    name: str
    industries: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class MarketPrice:
    """A point-in-time price snapshot for a single instrument."""

    ticker: str
    price: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    change: float        # absolute change from previous close
    change_pct: float    # percentage change from previous close
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_positive(self) -> bool:
        return self.change >= 0


@dataclass
class Company:
    """Fundamental profile of a publicly listed company."""

    ticker: str
    name: str
    sector: str
    industry: str
    country: str = "India"
    exchange: str = "NSE"

    # Financials — dynamically fetched, never hardcoded
    market_cap: float = 0.0
    current_price: float = 0.0
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0
    debt_to_equity: float = 0.0
    revenue: float = 0.0
    net_profit: float = 0.0
    roe: float = 0.0          # Return on Equity
    roce: float = 0.0         # Return on Capital Employed
    dividend_yield: float = 0.0
    beta: float = 1.0         # Market beta

    description: str = ""
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_large_cap(self) -> bool:
        """True for market cap > ₹20,000 crore."""
        return self.market_cap > 20_000 * 1e7

    @property
    def is_profitable(self) -> bool:
        return self.net_profit > 0


@dataclass
class CompanyImpact:
    """
    The computed impact of a market event on a specific company.

    Produced by the ImpactEngine after graph propagation.
    """

    ticker: str
    company_name: str
    direction: float       # -1.0 (very negative) to +1.0 (very positive)
    magnitude: float       # 0.0 to 1.0 — strength of impact
    reasoning_path: list[str] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def is_positive(self) -> bool:
        return self.direction > 0

    @property
    def impact_score(self) -> float:
        """Signed impact combining direction and magnitude."""
        return self.direction * self.magnitude * 10  # scale to -10 .. +10
