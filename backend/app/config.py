"""
Application configuration via Pydantic BaseSettings.

All values are loaded from environment variables with sensible defaults
so the app runs out-of-the-box without any .env file.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration.

    Every field can be overridden via an environment variable of the same
    name (case-insensitive).  Nested lists/dicts are accepted as JSON
    strings in the environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Application                                                          #
    # ------------------------------------------------------------------ #
    APP_NAME: str = "Helix Decidex"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ------------------------------------------------------------------ #
    # Database                                                             #
    # ------------------------------------------------------------------ #
    DATABASE_URL: str = "sqlite+aiosqlite:///helix_decidex.db"

    # ------------------------------------------------------------------ #
    # CORS                                                                 #
    # ------------------------------------------------------------------ #
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    # ------------------------------------------------------------------ #
    # ML Models                                                            #
    # ------------------------------------------------------------------ #
    USE_ML_MODELS: bool = False
    MODEL_CACHE_DIR: Path = Path("./model_cache")
    FINBERT_MODEL_NAME: str = "ProsusAI/finbert"
    ZERO_SHOT_MODEL_NAME: str = "facebook/bart-large-mnli"
    SENTENCE_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    SPACY_MODEL_NAME: str = "en_core_web_sm"

    # ------------------------------------------------------------------ #
    # Ingestion                                                            #
    # ------------------------------------------------------------------ #
    INGESTION_INTERVAL_SECONDS: int = 300  # 5 minutes
    MARKET_REFRESH_INTERVAL_SECONDS: int = 15  # 15 seconds
    STAKEHOLDER_REFRESH_INTERVAL_SECONDS: int = 3600  # 1 hour

    NEWS_RSS_FEEDS: list[str] = Field(
        default=[
            "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
            "https://www.moneycontrol.com/rss/marketreports.xml",
            "https://feeds.feedburner.com/ndtvprofit-latest",
            "https://www.business-standard.com/rss/markets-106.rss",
            "https://feeds.reuters.com/reuters/businessNews",
            "https://feeds.cnbc.com/channels/CNBC/id/100003114/device/rss/rss.html",
        ]
    )

    @field_validator("NEWS_RSS_FEEDS", mode="before")
    @classmethod
    def parse_rss_feeds(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    # ------------------------------------------------------------------ #
    # Market Tickers                                                       #
    # ------------------------------------------------------------------ #
    MARKET_TICKERS: list[str] = Field(
        default=[
            # NSE Blue-chips
            "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
            "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
            "LT.NS", "BAJFINANCE.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
            "TITAN.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "WIPRO.NS", "ONGC.NS",
            "NTPC.NS", "POWERGRID.NS", "TECHM.NS", "HCLTECH.NS", "NESTLEIND.NS",
            "HAL.NS", "BEL.NS", "INDIGO.NS", "COALINDIA.NS", "TATASTEEL.NS",
            # Indices
            "^NSEI",   # NIFTY 50
            "^BSESN",  # SENSEX
            "^NSEBANK", # BANK NIFTY
            "^GSPC",   # S&P 500
            "^IXIC",   # NASDAQ
            "^FTSE",   # FTSE 100
            "^N225",   # Nikkei 225
            "^GDAXI",  # DAX
            "^HSI",    # Hang Seng Index
            # Commodities
            "GC=F",   # Gold
            "CL=F",   # Crude Oil (WTI)
            "BZ=F",   # Brent Crude
            "SI=F",   # Silver
            # Foreign Stocks
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA",
        ]
    )

    @field_validator("MARKET_TICKERS", mode="before")
    @classmethod
    def parse_tickers(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    # ------------------------------------------------------------------ #
    # Prediction                                                           #
    # ------------------------------------------------------------------ #
    PREDICTION_HORIZONS_DAYS: list[int] = Field(default=[1, 3, 7, 30])
    MIN_CONFIDENCE_THRESHOLD: float = 0.45
    SIMILARITY_TOP_K: int = 5

    # ------------------------------------------------------------------ #
    # NSE/BSE Data                                                         #
    # ------------------------------------------------------------------ #
    NSE_BASE_URL: str = "https://www.nseindia.com"
    BSE_BASE_URL: str = "https://www.bseindia.com"
    HTTP_REQUEST_TIMEOUT_SECONDS: int = 30
    HTTP_MAX_RETRIES: int = 3


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
