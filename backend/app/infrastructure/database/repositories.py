"""
Concrete SQLAlchemy repository implementations.

Each class implements its corresponding domain interface and maps
between SQLAlchemy ORM rows and pure domain dataclasses.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.event import (
    EventCategory,
    EventSubCategory,
    MarketEvent,
    SentimentLabel,
)
from app.domain.models.ipo import IPO, IPOFinancials, IPOScore, IPOStatus
from app.domain.models.lead import AlphaLead, LeadAction
from app.domain.models.portfolio import Holding
from app.domain.models.prediction import (
    EvidenceItem,
    Prediction,
    ProbabilityDistribution,
    VolatilityRegime,
)
from app.domain.models.risk import RiskAlert, RiskFactor, RiskSeverity
from app.domain.models.stakeholder import (
    BlockDeal,
    BulkDeal,
    ConvictionLevel,
    DealType,
    EvidenceFactor,
    InstitutionalFlow,
    InsiderTrade,
    MarketRegime,
    ShareholdingPattern,
    SmartMoneySignal,
    StakeholderCategory,
)
from app.infrastructure.database.tables import (
    BulkDealTable,
    EventTable,
    HoldingTable,
    InstitutionalFlowTable,
    InsiderTradeTable,
    IPOTable,
    LeadTable,
    PredictionTable,
    RiskAlertTable,
    ShareholdingTable,
    SmartMoneySignalTable,
    UserTable,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ------------------------------------------------------------------ #
# Event Repository                                                     #
# ------------------------------------------------------------------ #


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_row(self, event: MarketEvent) -> EventTable:
        entities_list = [
            {
                "text": e.text,
                "entity_type": e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type),
                "confidence": e.confidence,
                "normalized_name": e.normalized_name,
            }
            for e in event.entities
        ]
        return EventTable(
            id=event.id,
            title=event.title,
            summary=event.summary,
            raw_text=event.raw_text,
            source=event.source,
            url=event.url,
            content_hash=_content_hash(event.raw_text),
            category=event.category.value,
            sub_category=event.sub_category.value,
            sentiment=event.sentiment.value,
            severity=event.severity,
            confidence=event.confidence,
            affected_regions_json=json.dumps(event.affected_regions),
            affected_industries_json=json.dumps(event.affected_industries),
            entities_json=json.dumps(entities_list),
            timestamp=event.timestamp,
        )

    def _to_domain(self, row: EventTable) -> MarketEvent:
        from app.domain.models.entity import ExtractedEntity, EntityType
        try:
            entities_data = json.loads(row.entities_json) if row.entities_json else []
            entities = [
                ExtractedEntity(
                    text=e["text"],
                    entity_type=EntityType(e["entity_type"]),
                    confidence=e["confidence"],
                    normalized_name=e["normalized_name"],
                )
                for e in entities_data
            ]
        except Exception:
            entities = []

        return MarketEvent(
            id=row.id,
            title=row.title,
            summary=row.summary,
            raw_text=row.raw_text,
            source=row.source,
            url=row.url,
            category=EventCategory(row.category),
            sub_category=EventSubCategory(row.sub_category),
            sentiment=SentimentLabel(row.sentiment),
            severity=row.severity,
            confidence=row.confidence,
            affected_regions=json.loads(row.affected_regions_json),
            affected_industries=json.loads(row.affected_industries_json),
            entities=entities,
            timestamp=row.timestamp,
        )

    async def save(self, event: MarketEvent) -> MarketEvent:
        row = self._to_row(event)
        self._session.add(row)
        await self._session.flush()
        return event

    async def get_by_id(self, event_id: str) -> MarketEvent | None:
        result = await self._session.get(EventTable, event_id)
        return self._to_domain(result) if result else None

    async def get_recent(self, *, limit: int = 50) -> list[MarketEvent]:
        stmt = select(EventTable).order_by(EventTable.timestamp.desc()).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def get_by_category(self, category: str, *, limit: int = 20) -> list[MarketEvent]:
        stmt = (
            select(EventTable)
            .where(EventTable.category == category)
            .order_by(EventTable.timestamp.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def exists_by_hash(self, content_hash: str) -> bool:
        stmt = select(EventTable.id).where(EventTable.content_hash == content_hash).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar() is not None


# ------------------------------------------------------------------ #
# Prediction Repository                                                #
# ------------------------------------------------------------------ #


class PredictionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, row: PredictionTable) -> Prediction:
        dist = ProbabilityDistribution(
            bullish_probability=row.bullish_probability,
            neutral_probability=row.neutral_probability,
            bearish_probability=row.bearish_probability,
            expected_move_pct=row.expected_move_pct,
            volatility_regime=VolatilityRegime(row.volatility_regime),
        )
        return Prediction(
            id=row.id,
            ticker=row.ticker,
            event_id=row.event_id,
            horizon_days=row.horizon_days,
            distribution=dist,
            confidence=row.confidence,
            evidence_count=row.evidence_count,
            historical_match_score=row.historical_match_score,
            reasoning_chain=json.loads(row.reasoning_chain_json),
            actual_move_pct=row.actual_move_pct,
            prediction_correct=row.prediction_correct,
            timestamp=row.timestamp,
        )

    def _to_row(self, pred: Prediction) -> PredictionTable:
        return PredictionTable(
            id=pred.id,
            ticker=pred.ticker,
            event_id=pred.event_id,
            horizon_days=pred.horizon_days,
            bullish_probability=pred.distribution.bullish_probability,
            neutral_probability=pred.distribution.neutral_probability,
            bearish_probability=pred.distribution.bearish_probability,
            expected_move_pct=pred.distribution.expected_move_pct,
            volatility_regime=pred.distribution.volatility_regime.value,
            confidence=pred.confidence,
            evidence_count=pred.evidence_count,
            historical_match_score=pred.historical_match_score,
            reasoning_chain_json=json.dumps(pred.reasoning_chain),
            actual_move_pct=pred.actual_move_pct,
            prediction_correct=pred.prediction_correct,
            timestamp=pred.timestamp,
        )

    async def save(self, prediction: Prediction) -> Prediction:
        self._session.add(self._to_row(prediction))
        await self._session.flush()
        return prediction

    async def get_by_id(self, prediction_id: str) -> Prediction | None:
        row = await self._session.get(PredictionTable, prediction_id)
        return self._to_domain(row) if row else None

    async def get_for_ticker(self, ticker: str, *, limit: int = 10) -> list[Prediction]:
        stmt = (
            select(PredictionTable)
            .where(PredictionTable.ticker == ticker)
            .order_by(PredictionTable.timestamp.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def get_unevaluated(self) -> list[Prediction]:
        stmt = select(PredictionTable).where(PredictionTable.prediction_correct.is_(None))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def update_outcome(self, prediction_id: str, actual_move_pct: float) -> None:
        row = await self._session.get(PredictionTable, prediction_id)
        if row:
            row.actual_move_pct = actual_move_pct
            expected = row.expected_move_pct
            row.prediction_correct = (expected > 0 and actual_move_pct > 0) or (
                expected < 0 and actual_move_pct < 0
            )
            await self._session.flush()


# ------------------------------------------------------------------ #
# Holding Repository                                                   #
# ------------------------------------------------------------------ #


class HoldingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, row: HoldingTable) -> Holding:
        return Holding(
            id=row.id,
            user_id=row.user_id,
            ticker=row.ticker,
            company_name=row.company_name,
            quantity=row.quantity,
            avg_buy_price=row.avg_buy_price,
            thesis=row.thesis or "",
            thesis_health=row.thesis_health,
            added_at=row.added_at,
        )

    async def save(self, holding: Holding) -> Holding:
        existing = await self.get_by_ticker(holding.user_id, holding.ticker)
        if existing:
            row = await self._session.get(HoldingTable, existing.id)
            if row:
                row.quantity = holding.quantity
                row.avg_buy_price = holding.avg_buy_price
                row.thesis = holding.thesis
                row.thesis_health = holding.thesis_health
        else:
            self._session.add(
                HoldingTable(
                    id=holding.id,
                    user_id=holding.user_id,
                    ticker=holding.ticker,
                    company_name=holding.company_name,
                    quantity=holding.quantity,
                    avg_buy_price=holding.avg_buy_price,
                    thesis=holding.thesis,
                    thesis_health=holding.thesis_health,
                    added_at=holding.added_at,
                )
            )
        await self._session.flush()
        return holding

    async def get_all(self, user_id: str | None = None) -> list[Holding]:
        stmt = select(HoldingTable)
        if user_id is not None:
            stmt = stmt.where(HoldingTable.user_id == user_id)
        stmt = stmt.order_by(HoldingTable.added_at)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def get_by_ticker(self, user_id: str, ticker: str) -> Holding | None:
        stmt = (
            select(HoldingTable)
            .where(HoldingTable.user_id == user_id)
            .where(HoldingTable.ticker == ticker)
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def delete(self, user_id: str, ticker: str) -> bool:
        stmt = (
            delete(HoldingTable)
            .where(HoldingTable.user_id == user_id)
            .where(HoldingTable.ticker == ticker)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, id: str, email: str, hashed_password: str) -> UserTable:
        user = UserTable(
            id=id,
            email=email.lower().strip(),
            hashed_password=hashed_password,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_email(self, email: str) -> UserTable | None:
        stmt = select(UserTable).where(UserTable.email == email.lower().strip()).limit(1)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return row

    async def get_by_id(self, user_id: str) -> UserTable | None:
        stmt = select(UserTable).where(UserTable.id == user_id).limit(1)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return row



# ------------------------------------------------------------------ #
# Stakeholder Repository                                               #
# ------------------------------------------------------------------ #


class StakeholderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # Shareholding
    async def save_shareholding(self, pattern: ShareholdingPattern) -> ShareholdingPattern:
        from sqlalchemy.exc import IntegrityError

        existing_stmt = (
            select(ShareholdingTable)
            .where(ShareholdingTable.ticker == pattern.ticker)
            .where(ShareholdingTable.quarter == pattern.quarter)
            .limit(1)
        )
        existing = (await self._session.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            existing.promoter_pct = pattern.promoter_pct
            existing.fii_pct = pattern.fii_pct
            existing.dii_pct = pattern.dii_pct
            existing.promoter_delta = pattern.promoter_delta
            existing.fii_delta = pattern.fii_delta
            await self._session.flush()
        else:
            try:
                async with self._session.begin_nested():
                    self._session.add(
                        ShareholdingTable(
                            id=pattern.id,
                            ticker=pattern.ticker,
                            quarter=pattern.quarter,
                            as_of_date=str(pattern.as_of_date),
                            promoter_pct=pattern.promoter_pct,
                            promoter_pledge_pct=pattern.promoter_pledge_pct,
                            fii_pct=pattern.fii_pct,
                            dii_pct=pattern.dii_pct,
                            mutual_fund_pct=pattern.mutual_fund_pct,
                            insurance_pct=pattern.insurance_pct,
                            retail_pct=pattern.retail_pct,
                            other_pct=pattern.other_pct,
                            promoter_delta=pattern.promoter_delta,
                            fii_delta=pattern.fii_delta,
                            dii_delta=pattern.dii_delta,
                            top_holders_json=json.dumps([
                                {
                                    "name": h.name,
                                    "category": h.category.value,
                                    "holding_pct": h.holding_pct,
                                    "change": h.change_vs_prev_quarter,
                                }
                                for h in pattern.top_holders
                            ]),
                        )
                    )
                    await self._session.flush()
            except IntegrityError:
                # Concurrent insert occurred, query the newly committed row and update it
                existing = (await self._session.execute(existing_stmt)).scalar_one_or_none()
                if existing:
                    existing.promoter_pct = pattern.promoter_pct
                    existing.fii_pct = pattern.fii_pct
                    existing.dii_pct = pattern.dii_pct
                    existing.promoter_delta = pattern.promoter_delta
                    existing.fii_delta = pattern.fii_delta
                    await self._session.flush()
        return pattern

    async def get_shareholding(self, ticker: str) -> ShareholdingPattern | None:
        stmt = (
            select(ShareholdingTable)
            .where(ShareholdingTable.ticker == ticker)
            .order_by(ShareholdingTable.as_of_date.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._row_to_shareholding(row) if row else None

    async def get_shareholding_history(
        self, ticker: str, *, quarters: int = 8
    ) -> list[ShareholdingPattern]:
        stmt = (
            select(ShareholdingTable)
            .where(ShareholdingTable.ticker == ticker)
            .order_by(ShareholdingTable.as_of_date.desc())
            .limit(quarters)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._row_to_shareholding(r) for r in reversed(rows)]

    def _row_to_shareholding(self, row: ShareholdingTable) -> ShareholdingPattern:
        from datetime import date

        holders_data = json.loads(row.top_holders_json)
        from app.domain.models.stakeholder import InstitutionalHolder

        holders = [
            InstitutionalHolder(
                name=h["name"],
                category=StakeholderCategory(h.get("category", "unknown")),
                holding_pct=h["holding_pct"],
                change_vs_prev_quarter=h.get("change", 0.0),
            )
            for h in holders_data
        ]
        return ShareholdingPattern(
            id=row.id,
            ticker=row.ticker,
            quarter=row.quarter,
            as_of_date=date.fromisoformat(row.as_of_date),
            promoter_pct=row.promoter_pct,
            promoter_pledge_pct=row.promoter_pledge_pct,
            fii_pct=row.fii_pct,
            dii_pct=row.dii_pct,
            mutual_fund_pct=row.mutual_fund_pct,
            insurance_pct=row.insurance_pct,
            retail_pct=row.retail_pct,
            other_pct=row.other_pct,
            promoter_delta=row.promoter_delta,
            fii_delta=row.fii_delta,
            dii_delta=row.dii_delta,
            top_holders=holders,
        )

    # Bulk Deals
    async def save_bulk_deal(self, deal: BulkDeal) -> BulkDeal:
        self._session.add(
            BulkDealTable(
                id=deal.id,
                ticker=deal.ticker,
                deal_date=str(deal.date),
                client_name=deal.client_name,
                deal_type=deal.deal_type.value,
                quantity=deal.quantity,
                price=deal.price,
                stakeholder_category=deal.stakeholder_category.value,
                exchange=deal.exchange,
            )
        )
        await self._session.flush()
        return deal

    async def get_bulk_deals(self, ticker: str | None, *, days: int = 30) -> list[BulkDeal]:
        from datetime import date, timedelta

        cutoff = str(date.today() - timedelta(days=days))
        stmt = select(BulkDealTable).where(BulkDealTable.deal_date >= cutoff)
        if ticker:
            stmt = stmt.where(BulkDealTable.ticker == ticker)
        stmt = stmt.order_by(BulkDealTable.deal_date.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            BulkDeal(
                id=r.id,
                ticker=r.ticker,
                date=__import__("datetime").date.fromisoformat(r.deal_date),
                client_name=r.client_name,
                deal_type=DealType(r.deal_type),
                quantity=r.quantity,
                price=r.price,
                stakeholder_category=StakeholderCategory(r.stakeholder_category),
                exchange=r.exchange,
            )
            for r in rows
        ]

    # Insider Trades
    async def save_insider_trade(self, trade: InsiderTrade) -> InsiderTrade:
        self._session.add(
            InsiderTradeTable(
                id=trade.id,
                ticker=trade.ticker,
                trade_date=str(trade.date),
                insider_name=trade.insider_name,
                designation=trade.designation,
                trade_type=trade.trade_type.value,
                quantity=trade.quantity,
                price=trade.price,
                pre_trade_holding_pct=trade.pre_trade_holding_pct,
                post_trade_holding_pct=trade.post_trade_holding_pct,
                remarks=trade.remarks,
            )
        )
        await self._session.flush()
        return trade

    async def get_insider_trades(
        self, ticker: str | None, *, days: int = 90
    ) -> list[InsiderTrade]:
        from datetime import date, timedelta

        cutoff = str(date.today() - timedelta(days=days))
        stmt = select(InsiderTradeTable).where(InsiderTradeTable.trade_date >= cutoff)
        if ticker:
            stmt = stmt.where(InsiderTradeTable.ticker == ticker)
        stmt = stmt.order_by(InsiderTradeTable.trade_date.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            InsiderTrade(
                id=r.id,
                ticker=r.ticker,
                date=__import__("datetime").date.fromisoformat(r.trade_date),
                insider_name=r.insider_name,
                designation=r.designation,
                trade_type=DealType(r.trade_type),
                quantity=r.quantity,
                price=r.price,
                pre_trade_holding_pct=r.pre_trade_holding_pct,
                post_trade_holding_pct=r.post_trade_holding_pct,
                remarks=r.remarks,
            )
            for r in rows
        ]

    # Institutional Flows
    async def save_institutional_flow(self, flow: InstitutionalFlow) -> InstitutionalFlow:
        from sqlalchemy.exc import IntegrityError

        existing_stmt = (
            select(InstitutionalFlowTable)
            .where(InstitutionalFlowTable.flow_date == str(flow.date))
            .limit(1)
        )
        existing = (await self._session.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            existing.fii_buy_cr = flow.fii_buy_cr
            existing.fii_sell_cr = flow.fii_sell_cr
            existing.dii_buy_cr = flow.dii_buy_cr
            existing.dii_sell_cr = flow.dii_sell_cr
            existing.market_regime = flow.market_regime.value
            await self._session.flush()
        else:
            try:
                async with self._session.begin_nested():
                    self._session.add(
                        InstitutionalFlowTable(
                            id=flow.id,
                            flow_date=str(flow.date),
                            fii_buy_cr=flow.fii_buy_cr,
                            fii_sell_cr=flow.fii_sell_cr,
                            dii_buy_cr=flow.dii_buy_cr,
                            dii_sell_cr=flow.dii_sell_cr,
                            market_regime=flow.market_regime.value,
                        )
                    )
                    await self._session.flush()
            except IntegrityError:
                existing = (await self._session.execute(existing_stmt)).scalar_one_or_none()
                if existing:
                    existing.fii_buy_cr = flow.fii_buy_cr
                    existing.fii_sell_cr = flow.fii_sell_cr
                    existing.dii_buy_cr = flow.dii_buy_cr
                    existing.dii_sell_cr = flow.dii_sell_cr
                    existing.market_regime = flow.market_regime.value
                    await self._session.flush()
        return flow

    async def get_institutional_flows(self, *, days: int = 30) -> list[InstitutionalFlow]:
        from datetime import date, timedelta

        cutoff = str(date.today() - timedelta(days=days))
        stmt = (
            select(InstitutionalFlowTable)
            .where(InstitutionalFlowTable.flow_date >= cutoff)
            .order_by(InstitutionalFlowTable.flow_date.asc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            InstitutionalFlow(
                id=r.id,
                date=__import__("datetime").date.fromisoformat(r.flow_date),
                fii_buy_cr=r.fii_buy_cr,
                fii_sell_cr=r.fii_sell_cr,
                dii_buy_cr=r.dii_buy_cr,
                dii_sell_cr=r.dii_sell_cr,
                market_regime=MarketRegime(r.market_regime),
            )
            for r in rows
        ]

    # Smart Money
    async def save_smart_money_signal(self, signal: SmartMoneySignal) -> SmartMoneySignal:
        from sqlalchemy.exc import IntegrityError

        existing = await self.get_smart_money_signal(signal.ticker)
        if existing:
            stmt_get = (
                select(SmartMoneySignalTable)
                .where(SmartMoneySignalTable.ticker == signal.ticker)
                .limit(1)
            )
            row = (await self._session.execute(stmt_get)).scalar_one_or_none()
            if row:
                row.accumulation_score = signal.accumulation_score
                row.distribution_score = signal.distribution_score
                row.conviction_level = signal.conviction_level.value
                row.divergence_alerts_json = json.dumps(signal.divergence_alerts)
                row.evidence_json = json.dumps(
                    [{"desc": e.description, "weight": e.weight, "pos": e.is_positive}
                     for e in signal.evidence]
                )
                row.timestamp = signal.timestamp
                await self._session.flush()
        else:
            try:
                async with self._session.begin_nested():
                    self._session.add(
                        SmartMoneySignalTable(
                            id=signal.id,
                            ticker=signal.ticker,
                            company_name=signal.company_name,
                            accumulation_score=signal.accumulation_score,
                            distribution_score=signal.distribution_score,
                            conviction_level=signal.conviction_level.value,
                            divergence_alerts_json=json.dumps(signal.divergence_alerts),
                            evidence_json=json.dumps(
                                [{"desc": e.description, "weight": e.weight, "pos": e.is_positive}
                                 for e in signal.evidence]
                            ),
                            timestamp=signal.timestamp,
                        )
                    )
                    await self._session.flush()
            except IntegrityError:
                stmt_get = (
                    select(SmartMoneySignalTable)
                    .where(SmartMoneySignalTable.ticker == signal.ticker)
                    .limit(1)
                )
                row = (await self._session.execute(stmt_get)).scalar_one_or_none()
                if row:
                    row.accumulation_score = signal.accumulation_score
                    row.distribution_score = signal.distribution_score
                    row.conviction_level = signal.conviction_level.value
                    row.divergence_alerts_json = json.dumps(signal.divergence_alerts)
                    row.evidence_json = json.dumps(
                        [{"desc": e.description, "weight": e.weight, "pos": e.is_positive}
                         for e in signal.evidence]
                    )
                    row.timestamp = signal.timestamp
                    await self._session.flush()
        return signal

    async def get_smart_money_signal(self, ticker: str) -> SmartMoneySignal | None:
        stmt = (
            select(SmartMoneySignalTable)
            .where(SmartMoneySignalTable.ticker == ticker)
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if not row:
            return None
        evidence_data = json.loads(row.evidence_json)
        return SmartMoneySignal(
            id=row.id,
            ticker=row.ticker,
            company_name=row.company_name,
            accumulation_score=row.accumulation_score,
            distribution_score=row.distribution_score,
            conviction_level=ConvictionLevel(row.conviction_level),
            divergence_alerts=json.loads(row.divergence_alerts_json),
            evidence=[
                EvidenceFactor(
                    description=e["desc"],
                    weight=e["weight"],
                    is_positive=e["pos"],
                )
                for e in evidence_data
            ],
            timestamp=row.timestamp,
        )


# ------------------------------------------------------------------ #
# IPO Repository                                                       #
# ------------------------------------------------------------------ #


class IPORepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_row(self, ipo: IPO) -> IPOTable:
        financials_dict = {
            "revenue": ipo.financials.revenue,
            "revenue_growth_yoy": ipo.financials.revenue_growth_yoy,
            "net_profit": ipo.financials.net_profit,
            "net_profit_margin": ipo.financials.net_profit_margin,
            "ebitda_margin": ipo.financials.ebitda_margin,
            "debt_to_equity": ipo.financials.debt_to_equity,
            "roe": ipo.financials.roe,
            "cash_flow_from_operations": ipo.financials.cash_flow_from_operations,
            "pe_ratio": ipo.financials.pe_ratio,
            "ev_to_ebitda": ipo.financials.ev_to_ebitda,
            "fresh_issue_cr": ipo.fresh_issue_cr,
            "ofs_cr": ipo.ofs_cr,
        }
        score_dict = {}
        if ipo.score:
            score_dict = {
                "revenue_growth_score": ipo.score.revenue_growth_score,
                "profitability_score": ipo.score.profitability_score,
                "debt_score": ipo.score.debt_score,
                "valuation_score": ipo.score.valuation_score,
                "sector_trend_score": ipo.score.sector_trend_score,
                "gmp_score": ipo.score.gmp_score,
            }
        return IPOTable(
            id=ipo.id,
            name=ipo.name,
            ticker=ipo.ticker,
            status=ipo.status.value,
            sector=ipo.sector,
            industry=ipo.industry,
            ipo_type=ipo.ipo_type,
            price_band_low=ipo.price_band_low,
            price_band_high=ipo.price_band_high,
            lot_size=ipo.lot_size,
            issue_size_cr=ipo.issue_size_cr,
            gmp=ipo.gmp,
            subscription_overall=ipo.subscription_overall,
            subscription_qib=ipo.subscription_qib,
            subscription_hni=ipo.subscription_hni,
            subscription_retail=ipo.subscription_retail,
            open_date=str(ipo.open_date) if ipo.open_date else None,
            close_date=str(ipo.close_date) if ipo.close_date else None,
            listing_date=str(ipo.listing_date) if ipo.listing_date else None,
            financials_json=json.dumps(financials_dict),
            score_json=json.dumps(score_dict),
            listing_price=ipo.listing_price,
            listing_gain_pct=ipo.listing_gain_pct,
        )

    def _to_domain(self, row: IPOTable) -> IPO:
        from datetime import date
        findata = json.loads(row.financials_json)
        financials = IPOFinancials(
            revenue=findata.get("revenue", 0.0),
            revenue_growth_yoy=findata.get("revenue_growth_yoy", 0.0),
            net_profit=findata.get("net_profit", 0.0),
            net_profit_margin=findata.get("net_profit_margin", 0.0),
            ebitda_margin=findata.get("ebitda_margin", 0.0),
            debt_to_equity=findata.get("debt_to_equity", 0.0),
            roe=findata.get("roe", 0.0),
            cash_flow_from_operations=findata.get("cash_flow_from_operations", 0.0),
            pe_ratio=findata.get("pe_ratio", 0.0),
            ev_to_ebitda=findata.get("ev_to_ebitda", 0.0),
        )
        score = None
        sdata = json.loads(row.score_json)
        if sdata:
            score = IPOScore(
                revenue_growth_score=sdata.get("revenue_growth_score", 0.0),
                profitability_score=sdata.get("profitability_score", 0.0),
                debt_score=sdata.get("debt_score", 0.0),
                valuation_score=sdata.get("valuation_score", 0.0),
                sector_trend_score=sdata.get("sector_trend_score", 0.0),
                gmp_score=sdata.get("gmp_score", 0.0),
            )
        return IPO(
            id=row.id,
            name=row.name,
            ticker=row.ticker,
            status=IPOStatus(row.status),
            sector=row.sector,
            industry=row.industry,
            ipo_type=row.ipo_type if hasattr(row, "ipo_type") and row.ipo_type else "mainboard",
            price_band_low=row.price_band_low,
            price_band_high=row.price_band_high,
            lot_size=row.lot_size,
            issue_size_cr=row.issue_size_cr,
            fresh_issue_cr=findata.get("fresh_issue_cr", 0.0),
            ofs_cr=findata.get("ofs_cr", 0.0),
            open_date=date.fromisoformat(row.open_date) if row.open_date else None,
            close_date=date.fromisoformat(row.close_date) if row.close_date else None,
            listing_date=date.fromisoformat(row.listing_date) if row.listing_date else None,
            gmp=row.gmp,
            subscription_overall=row.subscription_overall,
            subscription_qib=row.subscription_qib,
            subscription_hni=row.subscription_hni,
            subscription_retail=row.subscription_retail,
            financials=financials,
            score=score,
            listing_price=row.listing_price,
            listing_gain_pct=row.listing_gain_pct,
        )

    async def save(self, ipo: IPO) -> IPO:
        existing = await self.get_by_id(ipo.id)
        if existing:
            # Overwrite existing
            row = await self._session.get(IPOTable, ipo.id)
            if row:
                # update fields
                new_row = self._to_row(ipo)
                row.name = new_row.name
                row.ticker = new_row.ticker
                row.status = new_row.status
                row.sector = new_row.sector
                row.industry = new_row.industry
                row.ipo_type = new_row.ipo_type
                row.price_band_low = new_row.price_band_low
                row.price_band_high = new_row.price_band_high
                row.lot_size = new_row.lot_size
                row.issue_size_cr = new_row.issue_size_cr
                row.gmp = new_row.gmp
                row.subscription_overall = new_row.subscription_overall
                row.subscription_qib = new_row.subscription_qib
                row.subscription_hni = new_row.subscription_hni
                row.subscription_retail = new_row.subscription_retail
                row.open_date = new_row.open_date
                row.close_date = new_row.close_date
                row.listing_date = new_row.listing_date
                row.financials_json = new_row.financials_json
                row.score_json = new_row.score_json
                row.listing_price = new_row.listing_price
                row.listing_gain_pct = new_row.listing_gain_pct
        else:
            self._session.add(self._to_row(ipo))
        await self._session.flush()
        return ipo

    async def get_all(self) -> list[IPO]:
        stmt = select(IPOTable).order_by(IPOTable.name)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def get_by_status(self, status: str) -> list[IPO]:
        stmt = select(IPOTable).where(IPOTable.status == status).order_by(IPOTable.name)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def get_by_id(self, ipo_id: str) -> IPO | None:
        row = await self._session.get(IPOTable, ipo_id)
        return self._to_domain(row) if row else None

    async def delete(self, ipo_id: str) -> bool:
        row = await self._session.get(IPOTable, ipo_id)
        if row:
            await self._session.delete(row)
            await self._session.flush()
            return True
        return False


# ------------------------------------------------------------------ #
# Risk Alert Repository                                                #
# ------------------------------------------------------------------ #


class RiskAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_row(self, alert: RiskAlert) -> RiskAlertTable:
        return RiskAlertTable(
            id=alert.id,
            ticker=alert.ticker,
            company_name=alert.company_name,
            factor=alert.factor.value,
            severity=alert.severity.value,
            description=alert.description,
            evidence_json=json.dumps(alert.supporting_evidence),
            source=alert.source,
            timestamp=alert.timestamp,
        )

    def _to_domain(self, row: RiskAlertTable) -> RiskAlert:
        return RiskAlert(
            id=row.id,
            ticker=row.ticker,
            company_name=row.company_name,
            factor=RiskFactor(row.factor),
            severity=RiskSeverity(row.severity),
            description=row.description,
            supporting_evidence=json.loads(row.evidence_json),
            source=row.source,
            timestamp=row.timestamp,
        )

    async def save(self, alert: RiskAlert) -> RiskAlert:
        self._session.add(self._to_row(alert))
        await self._session.flush()
        return alert

    async def get_recent(self, *, limit: int = 50) -> list[RiskAlert]:
        stmt = select(RiskAlertTable).order_by(RiskAlertTable.timestamp.desc()).limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def get_for_ticker(self, ticker: str) -> list[RiskAlert]:
        stmt = (
            select(RiskAlertTable)
            .where(RiskAlertTable.ticker == ticker)
            .order_by(RiskAlertTable.timestamp.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]


# ------------------------------------------------------------------ #
# Lead Repository                                                      #
# ------------------------------------------------------------------ #


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_row(self, lead: AlphaLead) -> LeadTable:
        return LeadTable(
            id=lead.id,
            ticker=lead.ticker,
            company_name=lead.company_name,
            action=lead.action.value,
            conviction=lead.conviction,
            expected_move_pct=lead.expected_move_pct,
            trigger_event_id=lead.trigger_event_id,
            trigger_event_title=lead.trigger_event_title,
            reasoning_json=json.dumps(lead.reasoning),
            signals_json=json.dumps(lead.signals),
            sector=lead.sector,
            key_voice=lead.key_voice,
            expires_at=lead.expires_at,
            timestamp=lead.timestamp,
        )

    def _to_domain(self, row: LeadTable) -> AlphaLead:
        return AlphaLead(
            id=row.id,
            ticker=row.ticker,
            company_name=row.company_name,
            action=LeadAction(row.action),
            conviction=row.conviction,
            expected_move_pct=row.expected_move_pct,
            trigger_event_id=row.trigger_event_id,
            trigger_event_title=row.trigger_event_title,
            reasoning=json.loads(row.reasoning_json) if row.reasoning_json else [],
            signals=json.loads(row.signals_json) if row.signals_json else {},
            sector=row.sector,
            key_voice=row.key_voice,
            expires_at=row.expires_at,
            timestamp=row.timestamp,
        )

    async def save(self, lead: AlphaLead) -> AlphaLead:
        self._session.add(self._to_row(lead))
        await self._session.flush()
        return lead

    async def get_active(self, *, limit: int = 20) -> list[AlphaLead]:
        now = datetime.utcnow()
        stmt = (
            select(LeadTable)
            .where(LeadTable.expires_at > now)
            .order_by(LeadTable.conviction.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def get_by_ticker(self, ticker: str) -> list[AlphaLead]:
        now = datetime.utcnow()
        stmt = (
            select(LeadTable)
            .where(LeadTable.ticker == ticker, LeadTable.expires_at > now)
            .order_by(LeadTable.conviction.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(r) for r in rows]

    async def expire_stale(self) -> int:
        now = datetime.utcnow()
        stmt = delete(LeadTable).where(LeadTable.expires_at <= now)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

