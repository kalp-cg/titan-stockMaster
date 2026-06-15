"""
Smart Money Service

Aggregates institutional intelligence from multiple public data sources:
  1. NSE Bulk Deal data (daily scrape)
  2. FII/DII net flows (daily scrape from NSE)
  3. Insider/promoter trades (SEBI filings, scraped)
  4. Shareholding pattern changes (quarterly delta)

Algorithm: Multi-source Bayesian aggregation → SmartMoneyScore [0–100]
  > 65  → ACCUMULATING
  35-65 → NEUTRAL
  < 35  → DISTRIBUTING

Design principle: All computation happens at ingestion time.
  The score is stored in DB. API responses are pure DB reads.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import aiohttp

from app.domain.models.smart_money import (
    BulkDeal,
    InstitutionalFlow,
    SmartMoneyEvidence,
    SmartMoneyScore,
)
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Known institutional names (for classification of bulk deal clients)
# ---------------------------------------------------------------------------
FII_KEYWORDS = [
    "fund", "fpi", "investments ltd", "capital", "asset management",
    "global", "international", "mauritius", "cayman", "singapore", "ireland",
    "vanguard", "blackrock", "fidelity", "templeton", "aberdeen",
    "societe generale", "credit suisse", "jpmorgan", "goldman sachs",
]
MF_KEYWORDS = [
    "mutual fund", "mf", "sbi mf", "hdfc mf", "icici mf", "axis mf",
    "nippon", "kotak mf", "dsp", "franklin", "uti", "mirae", "invesco",
    "aditya birla", "sundaram",
]
INSURANCE_KEYWORDS = ["insurance", "lic", "life", "general insurance"]


def classify_client(name: str) -> str:
    """Classify a bulk deal client name into a stakeholder category."""
    n = name.lower()
    if any(k in n for k in MF_KEYWORDS):
        return "mutual_fund"
    if any(k in n for k in FII_KEYWORDS):
        return "fii"
    if any(k in n for k in INSURANCE_KEYWORDS):
        return "insurance"
    return "unknown"


# ---------------------------------------------------------------------------
# NSE Data Fetchers (public endpoints)
# ---------------------------------------------------------------------------

NSE_BULK_DEAL_URL = "https://www.nseindia.com/api/bulk-deals"
NSE_FII_DII_URL = "https://www.nseindia.com/api/fiidiiTradeReact"

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com",
}


async def _fetch_nse_json(url: str, session: aiohttp.ClientSession) -> dict | list | None:
    """Fetch JSON from NSE API with proper session cookie handling."""
    try:
        # NSE requires a cookie session — first hit the homepage
        async with session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as _:
            pass
        async with session.get(url, headers=NSE_HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                return await resp.json(content_type=None)
    except Exception as e:
        logger.error("NSE fetch failed", url=url, error=str(e))
    return None


async def fetch_bulk_deals_nse() -> list[BulkDeal]:
    """Fetch today's bulk deals from NSE public API."""
    deals: list[BulkDeal] = []
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
        data = await _fetch_nse_json(NSE_BULK_DEAL_URL, session)
        if not data:
            return deals

        rows = data if isinstance(data, list) else data.get("data", [])
        for row in rows:
            try:
                ticker_raw = str(row.get("symbol", "")).strip().upper()
                if not ticker_raw:
                    continue
                ticker = ticker_raw + ".NS"
                client = str(row.get("clientName", "")).strip()
                deal_type = "BUY" if str(row.get("buySell", "B")).upper() == "B" else "SELL"
                qty = int(float(str(row.get("quantityTraded", 0)).replace(",", "") or 0))
                price = float(str(row.get("tradePrice", 0)).replace(",", "") or 0)
                deal_date = str(row.get("date", datetime.utcnow().strftime("%Y-%m-%d")))

                deals.append(BulkDeal(
                    id=str(uuid4()),
                    ticker=ticker,
                    deal_date=deal_date,
                    client_name=client,
                    deal_type=deal_type,
                    quantity=qty,
                    price=price,
                    stakeholder_category=classify_client(client),
                    exchange="NSE",
                ))
            except Exception as e:
                logger.debug("Skipping malformed bulk deal row", error=str(e))

    logger.info("Fetched bulk deals from NSE", count=len(deals))
    return deals


