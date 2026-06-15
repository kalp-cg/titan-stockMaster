"""
FinBERT + Zero-Shot event classifier.

Implements IEventClassifier using two HuggingFace models:
1. FinBERT for financial sentiment (positive/negative/neutral).
2. Zero-shot BART-MNLI for event category classification.

Both models are loaded lazily on first use to avoid blocking startup.
"""

from __future__ import annotations

import threading
from typing import Any

from app.domain.models.event import EventCategory, EventSubCategory, SentimentLabel
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)

# Zero-shot candidate labels mapped to EventCategory
_CATEGORY_LABELS: list[str] = [
    "geopolitical conflict war military sanctions",
    "economic data inflation interest rates GDP unemployment",
    "company earnings merger acquisition bankruptcy layoffs",
    "regulatory policy government ban approval investigation",
    "stock market crash rally IPO volatility",
]

_CATEGORY_MAP: dict[int, EventCategory] = {
    0: EventCategory.GEOPOLITICAL,
    1: EventCategory.ECONOMIC,
    2: EventCategory.COMPANY,
    3: EventCategory.REGULATORY,
    4: EventCategory.MARKET,
}

# Sub-category labels for secondary classification
_SUB_CATEGORY_LABELS: dict[EventCategory, list[tuple[str, EventSubCategory]]] = {
    EventCategory.GEOPOLITICAL: [
        ("war military conflict attack strike", EventSubCategory.WAR),
        ("sanctions embargo trade restriction", EventSubCategory.SANCTIONS),
        ("trade war tariff import export", EventSubCategory.TRADE_WAR),
        ("election vote political crisis", EventSubCategory.ELECTION),
    ],
    EventCategory.ECONOMIC: [
        ("inflation CPI WPI price rise", EventSubCategory.INFLATION),
        ("interest rate central bank Fed RBI repo", EventSubCategory.INTEREST_RATE),
        ("GDP growth recession economy", EventSubCategory.GDP),
        ("commodity oil gold crude price shock", EventSubCategory.COMMODITY_SHOCK),
    ],
    EventCategory.COMPANY: [
        ("earnings revenue profit quarterly results", EventSubCategory.EARNINGS),
        ("merger acquisition takeover deal", EventSubCategory.MERGER),
        ("layoffs job cuts workforce reduction", EventSubCategory.LAYOFFS),
        ("IPO listing initial public offering", EventSubCategory.IPO),
        ("bankruptcy insolvency debt default", EventSubCategory.BANKRUPTCY),
    ],
    EventCategory.REGULATORY: [
        ("ban prohibition blocked restricted", EventSubCategory.GOVERNMENT_BAN),
        ("approval cleared allowed regulatory", EventSubCategory.REGULATORY_APPROVAL),
        ("antitrust monopoly competition", EventSubCategory.ANTITRUST),
        ("subsidy incentive scheme policy", EventSubCategory.SUBSIDY),
    ],
    EventCategory.MARKET: [
        ("crash fall drop plunge selloff", EventSubCategory.CRASH),
        ("rally surge rise bull market", EventSubCategory.RALLY),
        ("volatility VIX fear uncertainty", EventSubCategory.VOLATILITY_SPIKE),
    ],
}


