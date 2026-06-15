"""Impact propagation service.

Matches events to starting graph nodes and traverses the economic network
to compute downstream company impacts.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.domain.interfaces.knowledge_graph import IKnowledgeGraph
from app.domain.models.company import CompanyImpact
from app.domain.models.event import MarketEvent, SentimentLabel
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


class ImpactService:
    """Orchestrates BFS economic propagation through the knowledge graph."""

    def __init__(
        self,
        knowledge_graph: IKnowledgeGraph,
        prediction_service: Any = None,
    ) -> None:
        self._graph = knowledge_graph
        self._prediction_service = prediction_service

    @timed
    async def process_event_impact(self, event: MarketEvent) -> list[CompanyImpact]:
        logger.info("Propagating impact for event", event_id=event.id, title=event.title)

        # 1. Determine base impact score
        base_score = event.severity
        if event.sentiment == SentimentLabel.NEGATIVE:
            base_score = -event.severity
        elif event.sentiment == SentimentLabel.NEUTRAL:
            base_score = base_score * 0.2

        # 2. Find starting nodes
        start_nodes: list[tuple[str, float]] = []

        for ent in event.entities:
            node_id = ent.normalized_name.lower()
            if self._graph.get_node(node_id):
                start_nodes.append((node_id, ent.confidence))

        cat_node = event.category.value.lower()
        if self._graph.get_node(cat_node):
            start_nodes.append((cat_node, 0.5))

        subcat_node = event.sub_category.value.lower()
        if self._graph.get_node(subcat_node):
            start_nodes.append((subcat_node, 0.6))

        if not start_nodes:
            keyword_mappings = {
                "crude_oil": ["oil", "crude", "petroleum", "wti", "brent"],
                "natural_gas": ["gas", "lng", "cng"],
                "coal": ["coal"],
                "gold": ["gold", "jewel"],
                "silver": ["silver"],
                "steel": ["steel", "iron"],
                "copper": ["copper"],
                "semiconductors": ["semiconductor", "chip", "chips", "processor", "processors", "electronics"],
                "api_ingredients": ["api", "ingredients", "active pharmaceutical"],
                "agricultural_products": ["agriculture", "crop", "wheat", "rice", "sugar"],
                "technology": ["technology", "tech", "software", "it services", "tcs", "infosys", "wipro"],
                "banking_finance": ["bank", "banking", "finance", "fii", "dii", "interest rate", "inflation", "rbi", "fed"],
                "energy_utilities": ["energy", "power", "utility", "coal", "solar", "renewable"],
                "consumer_fmcg": ["fmcg", "consumer", "unilever", "itc", "nestle"],
                "automobiles": ["auto", "car", "vehicle", "electric vehicle", "ev", "motors"],
                "metals_mining": ["metal", "mining", "steel", "aluminium", "copper", "iron"],
                "defense_aerospace": ["defense", "aerospace", "military", "hindustan aeronautics", "bel"],
                "aviation": ["aviation", "airline", "flight", "indigo"],
                "pharmaceuticals": ["pharma", "pharmaceutical", "drug", "medicine"],
                "infrastructure": ["infra", "infrastructure", "l&t", "construction"],
                "paints": ["paint", "asian paint", "berger"],
                "cement": ["cement", "ultratech"],
                "middle_east": ["iran", "middle east", "israel", "gaza", "yemen", "suez", "red sea", "persian"],
                "usa": ["usa", "us", "united states", "fed", "wall st", "nasdaq"],
                "china": ["china", "chinese", "beijing"],
                "india": ["india", "indian", "nse", "bse", "nifty", "sensex"],
                "donald_trump": ["trump", "donald trump", "donald_trump"],
                "narendra_modi": ["modi", "narendra modi", "narendra_modi"],
                "jerome_powell": ["powell", "jerome powell", "jerome_powell", "fed chair"],
                "elon_musk": ["musk", "elon musk", "elon_musk"],
            }
            
            text_to_check = (event.title + " " + event.raw_text).lower()
            for node_id, keywords in keyword_mappings.items():
                for kw in keywords:
                    if kw in text_to_check:
                        if self._graph.get_node(node_id):
                            conf = 0.8 if kw in event.title.lower() else 0.5
                            start_nodes.append((node_id, conf))
                            break

        if not start_nodes:
            logger.info("No starting nodes in graph matched this event", event_id=event.id)
            return []

        # 3. Propagate and merge
        merged_impacts: dict[str, CompanyImpact] = {}

        for node_id, conf in start_nodes:
            adj_score = base_score * conf
            propagation = self._graph.propagate_impact(node_id, adj_score, max_depth=3)

            for comp in propagation.affected_companies:
                ticker = comp.ticker
                if ticker in merged_impacts:
                    if comp.magnitude > merged_impacts[ticker].magnitude:
                        merged_impacts[ticker] = comp
                else:
                    merged_impacts[ticker] = comp

        impacts_list = list(merged_impacts.values())
        logger.info("Impact propagation complete", event_id=event.id, affected_companies=len(impacts_list))

        # 4. Trigger predictions
        if self._prediction_service and impacts_list:
            await self._prediction_service.generate_predictions(event, impacts_list)

        return impacts_list

    async def get_company_impacts(self, event_id: str) -> list[CompanyImpact]:
        return []
