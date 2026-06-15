"""Smart Money API router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_smart_money_service, get_portfolio_service
from app.services.smart_money_service import SmartMoneyService
from app.services.portfolio_service import PortfolioService

router = APIRouter()


@router.get("/portfolio")
async def get_portfolio_smart_money(
    service: SmartMoneyService = Depends(get_smart_money_service),
):
    """Return smart money scores for all portfolio holdings."""
    try:
        scores = await service.get_portfolio_scores()
        return [
            {
                "ticker": s.ticker,
                "company_name": s.company_name,
                "score": s.score,
                "label": s.label,
                "bulk_deal_net_qty": s.bulk_deal_net_qty,
                "fii_net_3day_cr": s.fii_net_3day_cr,
                "insider_direction": s.insider_direction,
                "evidence": [
                    {
                        "source": e.source,
                        "description": e.description,
                        "direction": e.direction,
                        "strength": e.strength,
                        "date": e.date,
                    }
                    for e in s.evidence
                ],
                "computed_at": s.computed_at.isoformat(),
            }
            for s in scores
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticker/{ticker}")
async def get_ticker_smart_money(
    ticker: str,
    service: SmartMoneyService = Depends(get_smart_money_service),
):
    """Return smart money score for a single ticker."""
    try:
        score = await service.get_score(ticker.upper())
        return {
            "ticker": score.ticker,
            "company_name": score.company_name,
            "score": score.score,
            "label": score.label,
            "bulk_deal_net_qty": score.bulk_deal_net_qty,
            "fii_net_3day_cr": score.fii_net_3day_cr,
            "insider_direction": score.insider_direction,
            "evidence": [
                {
                    "source": e.source,
                    "description": e.description,
                    "direction": e.direction,
                    "strength": e.strength,
                    "date": e.date,
                }
                for e in score.evidence
            ],
            "computed_at": score.computed_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_smart_money_data(
    service: SmartMoneyService = Depends(get_smart_money_service),
):
    """Manually trigger a refresh of bulk deal and FII/DII data from NSE."""
    try:
        await service.refresh_market_data()
        return {"status": "ok", "message": "Smart money data refreshed from NSE"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
