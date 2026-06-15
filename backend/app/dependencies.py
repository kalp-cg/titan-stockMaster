"""Dependency injection container.

Sets up FastAPI dependencies including DB sessions, repositories, ML models, and services.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.infrastructure.database.engine import get_session_factory
from app.infrastructure.database.repositories import (
    EventRepository,
    HoldingRepository,
    IPORepository,
    LeadRepository,
    PredictionRepository,
    RiskAlertRepository,
    StakeholderRepository,
    UserRepository,
)
from app.infrastructure.ingestion.nse_stakeholder_provider import NSEStakeholderDataProvider
from app.infrastructure.ingestion.yfinance_provider import YFinanceDataProvider
from app.infrastructure.ingestion.rss_source import RSSNewsSource
from app.infrastructure.graph.memory_graph import NetworkXKnowledgeGraph
from app.infrastructure.graph.graph_seed import seed_knowledge_graph
from app.infrastructure.vector.numpy_similarity import NumPySimilarityEngine
from app.infrastructure.ml.finbert_classifier import FinBERTEventClassifier
from app.infrastructure.ml.spacy_extractor import SpacyEntityExtractor
from app.infrastructure.ml.sentence_embedder import SentenceEmbedder

from app.services.event_service import EventService
from app.services.impact_service import ImpactService
from app.services.lead_service import LeadService
from app.services.prediction_service import PredictionService
from app.services.portfolio_service import PortfolioService
from app.services.opportunity_service import OpportunityService
from app.services.ipo_service import IPOService
from app.services.risk_service import RiskService
from app.services.stakeholder_service import StakeholderService
from app.services.explanation_service import ExplanationService
from app.services.learning_service import LearningService
from app.services.ingestion_service import IngestionService

# Global Singletons
_graph = NetworkXKnowledgeGraph()
seed_knowledge_graph(_graph)

_similarity_engine = NumPySimilarityEngine()
_market_provider = YFinanceDataProvider()
_stakeholder_provider = NSEStakeholderDataProvider()
_scheduler = AsyncIOScheduler()

_settings = get_settings()
_news_sources = [
    RSSNewsSource(name="Global Financial News", feed_urls=_settings.NEWS_RSS_FEEDS)
]


# Database session dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Repositories
def get_event_repository(session: AsyncSession = Depends(get_db)) -> EventRepository:
    return EventRepository(session)


def get_prediction_repository(session: AsyncSession = Depends(get_db)) -> PredictionRepository:
    return PredictionRepository(session)


def get_holding_repository(session: AsyncSession = Depends(get_db)) -> HoldingRepository:
    return HoldingRepository(session)


def get_ipo_repository(session: AsyncSession = Depends(get_db)) -> IPORepository:
    return IPORepository(session)


def get_risk_repository(session: AsyncSession = Depends(get_db)) -> RiskAlertRepository:
    return RiskAlertRepository(session)


def get_stakeholder_repository(session: AsyncSession = Depends(get_db)) -> StakeholderRepository:
    return StakeholderRepository(session)


def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)


# Security and current user resolution
from app.services.auth_service import verify_access_token
from app.infrastructure.database.tables import UserTable

security_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserTable:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = verify_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id = payload["sub"]
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return user


# ML/NLP singletons
def get_classifier() -> FinBERTEventClassifier:
    return FinBERTEventClassifier.get_instance()


def get_extractor() -> SpacyEntityExtractor:
    return SpacyEntityExtractor.get_instance()


def get_embedder() -> SentenceEmbedder:
    return SentenceEmbedder.get_instance()


# Services
def get_stakeholder_service(
    repo: StakeholderRepository = Depends(get_stakeholder_repository),
) -> StakeholderService:
    return StakeholderService(repo, _stakeholder_provider, _market_provider)


def get_prediction_service(
    repo: PredictionRepository = Depends(get_prediction_repository),
    stakeholder_service: StakeholderService = Depends(get_stakeholder_service),
) -> PredictionService:
    from app.api.websocket import broadcast_message
    return PredictionService(repo, _similarity_engine, stakeholder_service, broadcast_message)


def get_impact_service(
    prediction_service: PredictionService = Depends(get_prediction_service),
) -> ImpactService:
    return ImpactService(_graph, prediction_service)


def get_lead_repository(session: AsyncSession = Depends(get_db)) -> LeadRepository:
    return LeadRepository(session)


def get_lead_service(
    lead_repo: LeadRepository = Depends(get_lead_repository),
    event_repo: EventRepository = Depends(get_event_repository),
    stakeholder_service: StakeholderService = Depends(get_stakeholder_service),
) -> LeadService:
    from app.api.websocket import broadcast_message
    return LeadService(lead_repo, _graph, event_repo, stakeholder_service, broadcast_message)


def get_portfolio_service(
    holding_repo: HoldingRepository = Depends(get_holding_repository),
    event_repo: EventRepository = Depends(get_event_repository),
    impact_service: ImpactService = Depends(get_impact_service),
) -> PortfolioService:
    return PortfolioService(holding_repo, event_repo, _market_provider, impact_service, _graph)


def get_event_service(
    repo: EventRepository = Depends(get_event_repository),
    classifier: FinBERTEventClassifier = Depends(get_classifier),
    extractor: SpacyEntityExtractor = Depends(get_extractor),
    embedder: SentenceEmbedder = Depends(get_embedder),
    impact_service: ImpactService = Depends(get_impact_service),
    lead_service: LeadService = Depends(get_lead_service),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
) -> EventService:
    return EventService(classifier, extractor, embedder, _similarity_engine, repo, impact_service, lead_service, portfolio_service)


def get_ingestion_service(
    event_repo: EventRepository = Depends(get_event_repository),
    event_service: EventService = Depends(get_event_service),
) -> IngestionService:
    from app.api.websocket import broadcast_message
    return IngestionService(
        _news_sources,
        _market_provider,
        event_repo,
        event_service,
        broadcast_message,
    )



def get_opportunity_service(
    event_repo: EventRepository = Depends(get_event_repository),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
) -> OpportunityService:
    return OpportunityService(_graph, event_repo, portfolio_service)


def get_ipo_service(
    ipo_repo: IPORepository = Depends(get_ipo_repository),
) -> IPOService:
    return IPOService(ipo_repo)


def get_risk_service(
    risk_repo: RiskAlertRepository = Depends(get_risk_repository),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    stakeholder_service: StakeholderService = Depends(get_stakeholder_service),
) -> RiskService:
    return RiskService(risk_repo, portfolio_service, stakeholder_service, _market_provider)


def get_explanation_service(
    pred_repo: PredictionRepository = Depends(get_prediction_repository),
) -> ExplanationService:
    return ExplanationService(pred_repo)


def get_learning_service(
    pred_repo: PredictionRepository = Depends(get_prediction_repository),
) -> LearningService:
    return LearningService(pred_repo, _market_provider)


# ------------------------------------------------------------------ #
# New Intelligence Layer Services                                    #
# ------------------------------------------------------------------ #

from app.services.smart_money_service import SmartMoneyService
from app.services.memory_engine import MemoryEngine
from app.services.attribution_service import AttributionService

_memory_engine = MemoryEngine(SentenceEmbedder.get_instance(), _similarity_engine)


def get_memory_engine() -> MemoryEngine:
    return _memory_engine


def get_smart_money_service(
    holding_repo: HoldingRepository = Depends(get_holding_repository),
    stakeholder_repo: StakeholderRepository = Depends(get_stakeholder_repository),
) -> SmartMoneyService:
    return SmartMoneyService(holding_repo, stakeholder_repo)


def get_attribution_service(
    event_repo: EventRepository = Depends(get_event_repository),
) -> AttributionService:
    return AttributionService(_market_provider, event_repo)


from app.services.causal_chain_service import CausalChainService

_causal_chain_service = CausalChainService(_graph)


def get_causal_chain_service() -> CausalChainService:
    return _causal_chain_service