class FinBERTEventClassifier:
    """
    Hybrid event classifier using FinBERT sentiment + zero-shot classification.

    Thread-safe singleton — models are loaded once and reused.
    """

    _instance: "FinBERTEventClassifier | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._finbert_pipeline: Any | None = None
        self._zero_shot_pipeline: Any | None = None
        self._ready = False
        self._model_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "FinBERTEventClassifier":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _load_models(self) -> None:
        """Load models lazily. Called on first classify() invocation."""
        if self._ready:
            return

        with self._model_lock:
            if self._ready:
                return

            from app.config import get_settings
            if not get_settings().USE_ML_MODELS:
                logger.info("ml_models_disabled_using_rule_fallback")
                self._ready = False
                return

            try:
                from transformers import pipeline

                logger.info("loading_finbert_model")
                self._finbert_pipeline = pipeline(
                    "text-classification",
                    model="ProsusAI/finbert",
                    top_k=None,
                )

                logger.info("loading_zero_shot_model")
                self._zero_shot_pipeline = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli",
                )

                self._ready = True
                logger.info("ml_models_loaded")

            except Exception as exc:
                logger.error("model_load_failed", error=str(exc))
                # Fall back to rule-based classification
                self._ready = False

    @timed("classify_event")
    def classify(
        self,
        text: str,
    ) -> tuple[EventCategory, EventSubCategory, SentimentLabel, float, float]:
        """
        Classify text into event category, sub-category, sentiment, severity, confidence.

        Falls back gracefully to rule-based heuristics if models aren't loaded.
        """
        self._load_models()

        if self._ready and self._finbert_pipeline and self._zero_shot_pipeline:
            return self._classify_with_models(text)
        else:
            return self._classify_rule_based(text)

    def _classify_with_models(
        self, text: str
    ) -> tuple[EventCategory, EventSubCategory, SentimentLabel, float, float]:
        """Use ML models for classification."""
        # Truncate to model max length
        truncated = text[:512]

        # FinBERT sentiment
        sentiment_results = self._finbert_pipeline(truncated)[0]
        sentiment_map = {r["label"]: r["score"] for r in sentiment_results}
        pos = sentiment_map.get("positive", 0.0)
        neg = sentiment_map.get("negative", 0.0)
        neu = sentiment_map.get("neutral", 0.0)

        if pos > neg and pos > neu:
            sentiment = SentimentLabel.POSITIVE
            sentiment_confidence = pos
        elif neg > pos and neg > neu:
            sentiment = SentimentLabel.NEGATIVE
            sentiment_confidence = neg
        else:
            sentiment = SentimentLabel.NEUTRAL
            sentiment_confidence = neu

        # Zero-shot category
        zs_result = self._zero_shot_pipeline(truncated, _CATEGORY_LABELS)
        best_idx = zs_result["labels"].index(zs_result["labels"][0])
        category = _CATEGORY_MAP.get(
            _CATEGORY_LABELS.index(zs_result["labels"][0]), EventCategory.UNKNOWN
        )
        category_confidence = zs_result["scores"][0]

        # Sub-category
        sub_category = self._classify_sub_category(truncated, category)

        # Severity: combination of negative sentiment + category confidence
        severity = (neg * 0.6 + (1 - neu) * 0.4) * category_confidence
        severity = min(max(severity, 0.0), 1.0)

        # Overall confidence
        confidence = (sentiment_confidence + category_confidence) / 2

        return category, sub_category, sentiment, severity, confidence

    def _classify_sub_category(
        self, text: str, category: EventCategory
    ) -> EventSubCategory:
        """Zero-shot classify into a sub-category for the given category."""
        sub_labels = _SUB_CATEGORY_LABELS.get(category, [])
        if not sub_labels or not self._zero_shot_pipeline:
            return EventSubCategory.UNKNOWN

        label_texts = [label for label, _ in sub_labels]
        result = self._zero_shot_pipeline(text, label_texts)
        best_label = result["labels"][0]
        for label_text, sub_cat in sub_labels:
            if label_text == best_label:
                return sub_cat
        return EventSubCategory.UNKNOWN

    def _classify_rule_based(
        self, text: str
    ) -> tuple[EventCategory, EventSubCategory, SentimentLabel, float, float]:
        """Simple keyword-based fallback classifier."""
        text_lower = text.lower()

        # Sentiment keywords
        positive_words = {"surge", "rally", "gain", "rise", "growth", "profit", "strong"}
        negative_words = {"crash", "fall", "drop", "sanction", "war", "attack", "default", "ban"}

        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)

        if neg_count > pos_count:
            sentiment = SentimentLabel.NEGATIVE
            severity = min(neg_count / 5, 1.0)
        elif pos_count > neg_count:
            sentiment = SentimentLabel.POSITIVE
            severity = 0.3
        else:
            sentiment = SentimentLabel.NEUTRAL
            severity = 0.2

        # Category keywords
        geo_words = {"war", "military", "sanction", "conflict", "attack", "iran", "china", "russia"}
        eco_words = {"inflation", "rate", "fed", "rbi", "gdp", "recession", "cpi"}
        comp_words = {"earnings", "merger", "acquisition", "revenue", "profit", "ipo", "layoff"}
        reg_words = {"ban", "policy", "regulation", "government", "ministry", "sebi", "rbi"}

        if any(w in text_lower for w in geo_words):
            category = EventCategory.GEOPOLITICAL
            sub = EventSubCategory.WAR if "war" in text_lower else EventSubCategory.SANCTIONS
        elif any(w in text_lower for w in eco_words):
            category = EventCategory.ECONOMIC
            sub = EventSubCategory.INTEREST_RATE if "rate" in text_lower else EventSubCategory.INFLATION
        elif any(w in text_lower for w in comp_words):
            category = EventCategory.COMPANY
            sub = EventSubCategory.EARNINGS if "earnings" in text_lower else EventSubCategory.MERGER
        elif any(w in text_lower for w in reg_words):
            category = EventCategory.REGULATORY
            sub = EventSubCategory.POLICY_CHANGE
        else:
            category = EventCategory.UNKNOWN
            sub = EventSubCategory.UNKNOWN

        return category, sub, sentiment, severity, 0.5

    def is_ready(self) -> bool:
        return self._ready
