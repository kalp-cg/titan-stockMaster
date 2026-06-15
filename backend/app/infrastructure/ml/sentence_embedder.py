"""
SentenceTransformer embedding model (Model 4).

Generates dense vector representations of text for semantic similarity
search. Thread-safe singleton with lazy loading.
"""

from __future__ import annotations

import threading
from typing import Any

import numpy as np

from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_EMBEDDING_DIM = 384  # MiniLM-L6-v2 output dimension


class SentenceEmbedder:
    """Thread-safe singleton sentence embedding model."""

    _instance: "SentenceEmbedder | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._model: Any | None = None
        self._ready = False
        self._model_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "SentenceEmbedder":
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
            from app.config import get_settings
            if not get_settings().USE_ML_MODELS:
                logger.info("sentence_embedder_disabled_using_hash_fallback")
                self._ready = False
                return
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(_MODEL_NAME)
                self._ready = True
                logger.info("sentence_embedder_loaded", model=_MODEL_NAME)
            except Exception as exc:
                logger.error("sentence_embedder_load_failed", error=str(exc))

    @timed("embed_text")
    def embed(self, text: str) -> np.ndarray:
        """Return a single embedding vector for the input text."""
        self._load_model()
        if self._model is None:
            return self._fallback_embed(text)
        result: np.ndarray = self._model.encode(text, convert_to_numpy=True)
        return result

    @timed("embed_batch")
    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Return a 2D embedding matrix (N × D)."""
        self._load_model()
        if self._model is None:
            return np.stack([self._fallback_embed(t) for t in texts])
        result: np.ndarray = self._model.encode(
            texts, convert_to_numpy=True, batch_size=32, show_progress_bar=False
        )
        return result

    def _fallback_embed(self, text: str) -> np.ndarray:
        """
        Deterministic hash-based fallback embedding when the model isn't loaded.
        Preserves basic similarity via term-frequency hashing.
        """
        vec = np.zeros(_EMBEDDING_DIM)
        for i, word in enumerate(text.lower().split()[:50]):
            idx = hash(word) % _EMBEDDING_DIM
            vec[idx] += 1.0 / (i + 1)  # TF-style weighting
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    @property
    def embedding_dim(self) -> int:
        return _EMBEDDING_DIM

    def is_ready(self) -> bool:
        return self._ready
