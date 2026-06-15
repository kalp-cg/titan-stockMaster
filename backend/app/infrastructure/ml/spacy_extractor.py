"""
spaCy-based named entity extractor (Model 2).

Extracts and normalises entities from text: companies, countries,
commodities, people, currencies, and sectors.
"""

from __future__ import annotations

import threading
from typing import Any

from app.domain.models.entity import EntityType, ExtractedEntity
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)

# Map spaCy NER labels to our EntityType enum
_SPACY_LABEL_MAP: dict[str, EntityType] = {
    "ORG": EntityType.COMPANY,
    "GPE": EntityType.COUNTRY,        # Geopolitical Entity
    "LOC": EntityType.COUNTRY,
    "MONEY": EntityType.COMMODITY,
    "PERSON": EntityType.PERSON,
    "NORP": EntityType.COUNTRY,       # Nationalities/groups
    "PRODUCT": EntityType.PRODUCT,
    "FACILITY": EntityType.COMPANY,
    "EVENT": EntityType.UNKNOWN,
    "QUANTITY": EntityType.UNKNOWN,
    "PERCENT": EntityType.UNKNOWN,
}

# Known commodities for recognition
_COMMODITY_KEYWORDS: frozenset[str] = frozenset({
    "oil", "crude", "brent", "wti", "gold", "silver", "copper", "steel", "iron",
    "aluminium", "aluminum", "coal", "natural gas", "lng", "wheat", "cotton",
    "rubber", "zinc", "nickel", "platinum", "palladium",
})

# NSE/BSE ticker normalisation — common entity name → ticker
_COMPANY_NORMALISATION: dict[str, str] = {
    "reliance industries": "RELIANCE",
    "reliance": "RELIANCE",
    "tata consultancy": "TCS",
    "tcs": "TCS",
    "infosys": "INFY",
    "hdfc bank": "HDFCBANK",
    "hdfc": "HDFCBANK",
    "icici bank": "ICICIBANK",
    "state bank": "SBIN",
    "sbi": "SBIN",
    "wipro": "WIPRO",
    "ongc": "ONGC",
    "oil and natural gas": "ONGC",
    "hindustan unilever": "HINDUNILVR",
    "hul": "HINDUNILVR",
    "asian paints": "ASIANPAINT",
    "maruti": "MARUTI",
    "maruti suzuki": "MARUTI",
    "itc": "ITC",
    "bajaj finance": "BAJFINANCE",
    "axis bank": "AXISBANK",
    "kotak mahindra": "KOTAKBANK",
    "larsen": "LT",
    "l&t": "LT",
    "titan": "TITAN",
    "sun pharma": "SUNPHARMA",
    "ntpc": "NTPC",
    "power grid": "POWERGRID",
    "tech mahindra": "TECHM",
    "hcl technologies": "HCLTECH",
    "nestle": "NESTLEIND",
    "hal": "HAL",
    "hindustan aeronautics": "HAL",
    "bel": "BEL",
    "bharat electronics": "BEL",
    "indigo": "INDIGO",
    "interglobe": "INDIGO",
    "coal india": "COALINDIA",
    "tata steel": "TATASTEEL",
    "bharat airtel": "BHARTIARTL",
    "airtel": "BHARTIARTL",
    "reliance jio": "RELIANCE",
    # Global companies
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "amazon": "AMZN",
    "tesla": "TSLA",
    "nvidia": "NVDA",
}

_COUNTRY_NORMALISATION: dict[str, str] = {
    "usa": "USA", "united states": "USA", "america": "USA", "american": "USA",
    "india": "IND", "indian": "IND",
    "china": "CHN", "chinese": "CHN",
    "russia": "RUS", "russian": "RUS",
    "iran": "IRN", "iranian": "IRN",
    "middle east": "MIDDLE_EAST",
    "europe": "EUROPE", "european": "EUROPE",
    "germany": "DEU", "france": "FRA", "uk": "GBR", "britain": "GBR",
    "japan": "JPN", "korea": "KOR", "south korea": "KOR",
    "opec": "OPEC",
}

_PERSON_NORMALISATION: dict[str, str] = {
    "trump": "donald_trump", "donald trump": "donald_trump",
    "modi": "narendra_modi", "narendra modi": "narendra_modi",
    "powell": "jerome_powell", "jerome powell": "jerome_powell",
    "musk": "elon_musk", "elon musk": "elon_musk",
}


