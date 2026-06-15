"""Domain models for Smart Money intelligence layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BulkDeal:
    """A single bulk/block deal recorded on NSE/BSE."""
    id: str
    ticker: str
    deal_date: str          # YYYY-MM-DD
    client_name: str
    deal_type: str          # BUY | SELL
    quantity: int
    price: float
    stakeholder_category: str = "unknown"   # institution | mutual_fund | fii | hni | unknown
    exchange: str = "NSE"


@dataclass
class InsiderTrade:
    """Promoter / designated person insider trade."""
    id: str
    ticker: str
    trade_date: str
    insider_name: str
    designation: str
    trade_type: str         # BUY | SELL
    quantity: int
    price: float
    pre_trade_holding_pct: float = 0.0
    post_trade_holding_pct: float = 0.0
    remarks: str = ""


@dataclass
class InstitutionalFlow:
    """Daily FII/DII net market-wide flow."""
    id: str
    flow_date: str          # YYYY-MM-DD
    fii_buy_cr: float       # FII gross buy in crore
    fii_sell_cr: float
    dii_buy_cr: float
    dii_sell_cr: float
    market_regime: str = "neutral"

    @property
    def fii_net_cr(self) -> float:
        return self.fii_buy_cr - self.fii_sell_cr

    @property
    def dii_net_cr(self) -> float:
        return self.dii_buy_cr - self.dii_sell_cr


@dataclass
class SmartMoneyEvidence:
    """One piece of evidence contributing to smart money score."""
    source: str             # bulk_deal | fii_flow | insider | shareholding
    description: str
    direction: str          # accumulation | distribution | neutral
    strength: float         # 0.0 to 1.0
    date: str


@dataclass
class SmartMoneyScore:
    """
    Aggregated smart money signal for one stock.

    Score is [0, 100]:
      > 65  → ACCUMULATING  (smart money buying)
      35-65 → NEUTRAL
      < 35  → DISTRIBUTING  (smart money exiting)
    """
    ticker: str
    company_name: str
    score: float
    label: str              # ACCUMULATING | NEUTRAL | DISTRIBUTING
    evidence: list[SmartMoneyEvidence] = field(default_factory=list)
    bulk_deal_net_qty: int = 0
    fii_net_3day_cr: float = 0.0
    insider_direction: str = "none"
    promoter_pledge_change_pct: float = 0.0
    computed_at: datetime = field(default_factory=datetime.utcnow)
