"""Predictions router.

Routes requests for ticker forecasts and portfolio-wide predictions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_portfolio_service, get_prediction_repository
from app.domain.interfaces.repository import IPredictionRepository
from app.services.portfolio_service import PortfolioService

router = APIRouter()


@router.get("/portfolio")
async def get_portfolio_predictions(
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    pred_repo: IPredictionRepository = Depends(get_prediction_repository),
):
    port = await portfolio_service.get_portfolio()
    results = {}
    for h in port.holdings:
        preds = await pred_repo.get_for_ticker(h.ticker, limit=1)
        if preds:
            results[h.ticker] = preds[0]
    return results


@router.get("/{ticker}")
async def get_ticker_predictions(
    ticker: str,
    pred_repo: IPredictionRepository = Depends(get_prediction_repository),
):
    return await pred_repo.get_for_ticker(ticker.upper(), limit=5)
