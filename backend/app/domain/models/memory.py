"""Domain models for Market Memory Engine (Historical Analogy Search)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HistoricalMarketImpact:
    """Price/sector impact following a historical event."""
    nifty_30d: float        # % change in 30 days
    nifty_60d: float        # % change in 60 days
    best_sectors: list[str] = field(default_factory=list)
    worst_sectors: list[str] = field(default_factory=list)
    sector_impacts: dict[str, float] = field(default_factory=dict)  # sector → % change


@dataclass
class HistoricalEvent:
    """
    A curated historical market event in the memory archive.
    Stored with pre-computed embedding for fast vector search.
    """
    id: str
    year: int
    title: str
    description: str
    category: str           # geopolitical | economic | regulatory | company | disaster
    market_impact: HistoricalMarketImpact
    keywords: list[str] = field(default_factory=list)
    embedding: list[float] = field(default_factory=list)


@dataclass
class HistoricalAnalogy:
    """One similar historical event matched to the current event."""
    event_id: str
    year: int
    title: str
    similarity_score: float         # cosine similarity 0..1
    nifty_impact_30d: float         # what happened to Nifty in 30 days
    nifty_impact_60d: float
    best_sectors: list[str]
    worst_sectors: list[str]
    description: str = ""


@dataclass
class HistoricalAnalysisResult:
    """Full result of historical analogy search for one event."""
    event_title: str
    analogies: list[HistoricalAnalogy]
    avg_expected_impact_30d: float  # weighted average across analogies
    avg_expected_impact_60d: float
    confidence: float               # average similarity score
    summary: str = ""
