"""Domain models for extracted named entities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EntityType(str, Enum):
    """Category of a named entity extracted from text."""

    COMPANY = "company"
    COUNTRY = "country"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    SECTOR = "sector"
    INDUSTRY = "industry"
    PERSON = "person"
    INDEX = "index"
    PRODUCT = "product"
    UNKNOWN = "unknown"


@dataclass
class ExtractedEntity:
    """A named entity identified by the NER model.

    Attributes:
        text: The raw surface form as it appeared in the source text.
        entity_type: Normalised entity category.
        confidence: Model confidence score [0.0, 1.0].
        normalized_name: Canonical identifier (e.g. ticker or ISO code).
                         Empty string if no normalisation was possible.
    """

    text: str
    entity_type: EntityType
    confidence: float
    normalized_name: str = ""

    @property
    def is_market_relevant(self) -> bool:
        """True for entity types that have direct market significance."""
        return self.entity_type in {
            EntityType.COMPANY,
            EntityType.COMMODITY,
            EntityType.INDEX,
            EntityType.CURRENCY,
            EntityType.COUNTRY,
            EntityType.PERSON,
        }
