"""Opportunity discovery service.

Traverses the economic graph from recent triggering events to find high-conviction
1st, 2nd, and 3rd order long/short opportunities, filtering out current holdings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.domain.interfaces.knowledge_graph import IKnowledgeGraph
from app.domain.interfaces.repository import IEventRepository
from app.domain.models.opportunity import Opportunity, OpportunityDirection, OpportunityOrder
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


class OpportunityService:
    """Scans the knowledge graph for 1st, 2nd, and 3rd order opportunities."""

    def __init__(
        self,
        knowledge_graph: IKnowledgeGraph,
        event_repository: IEventRepository,
        portfolio_service: Any = None,
    ) -> None:
        self._graph = knowledge_graph
        self._event_repo = event_repository
        self._portfolio_service = portfolio_service

    @timed
    async def scan_opportunities(self, *, limit: int = 15) -> list[Opportunity]:
        logger.info("Scanning for market opportunities")

        events = await self._event_repo.get_recent(limit=5)
        opportunities: list[Opportunity] = []

        portfolio_tickers = set()
        if self._portfolio_service:
            port = await self._portfolio_service.get_portfolio()
            portfolio_tickers = set(port.tickers)

        for event in events:
            start_nodes = []
            for ent in event.entities:
                node_id = ent.normalized_name.lower()
                if self._graph.get_node(node_id):
                    start_nodes.append((node_id, ent.confidence))

            cat_node = event.category.value.lower()
            if self._graph.get_node(cat_node):
                start_nodes.append((cat_node, 0.5))

            if not start_nodes:
                continue

            for start_id, conf in start_nodes:
                propagation = self._graph.propagate_impact(start_id, 1.0, max_depth=3)

                for comp in propagation.affected_companies:
                    if comp.ticker in portfolio_tickers:
                        continue

                    path_len = len(comp.reasoning_path)
                    if path_len <= 1:
                        order = OpportunityOrder.FIRST_ORDER
                    elif path_len == 2:
                        order = OpportunityOrder.SECOND_ORDER
                    else:
                        order = OpportunityOrder.THIRD_ORDER

                    is_bullish = comp.direction > 0
                    if event.sentiment == "negative":
                        is_bullish = not is_bullish

                    direction = (
                        OpportunityDirection.LONG if is_bullish else OpportunityDirection.SHORT
                    )

                    reasoning = [
                        f"Triggered by event '{event.title}'.",
                        f"Causal chain: {' -> '.join(comp.reasoning_path)}.",
                    ]

                    opp = Opportunity(
                        ticker=comp.ticker,
                        company_name=comp.company_name,
                        sector="Technology" if "TCS" in comp.ticker or "INFY" in comp.ticker else "Financial Services" if "BANK" in comp.ticker else "Conglomerate",
                        trigger_event_id=event.id,
                        trigger_event_title=event.title,
                        order=order,
                        direction=direction,
                        reasoning=reasoning,
                        graph_path=comp.reasoning_path,
                        confidence=round(comp.confidence * conf, 2),
                        expected_impact_pct=round(comp.magnitude * 5.0, 2),
                        id=str(uuid4()),
                        timestamp=datetime.utcnow(),
                    )
                    opportunities.append(opp)

        order_keys = {
            OpportunityOrder.THIRD_ORDER: 3,
            OpportunityOrder.SECOND_ORDER: 2,
            OpportunityOrder.FIRST_ORDER: 1,
        }

        opportunities = sorted(
            opportunities,
            key=lambda x: (order_keys[x.order], x.confidence),
            reverse=True,
        )

        return opportunities[:limit]
