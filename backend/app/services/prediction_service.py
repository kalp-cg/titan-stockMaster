"""Prediction engine service.

Combines economic graph impacts, historical similarity match results,
and smart money signals to output a stock price probability distribution.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.domain.interfaces.repository import IPredictionRepository
from app.domain.interfaces.similarity_engine import ISimilarityEngine
from app.domain.models.company import CompanyImpact
from app.domain.models.event import MarketEvent
from app.domain.models.prediction import (
    Prediction,
    ProbabilityDistribution,
    VolatilityRegime,
)
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


class PredictionService:
    """Orchestrates probabilistic stock predictions."""

    def __init__(
        self,
        prediction_repository: IPredictionRepository,
        similarity_engine: ISimilarityEngine,
        stakeholder_service: Any = None,
        broadcast_callback: Any = None,
    ) -> None:
        self._repository = prediction_repository
        self._similarity = similarity_engine
        self._stakeholder_service = stakeholder_service
        self._broadcast_callback = broadcast_callback

    @timed
    async def generate_predictions(
        self, event: MarketEvent, impacts: list[CompanyImpact]
    ) -> list[Prediction]:
        logger.info("Generating stock predictions", event_id=event.id, count=len(impacts))
        predictions = []

        sim_matches = []
        if event.embedding is not None:
            try:
                sim_matches = self._similarity.find_similar(event.embedding, top_k=3)
            except Exception as e:
                logger.error("Failed to fetch similarity matches", error=str(e))

        for impact in impacts:
            try:
                ticker = impact.ticker

                sm_net = 0.0
                sm_desc = "Neutral smart money signals."
                if self._stakeholder_service:
                    sm_sig = await self._stakeholder_service.get_smart_money_signal(ticker)
                    if sm_sig:
                        sm_net = sm_sig.net_score
                        sm_desc = f"Smart money conviction: {sm_sig.conviction_level.value} (accumulation: {sm_sig.accumulation_score:.2f}, distribution: {sm_sig.distribution_score:.2f})."

                direction = impact.direction
                magnitude = impact.magnitude
                graph_effect = direction * magnitude

                bullish = 0.33
                neutral = 0.34
                bearish = 0.33

                shift = (graph_effect * 0.25) + (sm_net * 0.15)

                hist_effect = 0.0
                hist_evidence_count = len(sim_matches)
                if sim_matches:
                    hist_effect = sum(
                        m.similarity_score * (1.0 if event.sentiment == "positive" else -1.0)
                        for m in sim_matches
                    ) / len(sim_matches)
                    shift += hist_effect * 0.1

                if shift > 0:
                    bullish += shift
                    bearish -= shift * 0.8
                    neutral = 1.0 - (bullish + bearish)
                else:
                    bearish += abs(shift)
                    bullish -= abs(shift) * 0.8
                    neutral = 1.0 - (bullish + bearish)

                bullish = max(0.05, min(0.90, bullish))
                bearish = max(0.05, min(0.90, bearish))
                neutral = max(0.05, min(0.90, neutral))
                total = bullish + neutral + bearish
                bullish /= total
                neutral /= total
                bearish /= total

                expected_move = graph_effect * 4.0 * (1.0 + abs(sm_net))

                if abs(expected_move) > 5.0 or event.severity > 0.7:
                    vol_regime = VolatilityRegime.HIGH
                elif abs(expected_move) < 1.5:
                    vol_regime = VolatilityRegime.LOW
                else:
                    vol_regime = VolatilityRegime.MEDIUM

                dist = ProbabilityDistribution(
                    bullish_probability=round(bullish, 3),
                    neutral_probability=round(neutral, 3),
                    bearish_probability=round(bearish, 3),
                    expected_move_pct=round(expected_move, 2),
                    volatility_regime=vol_regime,
                )

                confidence = (impact.confidence * 0.5) + 0.24
                if sim_matches:
                    confidence += 0.2

                reasoning = [
                    f"Economic knowledge graph propagated impact from starting nodes: {impact.reasoning_path[-1] if impact.reasoning_path else 'direct relationship'}.",
                    f"Computed signed impact score of {impact.impact_score:+.2f}/10.",
                    sm_desc,
                ]
                if sim_matches:
                    reasoning.append(
                        f"Analyzed {len(sim_matches)} historically similar event patterns in vector space (average similarity {sum(m.similarity_score for m in sim_matches)/len(sim_matches):.2f})."
                    )

                horizons = [1, 3, 7, 30]
                for horizon in horizons:
                    pred = Prediction(
                        id=str(uuid4()),
                        ticker=ticker,
                        event_id=event.id,
                        horizon_days=horizon,
                        distribution=dist,
                        confidence=round(confidence, 2),
                        evidence_count=1 + hist_evidence_count,
                        historical_match_score=round(
                            sum(m.similarity_score for m in sim_matches) / len(sim_matches)
                            if sim_matches
                            else 0.0,
                            2,
                        ),
                        reasoning_chain=reasoning,
                        timestamp=datetime.utcnow(),
                    )

                    await self._repository.save(pred)
                    predictions.append(pred)

                    if self._broadcast_callback:
                        await self._broadcast_callback(
                            {
                                "type": "new_prediction",
                                "data": {
                                    "id": pred.id,
                                    "ticker": pred.ticker,
                                    "horizon": pred.horizon_days,
                                    "expected_move": pred.distribution.expected_move_pct,
                                    "bullish": pred.distribution.bullish_probability,
                                    "bearish": pred.distribution.bearish_probability,
                                    "neutral": pred.distribution.neutral_probability,
                                    "confidence": pred.confidence,
                                    "timestamp": pred.timestamp.isoformat(),
                                },
                            }
                        )
            except Exception as e:
                logger.error("Failed to generate prediction", ticker=impact.ticker, error=str(e))

        return predictions
