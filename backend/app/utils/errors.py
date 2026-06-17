"""
Custom exception hierarchy for Helix Decidex.

All exceptions extend HelixError which carries a human-readable
message, an optional machine-readable error code, and optional
contextual data for debugging.

FastAPI exception handlers are registered in main.py and convert
these exceptions into structured JSON HTTP responses.
"""

from __future__ import annotations

from typing import Any


class HelixError(Exception):
    """Base exception for all application errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str,
        *,
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "detail": self.detail,
        }


# ------------------------------------------------------------------ #
# Ingestion Errors                                                     #
# ------------------------------------------------------------------ #


class IngestionError(HelixError):
    """Raised when a data source fails to deliver expected data."""

    status_code = 502
    error_code = "INGESTION_ERROR"


class RateLimitError(IngestionError):
    """Raised when an upstream source enforces rate limiting."""

    status_code = 429
    error_code = "RATE_LIMIT_ERROR"


class ParseError(IngestionError):
    """Raised when ingested content cannot be parsed."""

    status_code = 422
    error_code = "PARSE_ERROR"


# ------------------------------------------------------------------ #
# ML / Model Errors                                                    #
# ------------------------------------------------------------------ #


class ModelError(HelixError):
    """Raised when an ML model fails to produce a valid output."""

    status_code = 500
    error_code = "MODEL_ERROR"


class ModelNotLoadedError(ModelError):
    """Raised when a required model has not been initialised yet."""

    status_code = 503
    error_code = "MODEL_NOT_LOADED"


# ------------------------------------------------------------------ #
# Prediction Errors                                                    #
# ------------------------------------------------------------------ #


class PredictionError(HelixError):
    """Raised when the prediction pipeline cannot produce a result."""

    status_code = 500
    error_code = "PREDICTION_ERROR"


class InsufficientDataError(PredictionError):
    """Raised when there is not enough historical data to predict."""

    status_code = 422
    error_code = "INSUFFICIENT_DATA"


# ------------------------------------------------------------------ #
# Portfolio Errors                                                     #
# ------------------------------------------------------------------ #


class PortfolioError(HelixError):
    """Raised when a portfolio operation fails."""

    status_code = 400
    error_code = "PORTFOLIO_ERROR"


class HoldingNotFoundError(PortfolioError):
    """Raised when a requested holding is not found."""

    status_code = 404
    error_code = "HOLDING_NOT_FOUND"


# ------------------------------------------------------------------ #
# Graph Errors                                                         #
# ------------------------------------------------------------------ #


class GraphError(HelixError):
    """Raised when the knowledge graph cannot resolve a query."""

    status_code = 500
    error_code = "GRAPH_ERROR"


class NodeNotFoundError(GraphError):
    """Raised when a graph node does not exist."""

    status_code = 404
    error_code = "GRAPH_NODE_NOT_FOUND"


# ------------------------------------------------------------------ #
# Stakeholder Errors                                                   #
# ------------------------------------------------------------------ #


class StakeholderError(HelixError):
    """Raised when stakeholder data retrieval fails."""

    status_code = 502
    error_code = "STAKEHOLDER_ERROR"


# ------------------------------------------------------------------ #
# Not Found                                                            #
# ------------------------------------------------------------------ #


class NotFoundError(HelixError):
    """Generic 404 when a resource is not found."""

    status_code = 404
    error_code = "NOT_FOUND"


# ------------------------------------------------------------------ #
# Validation                                                           #
# ------------------------------------------------------------------ #


class ValidationError(HelixError):
    """Raised when input validation fails outside Pydantic."""

    status_code = 422
    error_code = "VALIDATION_ERROR"
