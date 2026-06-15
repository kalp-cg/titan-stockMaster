"""Market data router.

Provides endpoints for live price snapshots, indices values, and OHLC history.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.dependencies import _market_provider

router = APIRouter()


@router.get("/search")
async def search_tickers(
    q: str = Query(default=""),
):
    return await _market_provider.search_tickers(q)


@router.get("/prices")
async def get_prices(
    tickers: str = Query(description="Comma-separated ticker list"),
):
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        return {}
    return await _market_provider.get_prices(ticker_list)


@router.get("/indices")
async def get_indices():
    indices = [
        "^NSEI", "^BSESN", "^NSEBANK", 
        "^GSPC", "^IXIC", "^FTSE", "^N225", "^GDAXI", "^HSI",
        "GC=F", "CL=F"
    ]
    return await _market_provider.get_prices(indices)


@router.get("/history/{ticker}")
async def get_ticker_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
):
    return await _market_provider.get_history(
        ticker.upper(), period=period, interval=interval
    )
