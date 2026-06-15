"""Domain models for Causal Chain engine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChainNode:
    """A node inside the causal chain propagation path."""
    node_id: str
    label: str
    node_type: str       # country | commodity | sector | company | person
    depth: int
    impact: float        # scaled score
    direction: int       # 1 for positive, -1 for negative
    reason: str
    path: list[str] = field(default_factory=list)


@dataclass
class CausalChainResult:
    """Full result of the causal chain economic propagation trace."""
    trigger_node: str
    trigger_label: str
    base_impact: float
    chain: list[ChainNode]
