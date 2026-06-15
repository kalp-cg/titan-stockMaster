"""
Domain models for the Stakeholder Intelligence Engine (Layer 16).

Covers shareholding patterns, bulk/block deals, insider trades,
institutional flows, and smart money signals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from uuid import uuid4


class StakeholderCategory(str, Enum):
    """Category of a shareholder or market participant."""

    PROMOTER = "promoter"
    FII = "fii"               # Foreign Institutional Investor
    FPI = "fpi"               # Foreign Portfolio Investor (same as FII in practice)
    DII = "dii"               # Domestic Institutional Investor
    MUTUAL_FUND = "mutual_fund"
    INSURANCE = "insurance"
    BANK = "bank"
    GOVERNMENT = "government"
    RETAIL = "retail"
    OTHER = "other"
    UNKNOWN = "unknown"


class DealType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class ConvictionLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MarketRegime(str, Enum):
    """Market regime inferred from institutional flow patterns."""

    STRONGLY_BULLISH = "strongly_bullish"    # Both FII & DII buying
    BULLISH = "bullish"                       # FII buying, DII neutral
    CAUTIOUS = "cautious"                     # FII selling, DII absorbing
    BEARISH = "bearish"                       # Both selling
    VOLATILE = "volatile"                     # Diverging large flows
    NEUTRAL = "neutral"


@dataclass
class InstitutionalHolder:
    """A named institutional shareholder and their current holding."""

    name: str
    category: StakeholderCategory
    holding_pct: float
    shares_held: int = 0
    change_vs_prev_quarter: float = 0.0   # percentage point change
    profit_cr: float = 0.0

    @property
    def is_accumulating(self) -> bool:
        return self.change_vs_prev_quarter > 0


@dataclass
class ShareholdingPattern:
    """
    Quarterly shareholding breakdown for a company.

    All percentage fields are sourced dynamically from NSE/BSE filings.
    """

    ticker: str
    quarter: str                 # e.g., "Q1-2026"
    as_of_date: date

    promoter_pct: float = 0.0
    promoter_pledge_pct: float = 0.0    # Pledged shares as % of promoter holding
    fii_pct: float = 0.0
    dii_pct: float = 0.0
    mutual_fund_pct: float = 0.0
    insurance_pct: float = 0.0
    bank_pct: float = 0.0
    government_pct: float = 0.0
    retail_pct: float = 0.0
    other_pct: float = 0.0

    top_holders: list[InstitutionalHolder] = field(default_factory=list)

    # QoQ deltas — computed by the service, not stored raw
    promoter_delta: float = 0.0
    fii_delta: float = 0.0
    dii_delta: float = 0.0
    mutual_fund_delta: float = 0.0

    id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def institutional_total_pct(self) -> float:
        return self.fii_pct + self.dii_pct

    @property
    def is_promoter_strong(self) -> bool:
        """True when promoter holding is above 50% with minimal pledge."""
        return self.promoter_pct >= 50.0 and self.promoter_pledge_pct < 5.0


@dataclass
class BulkDeal:
    """
    A bulk deal disclosure from NSE/BSE.

    Bulk deal: any single transaction > 0.5% of total equity.
    """

    ticker: str
    date: date
    client_name: str
    deal_type: DealType
    quantity: int
    price: float
    stakeholder_category: StakeholderCategory = StakeholderCategory.UNKNOWN
    exchange: str = "NSE"

    id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def total_value(self) -> float:
        return self.quantity * self.price

    @property
    def is_institutional(self) -> bool:
        return self.stakeholder_category in {
            StakeholderCategory.FII,
            StakeholderCategory.DII,
            StakeholderCategory.MUTUAL_FUND,
            StakeholderCategory.INSURANCE,
        }


@dataclass
class BlockDeal:
    """
    A block deal disclosure (minimum ₹10 crore negotiated trade).

    Block deals execute in a special pre-market window and are
    disclosed the same day.
    """

    ticker: str
    date: date
    client_name: str
    deal_type: DealType
    quantity: int
    price: float
    window: str = "opening"    # "opening" or "closing"
    stakeholder_category: StakeholderCategory = StakeholderCategory.UNKNOWN
    exchange: str = "NSE"

    id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def total_value(self) -> float:
        return self.quantity * self.price


@dataclass
class InsiderTrade:
    """
    A SEBI-mandated insider trading disclosure.

    Covers directors, KMPs, and connected persons trading their own
    company's securities.
    """

    ticker: str
    date: date
    insider_name: str
    designation: str             # e.g., "Director", "CFO", "Promoter"
    trade_type: DealType
    quantity: int
    price: float
    pre_trade_holding_pct: float = 0.0
    post_trade_holding_pct: float = 0.0
    remarks: str = ""

    id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def total_value(self) -> float:
        return self.quantity * self.price

    @property
    def holding_change_pct(self) -> float:
        return self.post_trade_holding_pct - self.pre_trade_holding_pct

    @property
    def is_director_level(self) -> bool:
        return any(
            kw in self.designation.lower()
            for kw in ("director", "ceo", "cfo", "cto", "coo", "md", "chairman")
        )


@dataclass
class InstitutionalFlow:
    """
    Daily aggregate FII and DII buy/sell activity across the market.

    Values in ₹ crore.
    """

    date: date
    fii_buy_cr: float
    fii_sell_cr: float
    dii_buy_cr: float
    dii_sell_cr: float
    market_regime: MarketRegime = MarketRegime.NEUTRAL

    id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def fii_net_cr(self) -> float:
        return self.fii_buy_cr - self.fii_sell_cr

    @property
    def dii_net_cr(self) -> float:
        return self.dii_buy_cr - self.dii_sell_cr

    @property
    def combined_net_cr(self) -> float:
        return self.fii_net_cr + self.dii_net_cr


@dataclass
class EvidenceFactor:
    """A single signal contributing to a SmartMoneySignal."""

    description: str
    weight: float           # contribution [0.0, 1.0]
    is_positive: bool       # True = accumulation evidence


@dataclass
class SmartMoneySignal:
    """
    Composite conviction signal for a company.

    Accumulation and distribution scores are computed dynamically from
    all available stakeholder data signals — no static weights.
    Weights are calibrated from historical signal-to-outcome correlations.
    """

    ticker: str
    company_name: str
    accumulation_score: float   # 0.0 to 1.0
    distribution_score: float   # 0.0 to 1.0
    conviction_level: ConvictionLevel
    divergence_alerts: list[str] = field(default_factory=list)
    evidence: list[EvidenceFactor] = field(default_factory=list)

    timestamp: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid4()))
    net_score: float = 0.0
    has_divergence: bool = False

    def __post_init__(self) -> None:
        self.net_score = round(self.accumulation_score - self.distribution_score, 2)
        self.has_divergence = len(self.divergence_alerts) > 0
