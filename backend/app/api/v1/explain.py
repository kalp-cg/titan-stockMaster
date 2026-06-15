"""Explanation router.

Exposes endpoints for getting human-readable causal explanation chains.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_explanation_service
from app.services.explanation_service import ExplanationService

router = APIRouter()


@router.get("/{prediction_id}")
async def explain_prediction(
    prediction_id: str,
    service: ExplanationService = Depends(get_explanation_service),
):
    return await service.explain_prediction(prediction_id)
