"""Port interface for news data sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class RawArticle:
    """A raw, unprocessed news article from any source."""

    title: str
    content: str
    url: str
    source_name: str
    published_at: datetime
    language: str = "en"
    content_hash: str = ""    # SHA-256 for deduplication


class INewsSource(Protocol):
    """Interface for any news data source adapter."""

    @property
    def source_name(self) -> str:
        """Human-readable identifier for this source."""
        ...

    async def fetch_articles(self) -> list[RawArticle]:
        """
        Fetch the latest articles from this source.

        Returns:
            List of raw articles ready for NLP processing.
        """
        ...

    @property
    def reliability_score(self) -> float:
        """
        Estimated reliability of this source [0.0, 1.0].

        Used to weight predictions — high-reliability sources
        contribute more to confidence scores.
        """
        ...
