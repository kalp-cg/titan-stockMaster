"""In-memory knowledge graph implementation using NetworkX.

Provides economic node management, shortest causal path finding, and
BFS-based impact score propagation across connected economic entities.
"""

from __future__ import annotations

from collections import deque
import networkx as nx

from app.domain.interfaces.knowledge_graph import GraphEdge, GraphNode, ImpactPropagation
from app.domain.models.company import CompanyImpact
from app.utils.logging import get_logger

logger = get_logger(__name__)


class NetworkXKnowledgeGraph:
    """In-memory representation of economic connections."""

    def __init__(self) -> None:
        self._graph = nx.DiGraph()

    def add_node(self, node: GraphNode) -> None:
        self._graph.add_node(
            node.node_id,
            node_type=node.node_type,
            label=node.label,
            metadata=node.metadata,
        )

    def remove_node(self, node_id: str) -> None:
        if self._graph.has_node(node_id):
            self._graph.remove_node(node_id)

    def add_edge(self, edge: GraphEdge) -> None:
        self._graph.add_edge(
            edge.source_id,
            edge.target_id,
            relationship=edge.relationship,
            weight=edge.weight,
        )

    def get_node(self, node_id: str) -> GraphNode | None:
        if not self._graph.has_node(node_id):
            return None
        data = self._graph.nodes[node_id]
        return GraphNode(
            node_id=node_id,
            node_type=data["node_type"],
            label=data["label"],
            metadata=data["metadata"],
        )

    def get_neighbors(
        self,
        node_id: str,
        *,
        relationship: str | None = None,
        max_depth: int = 1,
    ) -> list[GraphNode]:
        if not self._graph.has_node(node_id):
            return []

        visited = set()
        queue = deque([(node_id, 0)])
        neighbors = []

        while queue:
            curr_id, depth = queue.popleft()
            if curr_id != node_id:
                neighbors.append(self.get_node(curr_id))

            if depth >= max_depth:
                continue

            for nbr in self._graph.successors(curr_id):
                if nbr in visited:
                    continue

                if relationship:
                    edge_data = self._graph.get_edge_data(curr_id, nbr)
                    if edge_data.get("relationship") != relationship:
                        continue

                visited.add(nbr)
                queue.append((nbr, depth + 1))

        return [n for n in neighbors if n is not None]

    def propagate_impact(
        self,
        source_node_id: str,
        impact_score: float,
        *,
        max_depth: int = 3,
    ) -> ImpactPropagation:
        if not self._graph.has_node(source_node_id):
            return ImpactPropagation(source_node=source_node_id, affected_companies=[])

        affected_companies: dict[str, CompanyImpact] = {}
        queue = deque([(source_node_id, impact_score, [self._graph.nodes[source_node_id]["label"]], 0)])
        visited_max_impact = {source_node_id: abs(impact_score)}

        while queue:
            curr_id, curr_score, path, depth = queue.popleft()
            curr_node_data = self._graph.nodes[curr_id]

            if curr_node_data["node_type"] == "company":
                ticker = curr_id
                company_name = curr_node_data["label"]
                direction = 1.0 if curr_score >= 0 else -1.0
                magnitude = min(1.0, abs(curr_score))

                if ticker in affected_companies:
                    if magnitude > affected_companies[ticker].magnitude:
                        affected_companies[ticker] = CompanyImpact(
                            ticker=ticker,
                            company_name=company_name,
                            direction=direction,
                            magnitude=magnitude,
                            reasoning_path=list(path),
                            confidence=max(0.1, 0.8 - (depth * 0.15)),
                        )
                else:
                    affected_companies[ticker] = CompanyImpact(
                        ticker=ticker,
                        company_name=company_name,
                        direction=direction,
                        magnitude=magnitude,
                        reasoning_path=list(path),
                        confidence=max(0.1, 0.8 - (depth * 0.15)),
                    )

            if depth >= max_depth:
                continue

            for nbr in self._graph.successors(curr_id):
                edge_data = self._graph.get_edge_data(curr_id, nbr)
                edge_weight = edge_data.get("weight", 1.0)
                rel = edge_data.get("relationship", "affects")

                # Attenuate impact score
                next_score = curr_score * edge_weight * 0.8

                if abs(next_score) < 0.05:
                    continue

                nbr_label = self._graph.nodes[nbr]["label"]
                edge_desc = f"{curr_node_data['label']} --[{rel} (w={edge_weight})]--> {nbr_label}"
                new_path = path + [edge_desc]

                if nbr not in visited_max_impact or abs(next_score) > visited_max_impact[nbr]:
                    visited_max_impact[nbr] = abs(next_score)
                    queue.append((nbr, next_score, new_path, depth + 1))

        sorted_companies = sorted(
            affected_companies.values(),
            key=lambda x: x.magnitude,
            reverse=True,
        )

        return ImpactPropagation(
            source_node=self._graph.nodes[source_node_id]["label"],
            affected_companies=sorted_companies,
            propagation_depth=max_depth,
        )

    def find_path(self, from_node_id: str, to_node_id: str) -> list[str]:
        if not (self._graph.has_node(from_node_id) and self._graph.has_node(to_node_id)):
            return []
        try:
            path = nx.shortest_path(self._graph, from_node_id, to_node_id)
            desc_path = []
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i + 1]
                data = self._graph.get_edge_data(u, v)
                rel = data.get("relationship", "affects")
                w = data.get("weight", 1.0)
                desc_path.append(
                    f"{self._graph.nodes[u]['label']} --[{rel} (w={w})]--> {self._graph.nodes[v]['label']}"
                )
            return desc_path
        except nx.NetworkXNoPath:
            return []

    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    def edge_count(self) -> int:
        return self._graph.number_of_edges()
