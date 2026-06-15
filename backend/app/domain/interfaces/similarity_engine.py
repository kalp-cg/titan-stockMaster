"""Port interface for the similarity / vector search engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass
class SimilarityMatch:
    """A historical event matched by vector similarity."""

    event_id: str
    event_title: str
    similarity_score: float      # cosine similarity [0.0, 1.0]
    market_outcome_summary: str  # human-readable summary of what happened
    event_date: str


class ISimilarityEngine(Protocol):
    """Interface for embedding storage and nearest-neighbour search."""

    def store_embedding(
        self,
        event_id: str,
        embedding: np.ndarray,
        *,
        metadata: dict | None = None,
    ) -> None:
        """Persist an event embedding for future similarity searches."""
        ...

    def find_similar(
        self,
        embedding: np.ndarray,
        *,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[SimilarityMatch]:
        """
        Return the top-k most similar historical events.

        Args:
            embedding: Query embedding vector.
            top_k: Maximum number of results.
            min_score: Minimum cosine similarity threshold.
        """
        ...

    def embedding_count(self) -> int:
        """Return total number of stored embeddings."""
        ...
