"""Domain models for IPO intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from uuid import uuid4


class IPOStatus(str, Enum):
    UPCOMING = "upcoming"
    OPEN = "open"
    CLOSED = "closed"
    LISTED = "listed"
    WITHDRAWN = "withdrawn"


@dataclass
class IPOFinancials:
    """Key financial metrics for IPO scoring — all dynamically sourced."""

    revenue: float = 0.0
    revenue_growth_yoy: float = 0.0    # YoY revenue growth %
    net_profit: float = 0.0
    net_profit_margin: float = 0.0     # %
    ebitda_margin: float = 0.0         # %
    debt_to_equity: float = 0.0
    roe: float = 0.0
    cash_flow_from_operations: float = 0.0
    pe_ratio: float = 0.0              # at upper band price
    ev_to_ebitda: float = 0.0


@dataclass
class IPOScore:
    """
    Composite IPO attractiveness score.

    All component scores are computed dynamically from the IPOFinancials
    and sector data — nothing is hardcoded.
    """

    revenue_growth_score: float     # 0.0 - 10.0
    profitability_score: float
    debt_score: float
    valuation_score: float
    sector_trend_score: float
    gmp_score: float                # Grey Market Premium signal

    @property
    def composite(self) -> float:
        """Weighted composite score out of 10."""
        weights = {
            "revenue_growth": 0.25,
            "profitability": 0.25,
            "debt": 0.15,
            "valuation": 0.15,
            "sector_trend": 0.10,
            "gmp": 0.10,
        }
        return (
            self.revenue_growth_score * weights["revenue_growth"]
            + self.profitability_score * weights["profitability"]
            + self.debt_score * weights["debt"]
            + self.valuation_score * weights["valuation"]
            + self.sector_trend_score * weights["sector_trend"]
            + self.gmp_score * weights["gmp"]
        )


@dataclass
class IPO:
    """Complete IPO data model."""

    name: str
    status: IPOStatus
    sector: str
    industry: str
    ipo_type: str = "mainboard"  # "mainboard" or "sme"

    # Pricing
    price_band_low: float = 0.0
    price_band_high: float = 0.0
    lot_size: int = 0

    # Issue details
    issue_size_cr: float = 0.0       # ₹ crore
    fresh_issue_cr: float = 0.0
    ofs_cr: float = 0.0              # Offer for Sale

    # Timeline
    open_date: date | None = None
    close_date: date | None = None
    listing_date: date | None = None

    # Market signal
    gmp: float = 0.0                 # Grey Market Premium (₹)
    subscription_overall: float = 0.0  # times
    subscription_qib: float = 0.0      # times
    subscription_hni: float = 0.0      # times
    subscription_retail: float = 0.0   # times

    # Financials and scores
    financials: IPOFinancials = field(default_factory=IPOFinancials)
    score: IPOScore | None = None

    # Post-listing
    listing_price: float | None = None
    listing_gain_pct: float | None = None

    ticker: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def gmp_pct(self) -> float:
        if self.price_band_high == 0:
            return 0.0
        return (self.gmp / self.price_band_high) * 100