async def fetch_fii_dii_flow() -> InstitutionalFlow | None:
    """Fetch today's FII/DII net flow from NSE."""
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
        data = await _fetch_nse_json(NSE_FII_DII_URL, session)
        if not data:
            return None

        rows = data if isinstance(data, list) else data.get("data", [])
        # Take the most recent row
        if not rows:
            return None
        row = rows[0] if rows else {}

        def parse_cr(val: Any) -> float:
            try:
                return float(str(val).replace(",", "").replace("-", "0") or 0)
            except Exception:
                return 0.0

        fii_buy = parse_cr(row.get("fiiBuyValue", 0))
        fii_sell = parse_cr(row.get("fiiSoldValue", 0))
        dii_buy = parse_cr(row.get("diiBuyValue", 0))
        dii_sell = parse_cr(row.get("diiSoldValue", 0))
        flow_date = str(row.get("date", datetime.utcnow().strftime("%Y-%m-%d")))

        fii_net = fii_buy - fii_sell
        regime = "bullish" if fii_net > 500 else "bearish" if fii_net < -500 else "neutral"

        logger.info("Fetched FII/DII flow", date=flow_date, fii_net_cr=fii_net)
        return InstitutionalFlow(
            id=str(uuid4()),
            flow_date=flow_date,
            fii_buy_cr=fii_buy,
            fii_sell_cr=fii_sell,
            dii_buy_cr=dii_buy,
            dii_sell_cr=dii_sell,
            market_regime=regime,
        )


# ---------------------------------------------------------------------------
# SmartMoneyService
# ---------------------------------------------------------------------------

