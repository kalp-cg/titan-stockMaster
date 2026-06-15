"""Risk alerts router.

Exposes endpoints for fetching corporate risk radar alerts.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_risk_service
from app.services.risk_service import RiskService

router = APIRouter()


@router.get("/alerts")
async def get_alerts(
    service: RiskService = Depends(get_risk_service),
):
    return await service.get_recent_alerts()
