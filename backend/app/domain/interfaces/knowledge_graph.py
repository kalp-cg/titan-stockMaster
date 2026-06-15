"""Port interfaces for the knowledge graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.domain.models.company import CompanyImpact


@dataclass
class GraphNode:
    """A node in the knowledge graph."""

    node_id: str
    node_type: str     # "country", "commodity", "sector", "company", etc.
    label: str
    metadata: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    """A directed, weighted edge in the knowledge graph."""

    source_id: str
    target_id: str
    relationship: str   # "affects", "supplies", "depends_on", etc.
    weight: float = 1.0  # positive = amplifies, negative = dampens


@dataclass
class ImpactPropagation:
    """Result of propagating an impact through the graph."""

    source_node: str
    affected_companies: list[CompanyImpact] = field(default_factory=list)
    propagation_depth: int = 0


class IKnowledgeGraph(Protocol):
    """Interface for the economic knowledge graph."""

    def add_node(self, node: GraphNode) -> None:
        """Add or update a node."""
        ...

    def remove_node(self, node_id: str) -> None:
        """Remove a node."""
        ...

    def add_edge(self, edge: GraphEdge) -> None:
        """Add or update a directed edge."""
        ...

    def get_node(self, node_id: str) -> GraphNode | None:
        ...

    def get_neighbors(
        self,
        node_id: str,
        *,
        relationship: str | None = None,
        max_depth: int = 1,
    ) -> list[GraphNode]:
        """Return all nodes reachable from node_id within max_depth hops."""
        ...

    def propagate_impact(
        self,
        source_node_id: str,
        impact_score: float,
        *,
        max_depth: int = 3,
    ) -> ImpactPropagation:
        """
        Propagate a signed impact score through the graph.

        Args:
            source_node_id: The graph node where the impact originates.
            impact_score: Signed score, positive = bullish, negative = bearish.
            max_depth: Maximum hops to traverse.

        Returns:
            ImpactPropagation with a ranked list of affected companies.
        """
        ...

    def find_path(
        self,
        from_node_id: str,
        to_node_id: str,
    ) -> list[str]:
        """Return the shortest causal path between two nodes."""
        ...

    def node_count(self) -> int:
        ...

    def edge_count(self) -> int:
        ...
