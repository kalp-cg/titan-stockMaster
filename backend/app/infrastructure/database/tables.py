"""
SQLAlchemy ORM table definitions.

These are infrastructure concerns only — domain models are pure
dataclasses in app/domain/models/.  The repository layer maps
between them.
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.engine import Base


class EventTable(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text, default="")
    raw_text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500), default="")
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    category: Mapped[str] = mapped_column(String(50), default="unknown")
    sub_category: Mapped[str] = mapped_column(String(50), default="unknown")
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")
    severity: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    affected_regions_json: Mapped[str] = mapped_column(Text, default="[]")
    affected_industries_json: Mapped[str] = mapped_column(Text, default="[]")
    entities_json: Mapped[str] = mapped_column(Text, default="[]")

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)

    __table_args__ = (
        Index("ix_events_category_timestamp", "category", "timestamp"),
        Index("ix_events_severity", "severity"),
    )


class PredictionTable(Base):
    __tablename__ = "predictions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    event_id: Mapped[str] = mapped_column(String(36), default="")
    horizon_days: Mapped[int] = mapped_column(Integer)

    bullish_probability: Mapped[float] = mapped_column(Float)
    neutral_probability: Mapped[float] = mapped_column(Float)
    bearish_probability: Mapped[float] = mapped_column(Float)
    expected_move_pct: Mapped[float] = mapped_column(Float)
    volatility_regime: Mapped[str] = mapped_column(String(20), default="medium")

    confidence: Mapped[float] = mapped_column(Float)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    historical_match_score: Mapped[float] = mapped_column(Float, default=0.0)
    reasoning_chain_json: Mapped[str] = mapped_column(Text, default="[]")

    # Self-learning fields
    actual_move_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    prediction_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class UserTable(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class HoldingTable(Base):
    __tablename__ = "holdings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    company_name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[float] = mapped_column(Float)
    avg_buy_price: Mapped[float] = mapped_column(Float)
    thesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    thesis_health: Mapped[float] = mapped_column(Float, default=100.0)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    __table_args__ = (
        Index("ix_holdings_user_id_ticker", "user_id", "ticker", unique=True),
    )


class IPOTable(Base):
    __tablename__ = "ipos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    ticker: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(20), index=True)
    sector: Mapped[str] = mapped_column(String(100))
    industry: Mapped[str] = mapped_column(String(100))
    ipo_type: Mapped[str] = mapped_column(String(20), default="mainboard")

    price_band_low: Mapped[float] = mapped_column(Float, default=0.0)
    price_band_high: Mapped[float] = mapped_column(Float, default=0.0)
    lot_size: Mapped[int] = mapped_column(Integer, default=0)
    issue_size_cr: Mapped[float] = mapped_column(Float, default=0.0)
    gmp: Mapped[float] = mapped_column(Float, default=0.0)
    subscription_overall: Mapped[float] = mapped_column(Float, default=0.0)
    subscription_qib: Mapped[float] = mapped_column(Float, default=0.0)
    subscription_hni: Mapped[float] = mapped_column(Float, default=0.0)
    subscription_retail: Mapped[float] = mapped_column(Float, default=0.0)

    open_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    close_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    listing_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

    financials_json: Mapped[str] = mapped_column(Text, default="{}")
    score_json: Mapped[str] = mapped_column(Text, default="{}")

    listing_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    listing_gain_pct: Mapped[float | None] = mapped_column(Float, nullable=True)


class RiskAlertTable(Base):
    __tablename__ = "risk_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    company_name: Mapped[str] = mapped_column(String(200))
    factor: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    source: Mapped[str] = mapped_column(String(200), default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class ShareholdingTable(Base):
    __tablename__ = "shareholding_patterns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    quarter: Mapped[str] = mapped_column(String(10))
    as_of_date: Mapped[str] = mapped_column(String(10))

    promoter_pct: Mapped[float] = mapped_column(Float, default=0.0)
    promoter_pledge_pct: Mapped[float] = mapped_column(Float, default=0.0)
    fii_pct: Mapped[float] = mapped_column(Float, default=0.0)
    dii_pct: Mapped[float] = mapped_column(Float, default=0.0)
    mutual_fund_pct: Mapped[float] = mapped_column(Float, default=0.0)
    insurance_pct: Mapped[float] = mapped_column(Float, default=0.0)
    retail_pct: Mapped[float] = mapped_column(Float, default=0.0)
    other_pct: Mapped[float] = mapped_column(Float, default=0.0)

    promoter_delta: Mapped[float] = mapped_column(Float, default=0.0)
    fii_delta: Mapped[float] = mapped_column(Float, default=0.0)
    dii_delta: Mapped[float] = mapped_column(Float, default=0.0)

    top_holders_json: Mapped[str] = mapped_column(Text, default="[]")

    __table_args__ = (
        Index("ix_shareholding_ticker_quarter", "ticker", "quarter", unique=True),
    )


class BulkDealTable(Base):
    __tablename__ = "bulk_deals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    deal_date: Mapped[str] = mapped_column(String(10), index=True)
    client_name: Mapped[str] = mapped_column(String(200))
    deal_type: Mapped[str] = mapped_column(String(10))
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    stakeholder_category: Mapped[str] = mapped_column(String(20), default="unknown")
    exchange: Mapped[str] = mapped_column(String(5), default="NSE")


class InsiderTradeTable(Base):
    __tablename__ = "insider_trades"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    trade_date: Mapped[str] = mapped_column(String(10), index=True)
    insider_name: Mapped[str] = mapped_column(String(200))
    designation: Mapped[str] = mapped_column(String(100))
    trade_type: Mapped[str] = mapped_column(String(10))
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    pre_trade_holding_pct: Mapped[float] = mapped_column(Float, default=0.0)
    post_trade_holding_pct: Mapped[float] = mapped_column(Float, default=0.0)
    remarks: Mapped[str] = mapped_column(String(500), default="")


class InstitutionalFlowTable(Base):
    __tablename__ = "institutional_flows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    flow_date: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    fii_buy_cr: Mapped[float] = mapped_column(Float, default=0.0)
    fii_sell_cr: Mapped[float] = mapped_column(Float, default=0.0)
    dii_buy_cr: Mapped[float] = mapped_column(Float, default=0.0)
    dii_sell_cr: Mapped[float] = mapped_column(Float, default=0.0)
    market_regime: Mapped[str] = mapped_column(String(30), default="neutral")


class SmartMoneySignalTable(Base):
    __tablename__ = "smart_money_signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(200))
    accumulation_score: Mapped[float] = mapped_column(Float, default=0.0)
    distribution_score: Mapped[float] = mapped_column(Float, default=0.0)
    conviction_level: Mapped[str] = mapped_column(String(10), default="low")
    divergence_alerts_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class LeadTable(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    company_name: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(20))
    conviction: Mapped[float] = mapped_column(Float)
    expected_move_pct: Mapped[float] = mapped_column(Float, default=0.0)

    trigger_event_id: Mapped[str] = mapped_column(String(36), default="")
    trigger_event_title: Mapped[str] = mapped_column(String(500), default="")

    reasoning_json: Mapped[str] = mapped_column(Text, default="[]")
    signals_json: Mapped[str] = mapped_column(Text, default="{}")

    sector: Mapped[str] = mapped_column(String(100), default="")
    key_voice: Mapped[str | None] = mapped_column(String(100), nullable=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)

    __table_args__ = (
        Index("ix_leads_conviction", "conviction"),
        Index("ix_leads_action", "action"),
    )
