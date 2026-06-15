"""Explanation builder service.

Retrieves and details step-by-step reasoning explanations for predictions.
"""

from __future__ import annotations

from app.domain.interfaces.repository import IPredictionRepository
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ExplanationService:
    """Explains predictions with human-readable causal chains."""

    def __init__(self, prediction_repo: IPredictionRepository) -> None:
        self._prediction_repo = prediction_repo

    async def explain_prediction(self, prediction_id: str) -> list[str]:
        pred = await self._prediction_repo.get_by_id(prediction_id)
        if not pred:
            return ["Prediction details not found."]

        return pred.reasoning_chain
