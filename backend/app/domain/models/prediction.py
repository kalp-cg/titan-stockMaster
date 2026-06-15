"""Domain models for market predictions and probability distributions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class Signal(str, Enum):
    """Discretised trading signal derived from probability distribution."""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class VolatilityRegime(str, Enum):
    """Current market volatility state for the instrument."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class ProbabilityDistribution:
    """
    Output of the market reaction predictor.

    All probabilities must sum to 1.0.
    No deterministic price targets — only probability distributions.
    """

    bullish_probability: float   # P(price up significantly)
    neutral_probability: float   # P(price roughly unchanged)
    bearish_probability: float   # P(price down significantly)
    expected_move_pct: float     # Signed expected percentage move
    volatility_regime: VolatilityRegime = VolatilityRegime.MEDIUM

    def __post_init__(self) -> None:
        total = self.bullish_probability + self.neutral_probability + self.bearish_probability
        if total > 0 and abs(total - 1.0) > 0.05:
            # Normalise if rounding caused slight deviation
            self.bullish_probability /= total
            self.neutral_probability /= total
            self.bearish_probability /= total

    @property
    def dominant_signal(self) -> Signal:
        """Derive a signal label from the probability distribution."""
        b = self.bullish_probability
        be = self.bearish_probability

        if b >= 0.65:
            return Signal.STRONG_BUY
        elif b >= 0.55:
            return Signal.BUY
        elif be >= 0.65:
            return Signal.STRONG_SELL
        elif be >= 0.55:
            return Signal.SELL
        else:
            return Signal.HOLD


@dataclass
class EvidenceItem:
    """A single piece of evidence contributing to a prediction."""

    source: str          # e.g., "historical_similarity", "graph_propagation"
    description: str
    weight: float        # contribution weight [0.0, 1.0]


@dataclass
class Prediction:
    """
    A probabilistic market prediction for a single instrument.

    Created by the PredictionService and stored for self-learning
    evaluation once the horizon elapses.
    """

    ticker: str
    horizon_days: int
    distribution: ProbabilityDistribution
    confidence: float           # composite model confidence [0.0, 1.0]
    evidence_count: int         # number of pieces of evidence used
    historical_match_score: float  # similarity to historical events [0.0, 1.0]
    reasoning_chain: list[str] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)

    # Self-learning fields — populated after the horizon elapses
    actual_move_pct: float | None = None
    prediction_correct: bool | None = None

    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = ""

    @property
    def signal(self) -> Signal:
        return self.distribution.dominant_signal

    @property
    def is_evaluated(self) -> bool:
        return self.prediction_correct is not None