class SpacyEntityExtractor:
    """
    Named-entity recognition using spaCy with custom finance-domain
    post-processing for normalisation.
    """

    _instance: "SpacyEntityExtractor | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._nlp: Any | None = None
        self._ready = False
        self._model_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "SpacyEntityExtractor":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _load_model(self) -> None:
        if self._ready:
            return
        with self._model_lock:
            if self._ready:
                return
            try:
                import spacy
                self._nlp = spacy.load("en_core_web_sm")
                self._ready = True
                logger.info("spacy_model_loaded")
            except OSError:
                logger.warning(
                    "spacy_model_not_found",
                    hint="Attempting on-the-fly download of en_core_web_sm...",
                )
                try:
                    from spacy.cli import download
                    download("en_core_web_sm")
                    self._nlp = spacy.load("en_core_web_sm")
                    self._ready = True
                    logger.info("spacy_model_downloaded_successfully")
                except Exception as ex:
                    logger.error("spacy_model_download_failed", error=str(ex))
                    self._ready = False

    @timed("extract_entities")
    def extract(self, text: str) -> list[ExtractedEntity]:
        """Extract and normalise named entities from the input text."""
        self._load_model()

        if self._ready and self._nlp:
            entities = self._extract_with_spacy(text)
        else:
            entities = self._extract_rule_based(text)

        # Guarantee key voices / leaders are ALWAYS extracted if present in text
        text_lower = text.lower()
        seen_norms = {e.normalized_name for e in entities}
        for pattern, code in _PERSON_NORMALISATION.items():
            if pattern in text_lower and code not in seen_norms:
                entities.append(
                    ExtractedEntity(
                        text=pattern.title(),
                        entity_type=EntityType.PERSON,
                        confidence=0.9,
                        normalized_name=code
                    )
                )
                seen_norms.add(code)

        return entities

    def _extract_with_spacy(self, text: str) -> list[ExtractedEntity]:
        """Use spaCy for extraction then apply finance normalisation."""
        doc = self._nlp(text[:1000])  # spaCy has no hard limit but speed degrades
        entities: list[ExtractedEntity] = []
        seen: set[str] = set()

        for ent in doc.ents:
            entity_type = _SPACY_LABEL_MAP.get(ent.label_, EntityType.UNKNOWN)
            if entity_type == EntityType.UNKNOWN:
                continue

            text_lower = ent.text.lower().strip()
            if text_lower in seen or len(text_lower) < 2:
                continue
            seen.add(text_lower)

            # Refine: check if it's actually a commodity
            if entity_type in {EntityType.COMPANY, EntityType.UNKNOWN}:
                if any(c in text_lower for c in _COMMODITY_KEYWORDS):
                    entity_type = EntityType.COMMODITY

            normalized = self._normalise(text_lower, entity_type)

            entities.append(
                ExtractedEntity(
                    text=ent.text,
                    entity_type=entity_type,
                    confidence=0.85,  # spaCy doesn't expose token scores by default
                    normalized_name=normalized,
                )
            )

        # Also extract commodity mentions not caught by NER
        entities.extend(self._extract_commodities(text, seen))

        # Sort by market relevance then confidence
        entities.sort(key=lambda e: (not e.is_market_relevant, -e.confidence))
        return entities[:20]  # cap output

    def _normalise(self, text_lower: str, entity_type: EntityType) -> str:
        if entity_type == EntityType.COMPANY:
            for pattern, ticker in _COMPANY_NORMALISATION.items():
                if pattern in text_lower:
                    return ticker
        elif entity_type == EntityType.COUNTRY:
            for pattern, code in _COUNTRY_NORMALISATION.items():
                if pattern in text_lower:
                    return code
        elif entity_type == EntityType.COMMODITY:
            for kw in _COMMODITY_KEYWORDS:
                if kw in text_lower:
                    return kw.upper()
        elif entity_type == EntityType.PERSON:
            for pattern, code in _PERSON_NORMALISATION.items():
                if pattern in text_lower:
                    return code
        return text_lower.upper()

    def _extract_commodities(
        self, text: str, seen: set[str]
    ) -> list[ExtractedEntity]:
        """Find commodity mentions not caught by NER."""
        found = []
        text_lower = text.lower()
        for kw in _COMMODITY_KEYWORDS:
            if kw in text_lower and kw not in seen:
                seen.add(kw)
                found.append(
                    ExtractedEntity(
                        text=kw,
                        entity_type=EntityType.COMMODITY,
                        confidence=0.70,
                        normalized_name=kw.upper(),
                    )
                )
        return found

    def _extract_rule_based(self, text: str) -> list[ExtractedEntity]:
        """Keyword fallback when spaCy is not available."""
        entities = []
        text_lower = text.lower()

        for name, ticker in _COMPANY_NORMALISATION.items():
            if name in text_lower:
                entities.append(
                    ExtractedEntity(
                        text=name,
                        entity_type=EntityType.COMPANY,
                        confidence=0.6,
                        normalized_name=ticker,
                    )
                )

        for name, code in _COUNTRY_NORMALISATION.items():
            if name in text_lower:
                entities.append(
                    ExtractedEntity(
                        text=name,
                        entity_type=EntityType.COUNTRY,
                        confidence=0.6,
                        normalized_name=code,
                    )
                )

        for kw in _COMMODITY_KEYWORDS:
            if kw in text_lower:
                entities.append(
                    ExtractedEntity(
                        text=kw,
                        entity_type=EntityType.COMMODITY,
                        confidence=0.65,
                        normalized_name=kw.upper(),
                    )
                )

        for name, code in _PERSON_NORMALISATION.items():
            if name in text_lower:
                entities.append(
                    ExtractedEntity(
                        text=name,
                        entity_type=EntityType.PERSON,
                        confidence=0.7,
                        normalized_name=code,
                    )
                )

        return entities[:15]

    def is_ready(self) -> bool:
        return self._ready
