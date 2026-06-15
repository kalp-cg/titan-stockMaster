"""Domain models for portfolio management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Holding:
    """A single stock position within a user's portfolio."""

    ticker: str
    company_name: str
    quantity: float
    avg_buy_price: float

    thesis: str = ""
    thesis_health: float = 100.0
    user_id: str = ""

    # Live data — populated by portfolio_service from market data provider
    current_price: float = 0.0

    id: str = field(default_factory=lambda: str(uuid4()))
    added_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def invested_value(self) -> float:
        return self.quantity * self.avg_buy_price

    @property
    def current_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def pnl(self) -> float:
        """Absolute profit / loss in ₹."""
        return self.current_value - self.invested_value

    @property
    def pnl_pct(self) -> float:
        """Percentage profit / loss."""
        if self.invested_value == 0:
            return 0.0
        return (self.pnl / self.invested_value) * 100

    @property
    def is_in_profit(self) -> bool:
        return self.pnl > 0


@dataclass
class SectorExposure:
    """Concentration of portfolio value in a single sector."""

    sector: str
    total_value: float
    holding_count: int
    weight_pct: float  # percentage of total portfolio


@dataclass
class Portfolio:
    """Aggregated view of all user holdings."""

    holdings: list[Holding] = field(default_factory=list)

    @property
    def total_invested(self) -> float:
        return sum(h.invested_value for h in self.holdings)

    @property
    def total_value(self) -> float:
        return sum(h.current_value for h in self.holdings)

    @property
    def overall_pnl(self) -> float:
        return self.total_value - self.total_invested

    @property
    def overall_pnl_pct(self) -> float:
        if self.total_invested == 0:
            return 0.0
        return (self.overall_pnl / self.total_invested) * 100

    @property
    def tickers(self) -> list[str]:
        return [h.ticker for h in self.holdings]

    def get_holding(self, ticker: str) -> Holding | None:
        for h in self.holdings:
            if h.ticker == ticker:
                return h
        return None


@dataclass
class AffectedHolding:
    """Impact of an event on one portfolio holding."""

    ticker: str
    company_name: str
    direction: float      # -1.0 to +1.0
    magnitude: float      # 0.0 to 1.0
    reasoning: list[str] = field(default_factory=list)


@dataclass
class PortfolioImpact:
    """
    The aggregated impact of a single market event on the
    user's entire portfolio.
    """

    event_id: str
    event_title: str
    risk_score: float           # 0.0 to 1.0
    opportunity_score: float    # 0.0 to 1.0
    affected_holdings: list[AffectedHolding] = field(default_factory=list)
    explanation: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def winners(self) -> list[AffectedHolding]:
        return [h for h in self.affected_holdings if h.direction > 0]

    @property
    def losers(self) -> list[AffectedHolding]:
        return [h for h in self.affected_holdings if h.direction < 0]
