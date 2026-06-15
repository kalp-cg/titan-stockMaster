"""Event service orchestration.

Coordinates the NLP pipeline (classification, NER, and embedding) and saves the processed event.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.domain.interfaces.event_classifier import IEventClassifier, IEntityExtractor, ISentenceEmbedder
from app.domain.interfaces.repository import IEventRepository
from app.domain.interfaces.similarity_engine import ISimilarityEngine
from app.domain.interfaces.news_source import RawArticle
from app.domain.models.event import MarketEvent
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


class EventService:
    """Orchestrates NLP pipeline: classification, entity extraction, embedding generation."""

    def __init__(
        self,
        event_classifier: IEventClassifier,
        entity_extractor: IEntityExtractor,
        sentence_embedder: ISentenceEmbedder,
        similarity_engine: ISimilarityEngine,
        event_repository: IEventRepository,
        impact_service: Any = None,
        lead_service: Any = None,
        portfolio_service: Any = None,
    ) -> None:
        self._classifier = event_classifier
        self._extractor = entity_extractor
        self._embedder = sentence_embedder
        self._similarity = similarity_engine
        self._repository = event_repository
        self._impact_service = impact_service
        self._lead_service = lead_service
        self._portfolio_service = portfolio_service

    @timed
    async def process_article(self, article: RawArticle, source_reliability: float) -> MarketEvent:
        logger.info("Processing raw article", title=article.title)

        # 1. Classification
        category, sub_category, sentiment, severity, confidence = self._classifier.classify(article.content)

        from app.domain.models.event import EventCategory
        if category == EventCategory.UNKNOWN:
            logger.info("Discarding non-business/unrelated news event", title=article.title)
            return None

        # 2. Entity extraction
        entities = self._extractor.extract(article.content)

        # 3. Generate embedding
        embedding = self._embedder.embed(article.content)

        # 4. Construct event
        event = MarketEvent(
            id=str(uuid4()),
            title=article.title,
            summary=article.content[:300] + "..." if len(article.content) > 300 else article.content,
            raw_text=article.content,
            source=article.source_name,
            url=article.url,
            category=category,
            sub_category=sub_category,
            sentiment=sentiment,
            severity=severity,
            confidence=confidence * source_reliability,
            affected_regions=[ent.normalized_name for ent in entities if ent.entity_type.value == "country"],
            affected_industries=[ent.normalized_name for ent in entities if ent.entity_type.value == "sector"],
            timestamp=article.published_at or datetime.utcnow(),
            entities=entities,
            embedding=embedding,
        )

        # Save to DB
        await self._repository.save(event)

        # Save to vector database (similarity engine)
        self._similarity.store_embedding(event.id, embedding, metadata={"title": event.title})

        logger.info("Saved event", event_id=event.id, category=event.category.value, severity=event.severity)

        # Trigger downstream impact propagation sequentially within transaction
        if self._impact_service:
            await self._impact_service.process_event_impact(event)

        # Trigger lead generation
        if self._lead_service:
            try:
                await self._lead_service.generate_leads(event)
            except Exception as e:
                logger.error("Lead generation failed", event_id=event.id, error=str(e))

        # Trigger real-time thesis drift evaluation for portfolio positions
        if self._portfolio_service:
            try:
                await self._portfolio_service.evaluate_thesis_drift(event)
            except Exception as e:
                logger.error("Thesis drift evaluation failed", event_id=event.id, error=str(e))

        return event

