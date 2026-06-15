"""IPOs router.

Exposes endpoints for querying IPO lists and dynamic attractiveness ratings.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_ipo_service
from app.services.ipo_service import IPOService

router = APIRouter()


@router.get("")
async def get_ipos(
    service: IPOService = Depends(get_ipo_service),
):
    return await service.get_all_ipos()
