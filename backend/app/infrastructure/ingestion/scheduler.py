"""Background tasks scheduler using APScheduler.

Coordinates polling jobs for news, market data, and SEBI/NSE stakeholder reports.
Each background execution is run in a dedicated, isolated database session.
"""

from __future__ import annotations

from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.utils.logging import get_logger
from app.infrastructure.database.engine import db_session
from app.infrastructure.database.repositories import (
    EventRepository,
    PredictionRepository,
    StakeholderRepository,
    HoldingRepository,
    LeadRepository,
)
from app.services.stakeholder_service import StakeholderService
from app.services.prediction_service import PredictionService
from app.services.impact_service import ImpactService
from app.services.event_service import EventService
from app.services.ingestion_service import IngestionService
from app.services.lead_service import LeadService

from app.dependencies import (
    _stakeholder_provider,
    _market_provider,
    _similarity_engine,
    _graph,
    _news_sources,
    get_classifier,
    get_embedder,
    get_extractor,
)
from app.api.websocket import broadcast_message

logger = get_logger(__name__)


async def run_news_ingestion() -> None:
    """Fetch RSS articles outside DB session, then save them in short-lived sessions."""
    logger.info("Starting news ingestion cycle")
    
    # 1. Fetch articles from all sources (network I/O) outside DB context
    articles_by_source = []
    for source in _news_sources:
        try:
            logger.debug("Fetching RSS articles", source=source.source_name)
            articles = await source.fetch_articles()
            articles_by_source.append((source, articles))
        except Exception as e:
            logger.error("Failed to fetch RSS feed", source=source.source_name, error=str(e))

    # 2. Open short-lived sessions to process and save new articles
    new_events_count = 0
    
    for source, articles in articles_by_source:
        for article in articles:
            try:
                async with db_session() as session:
                    event_repo = EventRepository(session)
                    exists = await event_repo.exists_by_hash(article.content_hash)
                    if exists:
                        continue

                    pred_repo = PredictionRepository(session)
                    stakeholder_repo = StakeholderRepository(session)

                    stakeholder_service = StakeholderService(
                        stakeholder_repo, _stakeholder_provider, _market_provider
                    )
                    prediction_service = PredictionService(
                        pred_repo, _similarity_engine, stakeholder_service
                    )
                    impact_service = ImpactService(_graph, prediction_service)

                    lead_repo = LeadRepository(session)
                    lead_service = LeadService(
                        lead_repo, _graph, event_repo, stakeholder_service, broadcast_message
                    )

                    event_service = EventService(
                        event_classifier=get_classifier(),
                        entity_extractor=get_extractor(),
                        sentence_embedder=get_embedder(),
                        similarity_engine=_similarity_engine,
                        event_repository=event_repo,
                        impact_service=impact_service,
                        lead_service=lead_service,
                    )
                    
                    event = await event_service.process_article(article, source.reliability_score)
                    if not event:
                        continue
                    new_events_count += 1
                    
                    await broadcast_message(
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
                logger.error("Failed to process news article", title=article.title, error=str(e))

    logger.info("Completed news ingestion cycle", new_events=new_events_count)


async def run_market_refresh() -> None:
    """Run market price refresh cycle."""
    async with db_session() as session:
        event_repo = EventRepository(session)
        holding_repo = HoldingRepository(session)
        
        # Dynamic lookup of user-added custom portfolio tickers
        try:
            holdings = await holding_repo.get_all()
            portfolio_tickers = [h.ticker for h in holdings]
        except Exception as e:
            logger.error("Failed to fetch custom portfolio tickers for market refresh", error=str(e))
            portfolio_tickers = []

        settings = get_settings()
        # Merge and deduplicate default and custom tickers
        all_tickers = list(dict.fromkeys(settings.MARKET_TICKERS + portfolio_tickers))

        ingestion_service = IngestionService(
            _news_sources,
            _market_provider,
            event_repo,
            None,
            broadcast_message,
        )
        await ingestion_service.refresh_market_prices(all_tickers)


async def run_stakeholder_refresh() -> None:
    """Fetch stakeholder filings outside DB session, then save them in short-lived sessions."""
    logger.info("Starting stakeholder data refresh cycle")
    settings = get_settings()

    # 1. Fetch institutional flows (network I/O) and save in a short session
    try:
        flows = await _stakeholder_provider.get_institutional_flows(days=5)
        async with db_session() as session:
            stakeholder_repo = StakeholderRepository(session)
            for f in flows:
                await stakeholder_repo.save_institutional_flow(f)
    except Exception as e:
        logger.error("Failed to refresh institutional flows", error=str(e))

    # 2. Iterate tickers: fetch outside session, then write inside a short session
    for ticker in settings.MARKET_TICKERS:
        if ticker.startswith("^") or ticker.startswith("GC=") or ticker.startswith("CL="):
            continue
        try:
            # Fetch details from API / provider (network I/O)
            history = await _stakeholder_provider.get_shareholding_history(ticker, quarters=4)
            deals = await _stakeholder_provider.get_bulk_deals(ticker, days=7)
            trades = await _stakeholder_provider.get_insider_trades(ticker, days=30)
            
            # Get company name from market provider outside session
            company_name = ticker
            if _market_provider:
                try:
                    info = await _market_provider.get_company_info(ticker)
                    company_name = info.name
                except Exception:
                    pass

            # Open short session to save to database
            async with db_session() as session:
                stakeholder_repo = StakeholderRepository(session)
                stakeholder_service = StakeholderService(
                    stakeholder_repo, _stakeholder_provider, _market_provider
                )
                
                for pattern in history:
                    await stakeholder_repo.save_shareholding(pattern)
                for d in deals:
                    await stakeholder_repo.save_bulk_deal(d)
                for t in trades:
                    await stakeholder_repo.save_insider_trade(t)
                
                await stakeholder_service.compute_smart_money_signal(ticker, company_name=company_name)

        except Exception as e:
            logger.error("Failed to refresh stakeholder details", ticker=ticker, error=str(e))

    logger.info("Stakeholder data refresh cycle complete")


class IngestionScheduler:
    """Schedules background tasks for market intelligence ingestion."""

    def __init__(
        self,
        scheduler: AsyncIOScheduler,
        ingestion_service: Any = None,
        stakeholder_service: Any = None,
    ) -> None:
        self._scheduler = scheduler

    def start(self) -> None:
        settings = get_settings()

        # Job 1: Ingest news feeds
        self._scheduler.add_job(
            run_news_ingestion,
            "interval",
            seconds=settings.INGESTION_INTERVAL_SECONDS,
            id="ingest_news",
            replace_existing=True,
        )

        # Job 2: Refresh live market prices
        self._scheduler.add_job(
            run_market_refresh,
            "interval",
            seconds=settings.MARKET_REFRESH_INTERVAL_SECONDS,
            id="refresh_market_prices",
            replace_existing=True,
        )

        # Job 3: Refresh stakeholder filings
        self._scheduler.add_job(
            run_stakeholder_refresh,
            "interval",
            seconds=settings.STAKEHOLDER_REFRESH_INTERVAL_SECONDS,
            id="refresh_stakeholders",
            replace_existing=True,
        )

        # Job 4: Cleanup expired leads
        self._scheduler.add_job(
            run_lead_cleanup,
            "interval",
            seconds=1800,  # every 30 minutes
            id="cleanup_leads",
            replace_existing=True,
        )

        self._scheduler.start()
        logger.info("Ingestion scheduler started successfully")

    def shutdown(self) -> None:
        self._scheduler.shutdown()
        logger.info("Ingestion scheduler shut down successfully")


async def run_lead_cleanup() -> None:
    """Remove expired leads from the database."""
    try:
        async with db_session() as session:
            lead_repo = LeadRepository(session)
            lead_service = LeadService(lead_repo, None, None)
            count = await lead_service.cleanup_expired()
            if count > 0:
                logger.info("Lead cleanup completed", expired_count=count)
    except Exception as e:
        logger.error("Failed to cleanup expired leads", error=str(e))
