"""WebSocket route handler.

Broadcasts real-time events, predictions, and alerts to connected frontends.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

_active_connections: set[WebSocket] = set()
_lock = asyncio.Lock()


async def broadcast_message(message: dict) -> None:
    """Broadcast JSON messages to all active client connections."""
    async with _lock:
        if not _active_connections:
            return

        disconnected_clients = []
        for ws in _active_connections:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected_clients.append(ws)

        for ws in disconnected_clients:
            if ws in _active_connections:
                _active_connections.remove(ws)


async def broadcast_price_update(prices: dict) -> None:
    """Broadcast market price updates to all connected clients."""
    # Format each price value to match what the frontend expects
    formatted_prices = {}
    for ticker, p in prices.items():
        # p is a MarketPrice model or dict. Let's handle both or convert to dict
        if hasattr(p, "price"):
            formatted_prices[ticker] = {
                "price": p.price,
                "change_pct": p.change_pct,
                "change": p.change,
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "volume": p.volume,
                "timestamp": p.timestamp.isoformat() if hasattr(p.timestamp, "isoformat") else str(p.timestamp)
            }
        elif isinstance(p, dict):
            formatted_prices[ticker] = p
    await broadcast_message({
        "type": "price_update",
        "data": formatted_prices
    })


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    async with _lock:
        _active_connections.add(websocket)
    logger.info("New WebSocket connection accepted", count=len(_active_connections))

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        async with _lock:
            if websocket in _active_connections:
                _active_connections.remove(websocket)
        logger.info("WebSocket disconnected", count=len(_active_connections))
    except Exception as e:
        logger.error("WebSocket session error", error=str(e))
        async with _lock:
            if websocket in _active_connections:
                _active_connections.remove(websocket)
