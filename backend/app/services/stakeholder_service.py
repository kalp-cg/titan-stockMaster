"""Stakeholder intelligence service.

Manages corporate filings data (shareholding patterns, bulk/block deals, insider trades, flows)
and calculates composite Smart Money conviction levels and alerts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.domain.interfaces.repository import IStakeholderRepository
from app.domain.interfaces.stakeholder_provider import IStakeholderDataProvider
from app.domain.models.stakeholder import (
    BlockDeal,
    BulkDeal,
    ConvictionLevel,
    DealType,
    EvidenceFactor,
    InsiderTrade,
    InstitutionalFlow,
    ShareholdingPattern,
    SmartMoneySignal,
    StakeholderCategory,
    InstitutionalHolder,
)
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


class StakeholderService:
    """Orchestrates SEBI/NSE corporate files and smart money signals."""

    def __init__(
        self,
        repository: IStakeholderRepository,
        provider: IStakeholderDataProvider,
        market_provider: Any = None,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._market_provider = market_provider
        self._company_name_cache: dict[str, str] = {}

    @timed
    async def refresh_all_stakeholders(self) -> None:
        logger.info("Starting stakeholder data refresh cycle")
        from app.config import get_settings

        settings = get_settings()

        try:
            flows = await self._provider.get_institutional_flows(days=5)
            for f in flows:
                await self._repository.save_institutional_flow(f)
        except Exception as e:
            logger.error("Failed to refresh institutional flows", error=str(e))

        for ticker in settings.MARKET_TICKERS:
            if ticker.startswith("^") or ticker.startswith("GC=") or ticker.startswith("CL="):
                continue
            try:
                history = await self._provider.get_shareholding_history(ticker, quarters=4)
                for pattern in history:
                    await self._repository.save_shareholding(pattern)

                deals = await self._provider.get_bulk_deals(ticker, days=7)
                for d in deals:
                    await self._repository.save_bulk_deal(d)

                trades = await self._provider.get_insider_trades(ticker, days=30)
                for t in trades:
                    await self._repository.save_insider_trade(t)

                await self.compute_smart_money_signal(ticker)

            except Exception as e:
                logger.error("Failed to refresh stakeholder details", ticker=ticker, error=str(e))

        logger.info("Stakeholder data refresh cycle complete")

    async def _enrich_shareholding_pattern(self, pattern: ShareholdingPattern | None) -> ShareholdingPattern | None:
        if not pattern:
            return None
        
        # Estimate total shares outstanding
        total_shares = 500_000_000
        current_price = 100.0
        
        if self._market_provider:
            try:
                # 1. Fetch current price
                price_dict = await self._market_provider.get_prices([pattern.ticker])
                if price_dict and pattern.ticker in price_dict:
                    current_price = price_dict[pattern.ticker].price or price_dict[pattern.ticker].close or 100.0
                
                # 2. Fetch company info for market cap
                company = await self._market_provider.get_company_info(pattern.ticker)
                if company and company.market_cap > 0 and company.current_price > 0:
                    total_shares = int(company.market_cap / company.current_price)
            except Exception as e:
                logger.debug("Failed to fetch market details for stakeholder enrichment", ticker=pattern.ticker, error=str(e))
        
        # Fallback dictionary of outstanding shares for common Indian tickers
        fallback_shares = {
            "RELIANCE.NS": 6760000000,
            "TCS.NS": 3660000000,
            "INFY.NS": 4150000000,
            "HDFCBANK.NS": 7590000000,
            "ICICIBANK.NS": 6980000000,
            "SBIN.NS": 8920000000,
            "KOTAKBANK.NS": 1980000000,
            "AXISBANK.NS": 3080000000,
            "BAJFINANCE.NS": 620000000,
            "HINDUNILVR.NS": 2350000000,
            "ITC.NS": 12480000000,
            "NESTLEIND.NS": 960000000,
            "MARUTI.NS": 310000000,
            "TITAN.NS": 890000000,
            "LT.NS": 1400000000,
            "ULTRACEMCO.NS": 290000000,
            "ASIANPAINT.NS": 960000000,
            "SUNPHARMA.NS": 2400000000,
            "HAL.NS": 670000000,
            "BEL.NS": 730000000,
            "INDIGO.NS": 390000000,
            "TATASTEEL.NS": 12480000000,
            "BHARTIARTL.NS": 5600000000,
        }
        if total_shares == 500_000_000 and pattern.ticker in fallback_shares:
            total_shares = fallback_shares[pattern.ticker]
            
        # Ensure promoter is in top holders list
        has_promoter = any(h.category == StakeholderCategory.PROMOTER or (isinstance(h.category, str) and h.category == "promoter") for h in pattern.top_holders)
        if not has_promoter and pattern.promoter_pct > 0:
            promoters_names = {
                "RELIANCE.NS": "Ambani Family (Promoters)",
                "TCS.NS": "Tata Sons Private Limited (Promoters)",
                "INFY.NS": "Murthy & Founders Family (Promoters)",
                "HDFCBANK.NS": "HDFC Group (Promoters)",
                "ICICIBANK.NS": "ICICI Group (Promoters)",
                "SBIN.NS": "President of India (Government/Promoter)",
            }
            promoter_name = promoters_names.get(pattern.ticker.upper(), "Promoter Group & Founders")
            promoter_holder = InstitutionalHolder(
                name=promoter_name,
                category=StakeholderCategory.PROMOTER,
                holding_pct=pattern.promoter_pct,
                change_vs_prev_quarter=pattern.promoter_delta,
            )
            pattern.top_holders.insert(0, promoter_holder)

        # Enrich holders and filter to only show big ones (>= 1.0%)
        enriched_holders = []
        for h in pattern.top_holders:
            if h.holding_pct < 1.0:
                continue
            
            # Calculate shares held
            h.shares_held = int(total_shares * (h.holding_pct / 100.0))
            
            # Calculate profit: assume they bought at 15% discount
            avg_cost = current_price * 0.85
            # Profit in Crores
            h.profit_cr = round((h.shares_held * (current_price - avg_cost)) / 10_000_000, 2)
            
            # Add dynamically as a dictionary attribute so it serializes
            # Dataclasses serialize their __dict__ or attributes
            h.__dict__["profit_cr"] = h.profit_cr
            
            enriched_holders.append(h)
            
        pattern.top_holders = enriched_holders
        return pattern

    async def get_shareholding_pattern(self, ticker: str) -> ShareholdingPattern | None:
        ticker = ticker.upper()
        pattern = await self._repository.get_shareholding(ticker)
        if not pattern:
            try:
                logger.info("Stakeholder pattern not found in DB, fetching dynamically", ticker=ticker)
                history = await self._provider.get_shareholding_history(ticker, quarters=4)
                for pat in history:
                    await self._repository.save_shareholding(pat)
                
                deals = await self._provider.get_bulk_deals(ticker, days=30)
                for d in deals:
                    await self._repository.save_bulk_deal(d)
                    
                trades = await self._provider.get_insider_trades(ticker, days=90)
                for t in trades:
                    await self._repository.save_insider_trade(t)
                    
                pattern = await self._repository.get_shareholding(ticker)
            except Exception as e:
                logger.error("Failed to dynamically fetch stakeholder details", ticker=ticker, error=str(e))
        return await self._enrich_shareholding_pattern(pattern)

    async def get_shareholding_history(
        self, ticker: str, quarters: int = 8
    ) -> list[ShareholdingPattern]:
        ticker = ticker.upper()
        history = await self._repository.get_shareholding_history(ticker, quarters=quarters)
        if not history:
            await self.get_shareholding_pattern(ticker)
            history = await self._repository.get_shareholding_history(ticker, quarters=quarters)
            
        enriched_history = []
        for pat in history:
            enriched = await self._enrich_shareholding_pattern(pat)
            if enriched:
                enriched_history.append(enriched)
        return enriched_history

    async def get_bulk_deals(self, ticker: str | None, days: int = 30) -> list[BulkDeal]:
        if ticker:
            ticker = ticker.upper()
            has_sh = await self._repository.get_shareholding(ticker)
            if not has_sh:
                await self.get_shareholding_pattern(ticker)
        return await self._repository.get_bulk_deals(ticker, days=days)

    async def get_insider_trades(self, ticker: str | None, days: int = 90) -> list[InsiderTrade]:
        if ticker:
            ticker = ticker.upper()
            has_sh = await self._repository.get_shareholding(ticker)
            if not has_sh:
                await self.get_shareholding_pattern(ticker)
        return await self._repository.get_insider_trades(ticker, days=days)

    async def get_institutional_flows(self, days: int = 30) -> list[InstitutionalFlow]:
        return await self._repository.get_institutional_flows(days=days)

    async def get_smart_money_signal(self, ticker: str) -> SmartMoneySignal | None:
        ticker = ticker.upper()
        signal = await self._repository.get_smart_money_signal(ticker)
        if not signal:
            signal = await self.compute_smart_money_signal(ticker)
        return signal

    @timed
    async def compute_smart_money_signal(
        self, ticker: str, company_name: str | None = None
    ) -> SmartMoneySignal:
        logger.debug("Computing Smart Money Signal", ticker=ticker)

        pattern = await self.get_shareholding_pattern(ticker)
        insiders = await self.get_insider_trades(ticker, days=90)
        bulk_deals = await self.get_bulk_deals(ticker, days=90)

        if not company_name:
            company_name = self._company_name_cache.get(ticker)
            if not company_name:
                company_name = ticker
                if self._market_provider:
                    try:
                        info = await self._market_provider.get_company_info(ticker)
                        company_name = info.name
                        self._company_name_cache[ticker] = company_name
                    except Exception:
                        pass
        else:
            self._company_name_cache[ticker] = company_name

        evidence = []
        acc_score = 0.0
        dist_score = 0.0
        divergences = []

        if pattern:
            if pattern.fii_delta > 0:
                fii_w = min(1.0, pattern.fii_delta * 0.4)
                acc_score += fii_w * 0.3
                evidence.append(
                    EvidenceFactor(
                        description=f"FIIs accumulated +{pattern.fii_delta:.2f}% shares",
                        weight=fii_w,
                        is_positive=True,
                    )
                )
            elif pattern.fii_delta < 0:
                fii_w = min(1.0, abs(pattern.fii_delta) * 0.4)
                dist_score += fii_w * 0.3
                evidence.append(
                    EvidenceFactor(
                        description=f"FIIs sold {pattern.fii_delta:.2f}% shares",
                        weight=fii_w,
                        is_positive=False,
                    )
                )

            if pattern.dii_delta > 0:
                dii_w = min(1.0, pattern.dii_delta * 0.4)
                acc_score += dii_w * 0.25
                evidence.append(
                    EvidenceFactor(
                        description=f"DIIs accumulated +{pattern.dii_delta:.2f}% shares",
                        weight=dii_w,
                        is_positive=True,
                    )
                )
            elif pattern.dii_delta < 0:
                dii_w = min(1.0, abs(pattern.dii_delta) * 0.4)
                dist_score += dii_w * 0.25
                evidence.append(
                    EvidenceFactor(
                        description=f"DIIs sold {pattern.dii_delta:.2f}% shares",
                        weight=dii_w,
                        is_positive=False,
                    )
                )

            if pattern.promoter_pledge_pct > 10.0:
                pledge_w = min(1.0, pattern.promoter_pledge_pct / 50.0)
                dist_score += pledge_w * 0.2
                evidence.append(
                    EvidenceFactor(
                        description=f"Promoters pledged {pattern.promoter_pledge_pct}% shares",
                        weight=pledge_w,
                        is_positive=False,
                    )
                )

        insider_buys = 0.0
        insider_sells = 0.0
        for t in insiders:
            if t.trade_type == DealType.BUY:
                insider_buys += t.total_value
            elif t.trade_type == DealType.SELL:
                insider_sells += t.total_value

        if insider_buys > 0:
            buy_w = min(1.0, insider_buys / 10_000_000)
            acc_score += buy_w * 0.2
            evidence.append(
                EvidenceFactor(
                    description=f"Insiders purchased shares totaling ₹{insider_buys/1e5:.1f} Lakhs",
                    weight=buy_w,
                    is_positive=True,
                )
            )

        if insider_sells > 0:
            sell_w = min(1.0, insider_sells / 10_000_000)
            dist_score += sell_w * 0.2
            evidence.append(
                EvidenceFactor(
                    description=f"Insiders sold shares totaling ₹{insider_sells/1e5:.1f} Lakhs",
                    weight=sell_w,
                    is_positive=False,
                )
            )

        bulk_buys = 0.0
        bulk_sells = 0.0
        for d in bulk_deals:
            if d.deal_type == DealType.BUY:
                bulk_buys += d.total_value
            elif d.deal_type == DealType.SELL:
                bulk_sells += d.total_value

        if bulk_buys > 0:
            bulk_w = min(1.0, bulk_buys / 50_000_000)
            acc_score += bulk_w * 0.25
            evidence.append(
                EvidenceFactor(
                    description=f"Institutions executed bulk buys of ₹{bulk_buys/1e7:.1f} Cr",
                    weight=bulk_w,
                    is_positive=True,
                )
            )

        if bulk_sells > 0:
            bulk_w = min(1.0, bulk_sells / 50_000_000)
            dist_score += bulk_w * 0.25
            evidence.append(
                EvidenceFactor(
                    description=f"Institutions executed bulk sales of ₹{bulk_sells/1e7:.1f} Cr",
                    weight=bulk_w,
                    is_positive=False,
                )
            )

        acc_score = min(1.0, acc_score)
        dist_score = min(1.0, dist_score)

        if acc_score > 0.6 and dist_score > 0.6:
            divergences.append("Heavy institutional buying competing with insider dumping.")
        elif pattern and pattern.fii_delta > 1.0 and pattern.promoter_delta < -1.0:
            divergences.append("FIIs are accumulating while promoters are diluting.")

        diff = acc_score - dist_score
        if abs(diff) < 0.2:
            conviction = ConvictionLevel.LOW
        elif abs(diff) < 0.5:
            conviction = ConvictionLevel.MEDIUM
        else:
            conviction = ConvictionLevel.HIGH

        signal = SmartMoneySignal(
            ticker=ticker,
            company_name=company_name,
            accumulation_score=round(acc_score, 2),
            distribution_score=round(dist_score, 2),
            conviction_level=conviction,
            divergence_alerts=divergences,
            evidence=evidence,
            timestamp=datetime.utcnow(),
        )

        await self._repository.save_smart_money_signal(signal)
        return signal
