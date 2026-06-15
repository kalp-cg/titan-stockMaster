"""Portfolio router.

Exposes endpoints for portfolio management, holdings updates, and exposure analyses.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_portfolio_service, get_attribution_service, get_current_user
from app.services.portfolio_service import PortfolioService
from app.infrastructure.database.tables import UserTable

router = APIRouter()


class AddHoldingRequest(BaseModel):
    ticker: str
    quantity: float
    avg_buy_price: float
    thesis: str = ""


@router.get("")
async def get_portfolio(
    service: PortfolioService = Depends(get_portfolio_service),
    current_user: UserTable = Depends(get_current_user),
):
    return await service.get_portfolio(user_id=current_user.id)


@router.post("/holdings")
async def add_holding(
    req: AddHoldingRequest,
    service: PortfolioService = Depends(get_portfolio_service),
    current_user: UserTable = Depends(get_current_user),
):
    try:
        return await service.add_holding(
            user_id=current_user.id,
            ticker=req.ticker,
            quantity=req.quantity,
            avg_buy_price=req.avg_buy_price,
            thesis=req.thesis,
        )
    except Exception as e:
        from app.utils.logging import get_logger
        get_logger(__name__).error("Failed to add holding", error=str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/holdings/{ticker}")
async def remove_holding(
    ticker: str,
    service: PortfolioService = Depends(get_portfolio_service),
    current_user: UserTable = Depends(get_current_user),
):
    deleted = await service.remove_holding(user_id=current_user.id, ticker=ticker)
    if not deleted:
        raise HTTPException(status_code=404, detail="Holding not found")
    return {"status": "success", "message": f"Deleted holding {ticker}"}


@router.get("/exposure")
async def get_portfolio_exposure(
    service: PortfolioService = Depends(get_portfolio_service),
    current_user: UserTable = Depends(get_current_user),
):
    return await service.get_exposure(user_id=current_user.id)


@router.get("/holdings/{ticker}/attribution")
async def get_holding_attribution(
    ticker: str,
    move_pct: float = 0.0,
    move_date: str | None = None,
    sector: str | None = None,
    volume_ratio: float = 1.0,
    service = Depends(get_attribution_service),
):
    try:
        attribution = await service.explain_move(
            ticker=ticker.upper(),
            move_pct=move_pct,
            move_date=move_date,
            sector=sector,
            volume_ratio=volume_ratio,
        )
        return {
            "ticker": attribution.ticker,
            "move_pct": attribution.move_pct,
            "move_date": attribution.move_date,
            "top_factor": attribution.top_factor,
            "explanation_summary": attribution.explanation_summary,
            "confidence": attribution.confidence,
            "volume_ratio": attribution.volume_ratio,
            "factors": [
                {
                    "name": f.name,
                    "probability": f.probability,
                    "direction": f.direction,
                    "evidence": f.evidence,
                }
                for f in attribution.factors
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

