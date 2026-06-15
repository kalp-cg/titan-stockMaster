"""
Causal Chain Engine — Multi-hop propagation tracing.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from app.domain.interfaces.knowledge_graph import IKnowledgeGraph
from app.domain.models.causal_chain import ChainNode, CausalChainResult
from app.domain.models.event import MarketEvent, SentimentLabel
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


class CausalChainService:
    """
    Computes multi-hop downstream causal chains for a macro trigger or market event.
    Algorithm:
      Multi-hop traversal using BFS with edge-weight decay and step attenuation.
      Effect = Hop N * edge_weight * 0.65
      Max depth = 4 hops.
    """

    def __init__(self, knowledge_graph: IKnowledgeGraph) -> None:
        self._graph = knowledge_graph

    @timed
    def trace_node(self, trigger_node_id: str, base_impact: float) -> CausalChainResult | None:
        """
        Trace propagation starting from trigger_node_id.
        """
        if not hasattr(self._graph, "_graph"):
            logger.warning("CausalChainService: knowledge graph is missing underlying networkx object")
            return None

        nx_graph = self._graph._graph
        if not nx_graph.has_node(trigger_node_id):
            return None

        trigger_label = nx_graph.nodes[trigger_node_id].get("label", trigger_node_id)
        
        # BFS Queue holds: (node_id, current_impact, depth, path)
        queue = deque([(trigger_node_id, base_impact, 0, [trigger_label])])
        visited = {trigger_node_id: base_impact}
        chain_nodes: list[ChainNode] = []

        while queue:
            node_id, impact, depth, path = queue.popleft()

            # Skip trigger node itself for the returned chain
            if node_id != trigger_node_id:
                node_data = nx_graph.nodes[node_id]
                node_label = node_data.get("label", node_id)
                node_type = node_data.get("node_type", "unknown")
                direction = 1 if impact >= 0 else -1

                # Format human-readable link reasoning
                reason = ""
                if len(path) > 1:
                    reason = f"Propagated shock: {' ➔ '.join(path[-2:])}"
                else:
                    reason = f"Directly affected by {trigger_label}"

                chain_nodes.append(
                    ChainNode(
                        node_id=node_id,
                        label=node_label,
                        node_type=node_type,
                        depth=depth,
                        impact=round(impact, 3),
                        direction=direction,
                        reason=reason,
                        path=list(path)
                    )
                )

            # Traversal limit — do not expand beyond depth 4 or when impact is negligible
            if depth >= 4 or abs(impact) < 0.05:
                continue

            # Visit adjacent nodes (successors in Directed Graph)
            for nbr in nx_graph.successors(node_id):
                edge_data = nx_graph.get_edge_data(node_id, nbr)
                edge_weight = edge_data.get("weight", 1.0)
                rel = edge_data.get("relationship", "affects")

                # Attenuate impact score
                next_impact = impact * edge_weight * 0.65

                if abs(next_impact) < 0.05:
                    continue

                nbr_label = nx_graph.nodes[nbr].get("label", nbr)
                # Form edge notation: Source --[relationship]-->
                edge_desc = f"{nx_graph.nodes[node_id].get('label')} --[{rel.replace('_', ' ')}]-->"
                new_path = path[:-1] + [edge_desc] + [nbr_label]

                if nbr not in visited or abs(next_impact) > abs(visited[nbr]):
                    visited[nbr] = next_impact
                    queue.append((nbr, next_impact, depth + 1, new_path))

        # Sort by impact magnitude descending
        chain_nodes.sort(key=lambda x: abs(x.impact), reverse=True)

        return CausalChainResult(
            trigger_node=trigger_node_id,
            trigger_label=trigger_label,
            base_impact=round(base_impact, 3),
            chain=chain_nodes
        )

    @timed
    def trace_event(self, event: MarketEvent) -> list[CausalChainResult]:
        """
        Matches event to starting graph nodes and traces causal chains for each.
        """
        # Determine base impact score
        base_score = event.severity
        if event.sentiment == SentimentLabel.NEGATIVE:
            base_score = -event.severity
        elif event.sentiment == SentimentLabel.NEUTRAL:
            base_score = base_score * 0.2

        start_nodes: list[tuple[str, float]] = []

        # 1. Match NLP entities
        for ent in event.entities:
            node_id = ent.normalized_name.lower()
            if self._graph.get_node(node_id):
                start_nodes.append((node_id, ent.confidence))

        # 2. Match Categories
        cat_node = event.category.value.lower()
        if self._graph.get_node(cat_node):
            start_nodes.append((cat_node, 0.5))

        # 3. Match keyword fallbacks if no starting nodes matched
        if not start_nodes and hasattr(self._graph, "_graph"):
            nx_graph = self._graph._graph
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
                "india": ["india", "indian", "rose", "nse", "bse", "nifty", "sensex"],
                "donald_trump": ["trump", "donald trump", "donald_trump"],
                "narendra_modi": ["modi", "narendra modi", "narendra_modi"],
                "jerome_powell": ["powell", "jerome powell", "jerome_powell", "fed chair"],
                "elon_musk": ["musk", "elon musk", "elon_musk"],
            }
            
            text_to_check = (event.title + " " + event.raw_text).lower()
            for node_id, keywords in keyword_mappings.items():
                for kw in keywords:
                    if kw in text_to_check:
                        if nx_graph.has_node(node_id):
                            conf = 0.8 if kw in event.title.lower() else 0.5
                            start_nodes.append((node_id, conf))
                            break

        results: list[CausalChainResult] = []
        for node_id, conf in start_nodes:
            adj_score = base_score * conf
            res = self.trace_node(node_id, adj_score)
            if res:
                results.append(res)
        return results
