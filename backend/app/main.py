"""Main FastAPI application entry point.

Sets up server startup lifecycle events, CORS policies, routing tables,
and logs application state changes.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.infrastructure.database.engine import create_all_tables, dispose_engine, get_session_factory
from app.infrastructure.database.repositories import (
    EventRepository,
    HoldingRepository,
    IPORepository,
    LeadRepository,
    PredictionRepository,
    RiskAlertRepository,
    StakeholderRepository,
)
from app.infrastructure.ingestion.scheduler import IngestionScheduler
from app.dependencies import (
    _scheduler,
    _news_sources,
    _market_provider,
    _stakeholder_provider,
    _similarity_engine,
    _graph,
)

from app.services.event_service import EventService
from app.services.impact_service import ImpactService
from app.services.lead_service import LeadService
from app.services.prediction_service import PredictionService
from app.services.stakeholder_service import StakeholderService
from app.services.ingestion_service import IngestionService

from app.api import websocket
from app.api.v1 import (
    auth,
    events,
    market,
    portfolio,
    predictions,
    opportunities,
    ipos,
    leads,
    risk,
    stakeholders,
    explain,
    search,
    smart_money,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")

    # 1. Initialize tables
    await create_all_tables()

    # 1.2. Run database schema migrations for auth scoping
    try:
        from app.infrastructure.database.db_migration import run_migration
        await run_migration()
    except Exception as e:
        logger.error("Failed to run database schema migrations on startup", error=str(e))

    # 1.5. Initialize MemoryEngine corpus
    try:
        from app.dependencies import get_memory_engine
        get_memory_engine().initialize()
    except Exception as e:
        logger.error("Failed to initialize MemoryEngine", error=str(e))

    # 2. Setup background tasks in scheduler
    session_factory = get_session_factory()
    async with session_factory() as session:
        event_repo = EventRepository(session)
        pred_repo = PredictionRepository(session)
        holding_repo = HoldingRepository(session)
        ipo_repo = IPORepository(session)
        risk_repo = RiskAlertRepository(session)
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
            lead_repo, _graph, event_repo, stakeholder_service
        )

        from app.dependencies import get_classifier, get_embedder, get_extractor

        event_service = EventService(
            event_classifier=get_classifier(),
            entity_extractor=get_extractor(),
            sentence_embedder=get_embedder(),
            similarity_engine=_similarity_engine,
            event_repository=event_repo,
            impact_service=impact_service,
            lead_service=lead_service,
        )
        ingestion_service = IngestionService(
            _news_sources,
            _market_provider,
            event_repo,
            event_service,
        )

        recent_events = await event_repo.get_recent(limit=1)
        if not recent_events:
            logger.info("Database empty, initiating startup ingestion and stakeholder seed")
            # Seed holdings with a few default Indian companies for immediate portfolio visibility
            await holding_repo.save(
                __import__("app.domain.models.portfolio", fromlist=["Holding"]).Holding(
                    ticker="RELIANCE.NS",
                    company_name="Reliance Industries",
                    quantity=50.0,
                    avg_buy_price=2450.0,
                )
            )
            await holding_repo.save(
                __import__("app.domain.models.portfolio", fromlist=["Holding"]).Holding(
                    ticker="TCS.NS",
                    company_name="Tata Consultancy Services",
                    quantity=20.0,
                    avg_buy_price=3300.0,
                )
            )
            await holding_repo.save(
                __import__("app.domain.models.portfolio", fromlist=["Holding"]).Holding(
                    ticker="INFY.NS",
                    company_name="Infosys",
                    quantity=35.0,
                    avg_buy_price=1500.0,
                )
            )
            await session.commit()

            # Ingest news & stakeholder patterns using fresh sessions
            from app.infrastructure.ingestion.scheduler import run_news_ingestion, run_stakeholder_refresh
            asyncio.create_task(run_news_ingestion())
            asyncio.create_task(run_stakeholder_refresh())

            # Seed mock articles for Key Voices & Speech Tracker
            import hashlib
            from datetime import datetime
            from app.domain.interfaces.news_source import RawArticle

            mock_articles = [
                RawArticle(
                    title="Trump Proposes New Tariffs on Global Hardware and Tech Equipment",
                    content="Donald Trump announced a new proposal for sweeping tariffs on imports of semiconductor chips and global hardware components. This tariff adjust is intended to boost domestic manufacturing, but analysts warn it will disrupt global technology supply chains and increase costs for major tech firms, while strengthening domestic energy and oil production companies.",
                    url="http://mocknews.com/trump-tariffs",
                    source_name="Financial Times",
                    published_at=datetime.utcnow(),
                    content_hash=hashlib.sha256(b"trump-tariffs").hexdigest()
                ),
                RawArticle(
                    title="PM Narendra Modi Announces Historic Capex Infrastructure Initiative",
                    content="Prime Minister Narendra Modi unveiled a massive capital expenditure package to accelerate infrastructure development across India. The program focuses heavily on upgrading transport networks, steel plants, cement manufacturing, and energy utilities, boosting local industries and job creation.",
                    url="http://mocknews.com/modi-capex",
                    source_name="Economic Times",
                    published_at=datetime.utcnow(),
                    content_hash=hashlib.sha256(b"modi-capex").hexdigest()
                ),
                RawArticle(
                    title="Fed Chair Jerome Powell Hints at Impending Rate Cuts as Inflation Moderates",
                    content="Federal Reserve Chair Jerome Powell indicated that the central bank is prepared to lower interest rates in the coming quarters. Powell noted that inflation is steadily moderating toward the target, which will relieve pressure on banking, finance, and consumer sectors globally.",
                    url="http://mocknews.com/powell-rates",
                    source_name="Wall Street Journal",
                    published_at=datetime.utcnow(),
                    content_hash=hashlib.sha256(b"powell-rates").hexdigest()
                ),
                RawArticle(
                    title="Elon Musk Unveils Vision for Autonomous EV Fleet Expansion",
                    content="Elon Musk shared details on Tesla's next-generation electric vehicles and global autonomous ride-hailing networks. Musk declared that this tech expansion will revolutionize the automobiles sector, driving immense demand for battery metals, copper, and advanced software systems.",
                    url="http://mocknews.com/musk-ev",
                    source_name="TechCrunch",
                    published_at=datetime.utcnow(),
                    content_hash=hashlib.sha256(b"musk-ev").hexdigest()
                )
            ]

            async def seed_articles():
                await asyncio.sleep(2.0)
                from app.infrastructure.database.engine import db_session
                from app.api.websocket import broadcast_message

                for article in mock_articles:
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

                            await event_service.process_article(article, 1.0)
                            logger.info(f"Seeded mock article successfully: {article.title}")
                    except Exception as e:
                        logger.error(f"Failed to seed mock article '{article.title}': {str(e)}")

            asyncio.create_task(seed_articles())

        scheduler_manager = IngestionScheduler(
            _scheduler
        )
        scheduler_manager.start()
        app.state.scheduler = scheduler_manager

    yield

    logger.info("Application shutting down...")
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
    await dispose_engine()


settings = get_settings()
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes registration
app.include_router(websocket.router)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(events.router, prefix="/api/v1/events", tags=["events"])
app.include_router(market.router, prefix="/api/v1/market", tags=["market"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["predictions"])
app.include_router(opportunities.router, prefix="/api/v1/opportunities", tags=["opportunities"])
app.include_router(ipos.router, prefix="/api/v1/ipos", tags=["ipos"])
app.include_router(leads.router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(risk.router, prefix="/api/v1/risk", tags=["risk"])
app.include_router(stakeholders.router, prefix="/api/v1/stakeholders", tags=["stakeholders"])
app.include_router(explain.router, prefix="/api/v1/explain", tags=["explain"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(smart_money.router, prefix="/api/v1/smart-money", tags=["smart_money"])


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
    }
