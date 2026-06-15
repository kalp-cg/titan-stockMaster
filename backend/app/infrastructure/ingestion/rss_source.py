"""RSS news source implementation.

Fetches and parses news articles from a list of RSS feeds.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any

import feedparser
import httpx

from app.domain.interfaces.news_source import RawArticle
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


class RSSNewsSource:
    """Adapter for fetching and parsing news from RSS feeds."""

    def __init__(
        self,
        name: str,
        feed_urls: list[str],
        reliability: float = 0.8,
        timeout_seconds: int = 15,
    ) -> None:
        self._name = name
        self._feed_urls = feed_urls
        self._reliability = reliability
        self._timeout_seconds = timeout_seconds

    @property
    def source_name(self) -> str:
        return self._name

    @property
    def reliability_score(self) -> float:
        return self._reliability

    def _clean_html(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _compute_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @timed
    async def fetch_articles(self) -> list[RawArticle]:
        articles: list[RawArticle] = []
        async with httpx.AsyncClient(timeout=self._timeout_seconds, follow_redirects=True) as client:
            for url in self._feed_urls:
                try:
                    logger.debug("Fetching RSS feed", url=url, source=self._name)
                    response = await client.get(url)
                    response.raise_for_status()

                    feed = feedparser.parse(response.text)
                    for entry in feed.entries:
                        title = entry.get("title", "")
                        summary = entry.get("summary", entry.get("description", ""))
                        link = entry.get("link", "")

                        published = None
                        if "published_parsed" in entry and entry.published_parsed:
                            published = datetime(*entry.published_parsed[:6])
                        elif "updated_parsed" in entry and entry.updated_parsed:
                            published = datetime(*entry.updated_parsed[:6])
                        else:
                            published = datetime.utcnow()

                        cleaned_content = self._clean_html(summary or title)
                        if not cleaned_content:
                            continue

                        content_hash = self._compute_hash(cleaned_content)

                        articles.append(
                            RawArticle(
                                title=self._clean_html(title),
                                content=cleaned_content,
                                url=link,
                                source_name=self._name,
                                published_at=published,
                                content_hash=content_hash,
                            )
                        )
                except Exception as e:
                    logger.error("Failed to fetch RSS feed", url=url, error=str(e))

        logger.info("Fetched RSS articles", source=self._name, count=len(articles))
        return articles
