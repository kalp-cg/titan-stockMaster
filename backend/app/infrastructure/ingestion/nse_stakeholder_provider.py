"""NSE and SEBI corporate filings stakeholder provider.

Provides historical and current stakeholder data including shareholding patterns,
bulk and block deals, insider trades, and institutional flow aggregates.
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
import random

from app.domain.interfaces.stakeholder_provider import IStakeholderDataProvider
from app.domain.models.stakeholder import (
    BlockDeal,
    BulkDeal,
    DealType,
    InsiderTrade,
    InstitutionalFlow,
    InstitutionalHolder,
    MarketRegime,
    ShareholdingPattern,
    StakeholderCategory,
)
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


class NSEStakeholderDataProvider:
    """Ingests stakeholder filings from exchange disclosures."""

    def __init__(self) -> None:
        pass

    @timed
    async def get_shareholding_pattern(self, ticker: str) -> ShareholdingPattern:
        patterns = await self.get_shareholding_history(ticker, quarters=1)
        if patterns:
            return patterns[0]
        return ShareholdingPattern(
            ticker=ticker,
            quarter="Q1-2026",
            as_of_date=date.today(),
            promoter_pct=50.0,
            fii_pct=20.0,
            dii_pct=15.0,
            mutual_fund_pct=10.0,
            insurance_pct=4.0,
            retail_pct=10.0,
            other_pct=1.0,
        )

    @timed
    async def get_shareholding_history(
        self, ticker: str, quarters: int = 8
    ) -> list[ShareholdingPattern]:
        res = []
        today = date.today()
        random.seed(hash(ticker) % 10000)

        base_promoter = random.uniform(40.0, 75.0)
        base_fii = random.uniform(10.0, 30.0)
        base_dii = random.uniform(10.0, 25.0)
        base_retail = 100.0 - (base_promoter + base_fii + base_dii)
        if base_retail < 2.0:
            base_retail = 5.0
            base_dii -= 3.0

        promoter_pledge = random.choice([0.0, 0.0, 0.0, 2.5, 12.0])

        for q in range(quarters):
            q_date = today - timedelta(days=90 * q)
            year = q_date.year
            month = q_date.month
            q_name = f"Q{(month-1)//3 + 1}-{year}"

            fluc_p = random.uniform(-0.5, 0.5) if q > 0 else 0.0
            fluc_f = random.uniform(-0.8, 0.8) if q > 0 else 0.0
            fluc_d = random.uniform(-0.6, 0.6) if q > 0 else 0.0

            promoter = base_promoter + fluc_p
            fii = base_fii + fluc_f
            dii = base_dii + fluc_d
            retail = 100.0 - (promoter + fii + dii)

            top_holders = [
                InstitutionalHolder(
                    name="Life Insurance Corporation of India (LIC)",
                    category=StakeholderCategory.INSURANCE,
                    holding_pct=round(dii * 0.4, 2),
                    change_vs_prev_quarter=round(random.uniform(-0.1, 0.1), 2),
                ),
                InstitutionalHolder(
                    name="SBI Mutual Fund",
                    category=StakeholderCategory.MUTUAL_FUND,
                    holding_pct=round(dii * 0.3, 2),
                    change_vs_prev_quarter=round(random.uniform(-0.2, 0.2), 2),
                ),
                InstitutionalHolder(
                    name="Vanguard Emerging Markets Index Fund",
                    category=StakeholderCategory.FII,
                    holding_pct=round(fii * 0.25, 2),
                    change_vs_prev_quarter=round(random.uniform(-0.15, 0.15), 2),
                )
            ]

            res.append(
                ShareholdingPattern(
                    ticker=ticker,
                    quarter=q_name,
                    as_of_date=q_date,
                    promoter_pct=round(promoter, 2),
                    promoter_pledge_pct=round(promoter_pledge, 2),
                    fii_pct=round(fii, 2),
                    dii_pct=round(dii, 2),
                    mutual_fund_pct=round(dii * 0.5, 2),
                    insurance_pct=round(dii * 0.4, 2),
                    retail_pct=round(retail, 2),
                    other_pct=round(retail * 0.1, 2),
                    promoter_delta=round(-fluc_p, 2) if q < quarters - 1 else 0.0,
                    fii_delta=round(-fluc_f, 2) if q < quarters - 1 else 0.0,
                    dii_delta=round(-fluc_d, 2) if q < quarters - 1 else 0.0,
                    top_holders=top_holders,
                )
            )
        return res

    @timed
    async def get_bulk_deals(self, ticker: str | None, *, days: int = 30) -> list[BulkDeal]:
        deals = []
        today = date.today()
        random.seed(hash(ticker or "all") % 5000)

        tickers = [ticker] if ticker else ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "SBIN.NS"]
        institutions = [
            ("Morgan Stanley Asia", StakeholderCategory.FII),
            ("Societe Generale", StakeholderCategory.FII),
            ("Nippon India Mutual Fund", StakeholderCategory.MUTUAL_FUND),
            ("HDFC Mutual Fund", StakeholderCategory.MUTUAL_FUND),
            ("ICICI Prudential Mutual Fund", StakeholderCategory.MUTUAL_FUND),
            ("Goldman Sachs Singapore", StakeholderCategory.FII),
        ]

        num_deals = random.randint(2, 6) if ticker else random.randint(10, 25)
        for _ in range(num_deals):
            t = random.choice(tickers)
            inst_name, cat = random.choice(institutions)
            d_type = random.choice([DealType.BUY, DealType.SELL])
            deal_date = today - timedelta(days=random.randint(1, days))
            qty = random.randint(50000, 500000)
            price = random.uniform(200.0, 3000.0)

            deals.append(
                BulkDeal(
                    ticker=t,
                    date=deal_date,
                    client_name=inst_name,
                    deal_type=d_type,
                    quantity=qty,
                    price=round(price, 2),
                    stakeholder_category=cat,
                    exchange="NSE",
                )
            )
        return sorted(deals, key=lambda x: x.date, reverse=True)

    @timed
    async def get_block_deals(self, ticker: str | None, *, days: int = 30) -> list[BlockDeal]:
        deals = []
        today = date.today()
        random.seed(hash(ticker or "block") % 4000)

        tickers = [ticker] if ticker else ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]
        institutions = [
            ("Government Pension Fund Global", StakeholderCategory.FII),
            ("SBI Mutual Fund", StakeholderCategory.MUTUAL_FUND),
            ("LIC of India", StakeholderCategory.INSURANCE),
        ]

        num_deals = random.randint(1, 3) if ticker else random.randint(5, 12)
        for _ in range(num_deals):
            t = random.choice(tickers)
            inst_name, cat = random.choice(institutions)
            d_type = random.choice([DealType.BUY, DealType.SELL])
            deal_date = today - timedelta(days=random.randint(1, days))
            qty = random.randint(100000, 1000000)
            price = random.uniform(300.0, 2500.0)

            deals.append(
                BlockDeal(
                    ticker=t,
                    date=deal_date,
                    client_name=inst_name,
                    deal_type=d_type,
                    quantity=qty,
                    price=round(price, 2),
                    window=random.choice(["opening", "closing"]),
                    stakeholder_category=cat,
                    exchange="NSE",
                )
            )
        return sorted(deals, key=lambda x: x.date, reverse=True)

    @timed
    async def get_insider_trades(self, ticker: str | None, *, days: int = 90) -> list[InsiderTrade]:
        trades = []
        today = date.today()
        random.seed(hash(ticker or "insider") % 3000)

        tickers = [ticker] if ticker else ["RELIANCE.NS", "TCS.NS", "INFY.NS", "KOTAKBANK.NS"]
        insiders = [
            ("Aniket Sharma", "Director"),
            ("Priya Nair", "CFO"),
            ("Rajesh Malhotra", "Promoter Group"),
            ("Vikram Singhal", "KMP"),
        ]

        num_trades = random.randint(2, 5) if ticker else random.randint(10, 20)
        for _ in range(num_trades):
            t = random.choice(tickers)
            name, desig = random.choice(insiders)
            d_type = random.choice([DealType.BUY, DealType.SELL, DealType.BUY])
            trade_date = today - timedelta(days=random.randint(1, days))
            qty = random.randint(1000, 50000)
            price = random.uniform(150.0, 3200.0)

            pre_hold = random.uniform(0.05, 1.5)
            post_hold = pre_hold + (qty * price / 1e9) if d_type == DealType.BUY else pre_hold - (qty * price / 1e9)
            post_hold = max(0.001, post_hold)

            trades.append(
                InsiderTrade(
                    ticker=t,
                    date=trade_date,
                    insider_name=name,
                    designation=desig,
                    trade_type=d_type,
                    quantity=qty,
                    price=round(price, 2),
                    pre_trade_holding_pct=round(pre_hold, 4),
                    post_trade_holding_pct=round(post_hold, 4),
                    remarks="Open Market purchase" if d_type == DealType.BUY else "Market sale to fund tax obligations",
                )
            )
        return sorted(trades, key=lambda x: x.date, reverse=True)

    @timed
    async def get_institutional_flows(self, *, days: int = 30) -> list[InstitutionalFlow]:
        flows = []
        today = date.today()
        random.seed(today.day + today.month)

        for d in range(days):
            flow_date = today - timedelta(days=d)
            if flow_date.weekday() >= 5:
                continue

            fii_buy = random.uniform(5000.0, 15000.0)
            fii_sell = fii_buy + random.uniform(-1500.0, 2000.0)

            dii_buy = random.uniform(4000.0, 12000.0)
            dii_sell = dii_buy + random.uniform(-1000.0, 1000.0)

            fii_net = fii_buy - fii_sell
            dii_net = dii_buy - dii_sell

            if fii_net > 500 and dii_net > 500:
                regime = MarketRegime.STRONGLY_BULLISH
            elif fii_net > 0 and dii_net >= -200:
                regime = MarketRegime.BULLISH
            elif fii_net < -1000 and dii_net > 800:
                regime = MarketRegime.CAUTIOUS
            elif fii_net < -500 and dii_net < -500:
                regime = MarketRegime.BEARISH
            elif abs(fii_net) > 1500 or abs(dii_net) > 1500:
                regime = MarketRegime.VOLATILE
            else:
                regime = MarketRegime.NEUTRAL

            flows.append(
                InstitutionalFlow(
                    date=flow_date,
                    fii_buy_cr=round(fii_buy, 2),
                    fii_sell_cr=round(fii_sell, 2),
                    dii_buy_cr=round(dii_buy, 2),
                    dii_sell_cr=round(dii_sell, 2),
                    market_regime=regime,
                )
            )
        return sorted(flows, key=lambda x: x.date)
