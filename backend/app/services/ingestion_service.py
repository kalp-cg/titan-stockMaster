"""Ingestion orchestrator service.

Coordinates raw article fetching, deduplication, NLP parsing, and live market price updates.
"""

from __future__ import annotations

from typing import Any, Callable

from app.config import get_settings
from app.domain.interfaces.repository import IEventRepository
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


class IngestionService:
    """Orchestrates data collection from market sources and news feeds."""

    def __init__(
        self,
        news_sources: list[Any],
        market_data_provider: Any,
        event_repository: IEventRepository,
        event_service: Any,
        broadcast_callback: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self._news_sources = news_sources
        self._market_data_provider = market_data_provider
        self._event_repository = event_repository
        self._event_service = event_service
        self._broadcast_callback = broadcast_callback

    @timed
    async def ingest_news(self) -> None:
        logger.info("Starting news ingestion cycle")
        new_events_count = 0

        for source in self._news_sources:
            try:
                logger.debug("Ingesting from source", source=source.source_name)
                articles = await source.fetch_articles()
                for article in articles:
                    exists = await self._event_repository.exists_by_hash(article.content_hash)
                    if exists:
                        continue

                    event = await self._event_service.process_article(article, source.reliability_score)
                    if not event:
                        continue
                    new_events_count += 1

                    if self._broadcast_callback:
                        await self._broadcast_callback(
                            {
                                "type": "new_event",
                                "data": {
                                    "id": event.id,
                                    "title": event.title,
                                    "summary": event.summary,
                                    "category": event.category.value,
                                    "severity": event.severity,
                                    "timestamp": event.timestamp.isoformat(),
                                },
                            }
                        )
            except Exception as e:
                logger.error("Failed to ingest news from source", source=source.source_name, error=str(e))

        logger.info("Completed news ingestion cycle", new_events=new_events_count)

    @timed
    async def refresh_market_prices(self, tickers: list[str] | None = None) -> None:
        if tickers is None:
            settings = get_settings()
            tickers = settings.MARKET_TICKERS
        try:
            logger.debug("Refreshing market prices", count=len(tickers))
            prices = await self._market_data_provider.get_prices(tickers)
            logger.info("Successfully refreshed market prices", count=len(prices))
            
            # Broadcast price update via WebSocket
            from app.api.websocket import broadcast_price_update
            await broadcast_price_update(prices)
        except Exception as e:
            logger.error("Failed to refresh market prices", error=str(e))
