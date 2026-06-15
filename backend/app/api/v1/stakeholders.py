"""Stakeholders router.

Exposes REST endpoints for SEBI/NSE stakeholder pattern tracking, deal registers, and institutional flows.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_stakeholder_service
from app.services.stakeholder_service import StakeholderService

router = APIRouter()


@router.get("/bulk-deals")
async def get_bulk_deals(
    ticker: str | None = None,
    days: int = Query(default=30, ge=1, le=90),
    service: StakeholderService = Depends(get_stakeholder_service),
):
    return await service.get_bulk_deals(
        ticker.upper() if ticker else None, days=days
    )


@router.get("/insider-trades")
async def get_insider_trades(
    ticker: str | None = None,
    days: int = Query(default=90, ge=1, le=180),
    service: StakeholderService = Depends(get_stakeholder_service),
):
    return await service.get_insider_trades(
        ticker.upper() if ticker else None, days=days
    )


@router.get("/institutional-flows")
async def get_institutional_flows(
    days: int = Query(default=30, ge=1, le=90),
    service: StakeholderService = Depends(get_stakeholder_service),
):
    return await service.get_institutional_flows(days=days)


@router.get("/{ticker}/shareholding")
async def get_shareholding(
    ticker: str,
    service: StakeholderService = Depends(get_stakeholder_service),
):
    return await service.get_shareholding_pattern(ticker.upper())


@router.get("/{ticker}/shareholding/history")
async def get_shareholding_history(
    ticker: str,
    quarters: int = Query(default=8, ge=1, le=12),
    service: StakeholderService = Depends(get_stakeholder_service),
):
    return await service.get_shareholding_history(ticker.upper(), quarters=quarters)


@router.get("/{ticker}/smart-money")
async def get_smart_money(
    ticker: str,
    service: StakeholderService = Depends(get_stakeholder_service),
):
    return await service.get_smart_money_signal(ticker.upper())
