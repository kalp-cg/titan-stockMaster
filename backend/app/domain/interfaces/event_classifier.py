"""
Port interfaces for the event classifier and entity extractor ML models.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.models.entity import ExtractedEntity
from app.domain.models.event import EventCategory, EventSubCategory, SentimentLabel


class IEventClassifier(Protocol):
    """Interface for the event classification model (Model 1)."""

    def classify(
        self,
        text: str,
    ) -> tuple[EventCategory, EventSubCategory, SentimentLabel, float, float]:
        """
        Classify a piece of text into an event type.

        Returns:
            Tuple of (category, sub_category, sentiment, severity, confidence).
            severity: float [0.0, 1.0]
            confidence: float [0.0, 1.0]
        """
        ...

    def is_ready(self) -> bool:
        """Return True if the model is loaded and ready."""
        ...


class IEntityExtractor(Protocol):
    """Interface for the named-entity recognition model (Model 2)."""

    def extract(self, text: str) -> list[ExtractedEntity]:
        """
        Extract named entities from text.

        Args:
            text: Source text (title + summary recommended).

        Returns:
            List of extracted entities, sorted by confidence descending.
        """
        ...

    def is_ready(self) -> bool:
        """Return True if the model is loaded and ready."""
        ...


class ISentenceEmbedder(Protocol):
    """Interface for the sentence embedding model (Model 4)."""

    def embed(self, text: str) -> "np.ndarray":  # type: ignore[name-defined]
        """Return a single embedding vector for the input text."""
        ...

    def embed_batch(self, texts: list[str]) -> "np.ndarray":  # type: ignore[name-defined]
        """Return a 2D array of embedding vectors (N × D)."""
        ...

    @property
    def embedding_dim(self) -> int:
        """Dimensionality of the output embeddings."""
        ...

    def is_ready(self) -> bool:
        ...