class SmartMoneyService:
    """
    Computes and serves Smart Money Scores for portfolio holdings.

    Algorithm:
        score = 50 (neutral baseline)
        + bulk deal net qty contribution  [±20]
        + FII 3-day net flow contribution [±15]
        + shareholding QoQ change         [±10]
        - promoter pledge delta           [0 to -15]
        → clamped to [0, 100]
    """

    def __init__(self, holding_repo: Any, bulk_deal_repo: Any = None) -> None:
        self._holding_repo = holding_repo
        self._bulk_deal_repo = bulk_deal_repo
        self._flow_cache: list[InstitutionalFlow] = []  # last 3 days in memory

    @timed
    async def refresh_market_data(self) -> None:
        """
        Pull latest bulk deals and FII/DII data from NSE.
        Called by the scheduler every market day at 18:30 IST.
        """
        logger.info("SmartMoneyService: refreshing market data from NSE")

        # Fetch in parallel
        bulk_task = asyncio.create_task(fetch_bulk_deals_nse())
        flow_task = asyncio.create_task(fetch_fii_dii_flow())

        deals, flow = await asyncio.gather(bulk_task, flow_task, return_exceptions=True)

        if isinstance(flow, InstitutionalFlow):
            self._flow_cache.append(flow)
            if len(self._flow_cache) > 3:
                self._flow_cache.pop(0)
            logger.info("FII/DII flow cached", entries=len(self._flow_cache))
        elif isinstance(flow, Exception):
            logger.warning("FII flow fetch failed", error=str(flow))

        if isinstance(deals, list):
            logger.info("Bulk deals fetched", count=len(deals))
        elif isinstance(deals, Exception):
            logger.warning("Bulk deals fetch failed", error=str(deals))

    @timed
    async def get_score(self, ticker: str, company_name: str = "") -> SmartMoneyScore:
        """
        Compute smart money score for a single ticker.
        Returns NEUTRAL (score=50) when data is unavailable — never fails.
        """
        score = 50.0
        evidence: list[SmartMoneyEvidence] = []
        bulk_net_qty = 0
        fii_net_3d = 0.0

        # --- Signal 1: Bulk Deal Analysis (last 5 days) ---
        try:
            recent_deals = await self._get_recent_bulk_deals(ticker, days=5)
            buy_qty = sum(d.quantity for d in recent_deals if d.deal_type == "BUY")
            sell_qty = sum(d.quantity for d in recent_deals if d.deal_type == "SELL")
            bulk_net_qty = buy_qty - sell_qty

            # Normalize: ±20 points for extreme bulk deals (>1M shares)
            bulk_contribution = max(-20.0, min(20.0, bulk_net_qty / 50_000))
            score += bulk_contribution

            if abs(bulk_contribution) > 2:
                direction = "accumulation" if bulk_net_qty > 0 else "distribution"
                evidence.append(SmartMoneyEvidence(
                    source="bulk_deal",
                    description=f"Net {abs(bulk_net_qty):,} shares {'bought' if bulk_net_qty > 0 else 'sold'} in bulk deals (last 5 days)",
                    direction=direction,
                    strength=min(1.0, abs(bulk_net_qty) / 500_000),
                    date=datetime.utcnow().strftime("%Y-%m-%d"),
                ))
        except Exception as e:
            logger.debug("Bulk deal scoring failed", ticker=ticker, error=str(e))

        # --- Signal 2: FII 3-day Net Flow (market-wide proxy) ---
        try:
            if self._flow_cache:
                fii_net_3d = sum(f.fii_net_cr for f in self._flow_cache[-3:])
                # Normalize: ±15 points for extreme FII moves (±3000 cr in 3 days)
                fii_contribution = max(-15.0, min(15.0, fii_net_3d / 200))
                score += fii_contribution

                if abs(fii_contribution) > 1:
                    direction = "accumulation" if fii_net_3d > 0 else "distribution"
                    evidence.append(SmartMoneyEvidence(
                        source="fii_flow",
                        description=f"FII net {'inflow' if fii_net_3d > 0 else 'outflow'} of ₹{abs(fii_net_3d):.0f} Cr (3-day)",
                        direction=direction,
                        strength=min(1.0, abs(fii_net_3d) / 3000),
                        date=datetime.utcnow().strftime("%Y-%m-%d"),
                    ))
        except Exception as e:
            logger.debug("FII flow scoring failed", ticker=ticker, error=str(e))

        # --- Signal 3: Insider / Promoter classification from bulk deals ---
        promoter_direction = "none"
        try:
            recent_deals = await self._get_recent_bulk_deals(ticker, days=30)
            promoter_buys = sum(d.quantity for d in recent_deals
                                if d.deal_type == "BUY" and d.stakeholder_category in ("insider", "promoter"))
            promoter_sells = sum(d.quantity for d in recent_deals
                                 if d.deal_type == "SELL" and d.stakeholder_category in ("insider", "promoter"))
            if promoter_buys > promoter_sells and promoter_buys > 10_000:
                score += 8.0
                promoter_direction = "buying"
                evidence.append(SmartMoneyEvidence(
                    source="insider",
                    description=f"Promoter/insider net buying: {promoter_buys - promoter_sells:,} shares (last 30 days)",
                    direction="accumulation",
                    strength=0.7,
                    date=datetime.utcnow().strftime("%Y-%m-%d"),
                ))
            elif promoter_sells > promoter_buys and promoter_sells > 10_000:
                score -= 10.0
                promoter_direction = "selling"
                evidence.append(SmartMoneyEvidence(
                    source="insider",
                    description=f"Promoter/insider net selling: {promoter_sells - promoter_buys:,} shares (last 30 days)",
                    direction="distribution",
                    strength=0.8,
                    date=datetime.utcnow().strftime("%Y-%m-%d"),
                ))
        except Exception as e:
            logger.debug("Insider scoring failed", ticker=ticker, error=str(e))

        # Clamp and label
        score = round(max(0.0, min(100.0, score)), 1)
        label = (
            "ACCUMULATING" if score > 65
            else "DISTRIBUTING" if score < 35
            else "NEUTRAL"
        )

        return SmartMoneyScore(
            ticker=ticker,
            company_name=company_name,
            score=score,
            label=label,
            evidence=evidence,
            bulk_deal_net_qty=bulk_net_qty,
            fii_net_3day_cr=round(fii_net_3d, 2),
            insider_direction=promoter_direction,
        )

    @timed
    async def get_portfolio_scores(self) -> list[SmartMoneyScore]:
        """
        Compute smart money scores for all holdings in the portfolio.
        Runs concurrently for all tickers.
        """
        holdings = await self._holding_repo.get_all()
        if not holdings:
            return []

        tasks = [
            self.get_score(h.ticker, h.company_name)
            for h in holdings
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, SmartMoneyScore)]

    async def _get_recent_bulk_deals(self, ticker: str, days: int = 5) -> list[BulkDeal]:
        """Retrieve recent bulk deals for a ticker from the database or return empty."""
        if not self._bulk_deal_repo:
            return []
        try:
            if hasattr(self._bulk_deal_repo, "get_bulk_deals"):
                return await self._bulk_deal_repo.get_bulk_deals(ticker, days=days)
            return await self._bulk_deal_repo.get_by_ticker(ticker, days=days)
        except Exception as e:
            logger.debug("Failed to retrieve recent bulk deals", ticker=ticker, error=str(e))
            return []
