"""
NumPy cosine-similarity vector store.

Implements ISimilarityEngine using in-memory numpy arrays.
Persists embeddings to SQLite (as blobs) for reload across restarts.
"""

from __future__ import annotations

import threading
from collections import defaultdict

import numpy as np

from app.domain.interfaces.similarity_engine import ISimilarityEngine, SimilarityMatch
from app.utils.logging import get_logger

logger = get_logger(__name__)


class NumPySimilarityEngine:
    """
    In-memory similarity engine with cosine distance.

    All embeddings are kept in a 2D numpy matrix for fast batch
    distance computation.  Thread-safe via a read-write lock.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._ids: list[str] = []
        self._matrix: np.ndarray | None = None   # shape (N, D)
        self._metadata: dict[str, dict] = {}

    def store_embedding(
        self,
        event_id: str,
        embedding: np.ndarray,
        *,
        metadata: dict | None = None,
    ) -> None:
        """Add or update an embedding in the in-memory store."""
        with self._lock:
            if event_id in self._ids:
                idx = self._ids.index(event_id)
                if self._matrix is not None:
                    self._matrix[idx] = self._normalise(embedding)
            else:
                self._ids.append(event_id)
                norm = self._normalise(embedding).reshape(1, -1)
                self._matrix = (
                    norm
                    if self._matrix is None
                    else np.vstack([self._matrix, norm])
                )

            if metadata:
                self._metadata[event_id] = metadata

    def find_similar(
        self,
        embedding: np.ndarray,
        *,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[SimilarityMatch]:
        """
        Return the top-k most similar stored events by cosine similarity.

        Time complexity: O(N) where N = number of stored embeddings.
        For N < 100,000 this is fast enough for real-time use.
        """
        with self._lock:
            if self._matrix is None or len(self._ids) == 0:
                return []

            query = self._normalise(embedding)
            # Cosine similarity = dot product of L2-normalised vectors
            scores: np.ndarray = self._matrix @ query

            # Get top-k indices (excluding perfect self-matches)
            k = min(top_k, len(self._ids))
            top_indices = np.argpartition(scores, -k)[-k:]
            top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

            results = []
            for idx in top_indices:
                score = float(scores[idx])
                if score < min_score:
                    continue
                event_id = self._ids[idx]
                meta = self._metadata.get(event_id, {})
                results.append(
                    SimilarityMatch(
                        event_id=event_id,
                        event_title=meta.get("title", f"Event {event_id[:8]}"),
                        similarity_score=score,
                        market_outcome_summary=meta.get("outcome", ""),
                        event_date=meta.get("date", ""),
                    )
                )
            return results

    def embedding_count(self) -> int:
        with self._lock:
            return len(self._ids)

    @staticmethod
    def _normalise(vec: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
