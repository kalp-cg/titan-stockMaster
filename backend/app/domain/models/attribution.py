"""Domain models for Movement Attribution Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class AttributionFactor:
    """One factor explaining a stock's price movement."""
    name: str               # human-readable factor name
    probability: float      # 0.0 to 1.0, contribution to explaining the move
    direction: str          # "positive" | "negative" | "neutral"
    evidence: str           # one-line human-readable evidence summary


@dataclass
class MoveAttribution:
    """
    Bayesian attribution of a stock's price move to causal factors.

    Factors sum to 1.0 (probability distribution).
    """
    ticker: str
    move_pct: float             # the actual price move being explained
    move_date: str              # YYYY-MM-DD
    factors: list[AttributionFactor]   # sorted desc by probability
    top_factor: str             # name of the most probable cause
    explanation_summary: str    # one-paragraph human-readable summary
    confidence: float           # overall confidence in attribution (0..1)
    volume_ratio: float = 1.0   # actual volume / 30-day average

    @property
    def primary_cause(self) -> AttributionFactor | None:
        if not self.factors:
            return None
        return self.factors[0]
