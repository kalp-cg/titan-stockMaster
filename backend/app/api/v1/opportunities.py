"""Opportunities router.

Exposes endpoints for listing 1st, 2nd, and 3rd order market opportunities.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_opportunity_service
from app.services.opportunity_service import OpportunityService

router = APIRouter()


@router.get("")
async def get_opportunities(
    service: OpportunityService = Depends(get_opportunity_service),
):
    return await service.scan_opportunities()
