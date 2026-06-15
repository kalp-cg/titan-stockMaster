"""
Domain models for market events.

These are pure Python dataclasses with no ORM or framework coupling.
The infrastructure layer maps these to/from the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    import numpy as np

    from app.domain.models.entity import ExtractedEntity


class EventCategory(str, Enum):
    """Top-level classification of a market event."""

    GEOPOLITICAL = "geopolitical"
    ECONOMIC = "economic"
    COMPANY = "company"
    REGULATORY = "regulatory"
    MARKET = "market"
    UNKNOWN = "unknown"


class EventSubCategory(str, Enum):
    """Granular event sub-type within a category."""

    # Geopolitical
    WAR = "war"
    SANCTIONS = "sanctions"
    TRADE_WAR = "trade_war"
    MILITARY_ACTION = "military_action"
    BORDER_DISPUTE = "border_dispute"
    ELECTION = "election"
    POLITICAL_CRISIS = "political_crisis"

    # Economic
    INFLATION = "inflation"
    DEFLATION = "deflation"
    GDP = "gdp"
    INTEREST_RATE = "interest_rate"
    UNEMPLOYMENT = "unemployment"
    CURRENCY_CRISIS = "currency_crisis"
    COMMODITY_SHOCK = "commodity_shock"

    # Company
    EARNINGS = "earnings"
    MERGER = "merger"
    ACQUISITION = "acquisition"
    LAYOFFS = "layoffs"
    CEO_CHANGE = "ceo_change"
    PRODUCT_LAUNCH = "product_launch"
    PRODUCT_RECALL = "product_recall"
    BANKRUPTCY = "bankruptcy"
    GUIDANCE_UPGRADE = "guidance_upgrade"
    GUIDANCE_DOWNGRADE = "guidance_downgrade"

    # Regulatory
    GOVERNMENT_BAN = "government_ban"
    REGULATORY_APPROVAL = "regulatory_approval"
    ANTITRUST = "antitrust"
    SUBSIDY = "subsidy"
    POLICY_CHANGE = "policy_change"
    INVESTIGATION = "investigation"

    # Market
    IPO = "ipo"
    FPO = "fpo"
    RIGHTS_ISSUE = "rights_issue"
    CRASH = "crash"
    RALLY = "rally"
    VOLATILITY_SPIKE = "volatility_spike"

    UNKNOWN = "unknown"


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class MarketEvent:
    """
    A structured, classified market event derived from raw news.

    All fields except ``id`` and ``timestamp`` are populated
    progressively through the NLP pipeline.
    """

    title: str
    raw_text: str
    source: str

    # Classification outputs
    category: EventCategory = EventCategory.UNKNOWN
    sub_category: EventSubCategory = EventSubCategory.UNKNOWN
    sentiment: SentimentLabel = SentimentLabel.NEUTRAL

    # Severity 0.0 (trivial) → 1.0 (systemic crisis)
    severity: float = 0.0
    # Model confidence in the above classification
    confidence: float = 0.0

    # Geographic and industry scope
    affected_regions: list[str] = field(default_factory=list)
    affected_industries: list[str] = field(default_factory=list)

    # NLP outputs
    summary: str = ""
    entities: list[ExtractedEntity] = field(default_factory=list)

    # Vector embedding — stored separately, not persisted in the main table
    embedding: "np.ndarray | None" = field(default=None, repr=False)

    # Identity
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    url: str = ""

    @property
    def is_high_severity(self) -> bool:
        return self.severity >= 0.7

    @property
    def is_classified(self) -> bool:
        return self.category != EventCategory.UNKNOWN

    def __hash__(self) -> int:
        return hash(self.id)
