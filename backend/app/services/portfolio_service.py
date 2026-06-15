"""Portfolio management service.

Handles positions CRUD, queries the market provider for live prices, calculates
exposures, and evaluates the risk/opportunity impacts of global events on holdings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from app.domain.interfaces.market_data import IMarketDataProvider
from app.domain.interfaces.repository import IEventRepository, IHoldingRepository
from app.domain.models.portfolio import (
    AffectedHolding,
    Holding,
    Portfolio,
    PortfolioImpact,
    SectorExposure,
)
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


class PortfolioService:
    """Manages holdings, calculates live P&L, exposure, and event impacts."""

    def __init__(
        self,
        holding_repository: IHoldingRepository,
        event_repository: IEventRepository,
        market_provider: IMarketDataProvider,
        impact_service: Any,
        knowledge_graph: Any = None,
    ) -> None:
        self._holding_repo = holding_repository
        self._event_repo = event_repository
        self._market_provider = market_provider
        self._impact_service = impact_service
        self._graph = knowledge_graph

    @timed
    async def get_portfolio(self, user_id: str = "00000000-0000-0000-0000-000000000000") -> Portfolio:
        holdings = await self._holding_repo.get_all(user_id)
        if not holdings:
            return Portfolio(holdings=[])

        # Register each holding in the knowledge graph dynamically
        for h in holdings:
            await self._register_holding_in_graph(h)

        tickers = [h.ticker for h in holdings]
        try:
            prices = await self._market_provider.get_prices(tickers)
            for h in holdings:
                if h.ticker in prices:
                    h.current_price = prices[h.ticker].price
        except Exception as e:
            logger.error("Failed to fetch current prices for portfolio", error=str(e))

        return Portfolio(holdings=holdings)

    @timed
    async def add_holding(self, user_id: str, ticker: str, quantity: float, avg_buy_price: float, thesis: str = "") -> Holding:
        ticker = ticker.upper()

        company_name = ticker
        try:
            info = await self._market_provider.get_company_info(ticker)
            company_name = info.name
        except Exception as e:
            logger.error("Failed to fetch company info for ticker", ticker=ticker, error=str(e))

        holding = Holding(
            ticker=ticker,
            company_name=company_name,
            quantity=quantity,
            avg_buy_price=avg_buy_price,
            thesis=thesis,
            thesis_health=100.0,
            user_id=user_id,
            id=str(uuid4()),
            added_at=datetime.utcnow(),
        )

        try:
            price_data = await self._market_provider.get_price(ticker)
            holding.current_price = price_data.price
        except Exception:
            holding.current_price = avg_buy_price

        await self._holding_repo.save(holding)
        # Register custom holding in knowledge graph dynamically
        await self._register_holding_in_graph(holding)
        logger.info("Added holding", ticker=ticker, quantity=quantity, user_id=user_id)
        return holding

    @timed
    async def remove_holding(self, user_id: str, ticker: str) -> bool:
        ticker_upper = ticker.upper()
        deleted = await self._holding_repo.delete(user_id, ticker_upper)
        if deleted and self._graph:
            try:
                self._graph.remove_node(ticker_upper)
                logger.info("Removed custom holding from knowledge graph", ticker=ticker_upper)
            except Exception as e:
                logger.error("Failed to remove holding from knowledge graph", ticker=ticker_upper, error=str(e))
        logger.info("Removed holding", ticker=ticker, user_id=user_id, success=deleted)
        return deleted

    async def _register_holding_in_graph(self, holding: Holding) -> None:
        if not self._graph:
            return
        
        ticker = holding.ticker
        if self._graph.get_node(ticker):
            return
            
        logger.info("Registering custom holding in knowledge graph", ticker=ticker)
        
        sector_id = "technology"  # default
        try:
            info = await self._market_provider.get_company_info(ticker)
            sector_id = self._map_sector_to_node_id(info.sector)
        except Exception as e:
            logger.error("Failed to fetch sector for knowledge graph registration", ticker=ticker, error=str(e))
            
        from app.domain.interfaces.knowledge_graph import GraphNode, GraphEdge
        
        # Add the company node
        self._graph.add_node(
            GraphNode(
                node_id=ticker,
                node_type="company",
                label=holding.company_name,
                metadata={"exchange": "NSE", "country": "India"}
            )
        )
        
        # Link it to the mapped sector node
        self._graph.add_edge(
            GraphEdge(
                source_id=sector_id,
                target_id=ticker,
                relationship="contains",
                weight=1.0
            )
        )
        
        # Add dynamic commodity link if name matches keywords
        name_lower = holding.company_name.lower()
        ticker_lower = ticker.lower()
        
        if "coal" in name_lower or "coal" in ticker_lower:
            self._graph.add_edge(GraphEdge(source_id="coal", target_id=ticker, relationship="benefits", weight=0.9))
        if "oil" in name_lower or "petroleum" in name_lower or "crude" in name_lower:
            self._graph.add_edge(GraphEdge(source_id="crude_oil", target_id=ticker, relationship="benefits", weight=0.8))
        if "gas" in name_lower:
            self._graph.add_edge(GraphEdge(source_id="natural_gas", target_id=ticker, relationship="benefits", weight=0.8))
        if "steel" in name_lower or "iron" in name_lower:
            self._graph.add_edge(GraphEdge(source_id="steel", target_id=ticker, relationship="benefits", weight=0.8))
        if "gold" in name_lower:
            self._graph.add_edge(GraphEdge(source_id="gold", target_id=ticker, relationship="affects", weight=-0.3))
        if "silver" in name_lower:
            self._graph.add_edge(GraphEdge(source_id="silver", target_id=ticker, relationship="affects", weight=-0.3))

    def _map_sector_to_node_id(self, sector: str | None) -> str:
        if not sector:
            return "technology"
        s = sector.lower()
        if "tech" in s or "software" in s or "computer" in s:
            return "technology"
        elif "bank" in s or "financ" in s or "insur" in s or "capital" in s:
            return "banking_finance"
        elif "energy" in s or "utilities" in s or "power" in s or "oil" in s or "gas" in s or "coal" in s:
            return "energy_utilities"
        elif "consumer" in s or "fmcg" in s or "food" in s or "beverage" in s or "tobacco" in s:
            return "consumer_fmcg"
        elif "auto" in s or "vehicle" in s:
            return "automobiles"
        elif "metal" in s or "mine" in s or "mining" in s or "materials" in s:
            return "metals_mining"
        elif "aerospace" in s or "defense" in s:
            return "defense_aerospace"
        elif "aviation" in s or "airline" in s:
            return "aviation"
        elif "pharma" in s or "drug" in s or "health" in s or "medicine" in s:
            return "pharmaceuticals"
        elif "infra" in s or "construct" in s or "real estate" in s:
            return "infrastructure"
        elif "paint" in s:
            return "paints"
        elif "cement" in s:
            return "cement"
        elif "jewel" in s or "retail" in s:
            return "jewellery"
        return "technology"

    @timed
    async def evaluate_impact(self, user_id: str, event_id: str) -> PortfolioImpact:
        event = await self._event_repo.get_by_id(event_id)
        if not event:
            raise ValueError(f"Event {event_id} not found")

        portfolio = await self.get_portfolio(user_id)
        if not portfolio.holdings:
            return PortfolioImpact(
                event_id=event_id,
                event_title=event.title,
                risk_score=0.0,
                opportunity_score=0.0,
                explanation="No holdings in portfolio.",
            )

        company_impacts = await self._impact_service.process_event_impact(event)
        impacts_by_ticker = {ci.ticker: ci for ci in company_impacts}

        affected_holdings = []
        total_risk = 0.0
        total_opportunity = 0.0
        total_value = portfolio.total_value or 1.0

        for h in portfolio.holdings:
            if h.ticker in impacts_by_ticker:
                ci = impacts_by_ticker[h.ticker]
                weight = h.current_value / total_value

                impact_val = ci.direction * ci.magnitude
                if impact_val < 0:
                    total_risk += abs(impact_val) * weight
                else:
                    total_opportunity += impact_val * weight

                affected_holdings.append(
                    AffectedHolding(
                        ticker=h.ticker,
                        company_name=h.company_name,
                        direction=ci.direction,
                        magnitude=ci.magnitude,
                        reasoning=ci.reasoning_path,
                    )
                )

        winners_count = len([ah for ah in affected_holdings if ah.direction > 0])
        losers_count = len([ah for ah in affected_holdings if ah.direction < 0])
        explanation = (
            f"Event '{event.title}' affects {len(affected_holdings)} holdings. "
            f"Expected positive impact on {winners_count} positions and negative on {losers_count} positions."
        )

        return PortfolioImpact(
            event_id=event_id,
            event_title=event.title,
            risk_score=round(min(1.0, total_risk), 2),
            opportunity_score=round(min(1.0, total_opportunity), 2),
            affected_holdings=affected_holdings,
            explanation=explanation,
            timestamp=datetime.utcnow(),
        )

    @timed
    async def get_exposure(self, user_id: str = "00000000-0000-0000-0000-000000000000") -> list[SectorExposure]:
        portfolio = await self.get_portfolio(user_id)
        if not portfolio.holdings:
            return []

        sector_values: dict[str, float] = {}
        sector_counts: dict[str, int] = {}

        for h in portfolio.holdings:
            try:
                info = await self._market_provider.get_company_info(h.ticker)
                sector = info.sector or "Other"
            except Exception:
                sector = "Other"

            sector_values[sector] = sector_values.get(sector, 0.0) + h.current_value
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

        total_value = portfolio.total_value or 1.0
        exposure = []
        for sector, val in sector_values.items():
            exposure.append(
                SectorExposure(
                    sector=sector,
                    total_value=round(val, 2),
                    holding_count=sector_counts[sector],
                    weight_pct=round((val / total_value) * 100, 2),
                )
            )
        return sorted(exposure, key=lambda x: x.weight_pct, reverse=True)

    @timed
    async def evaluate_thesis_drift(self, event: Any) -> None:
        """
        Evaluate whether a freshly processed MarketEvent decays or validates
        the written thesis for each portfolio holding.

        Logic:
        - Build a keyword index from the holding thesis text.
        - Check whether any keyword appears in the event's title or summary.
        - Sentiment clash (e.g., positive thesis vs. negative event) → decay health.
        - Sentiment alignment (positive thesis + positive event) → heal health.
        - Health is bounded to [10.0, 100.0] and persisted to the database.
        """
        holdings = await self._holding_repo.get_all()
        if not holdings:
            return

        # Pull event fields safely
        event_text = f"{getattr(event, 'title', '')} {getattr(event, 'summary', '')}".lower()
        event_sentiment = str(getattr(event, 'sentiment', '')).lower()
        event_severity = float(getattr(event, 'severity', 0.3))

        # Map raw sentiment enum values to polarity booleans
        is_event_negative = "negative" in event_sentiment
        is_event_positive = "positive" in event_sentiment

        # Sector-keyword fingerprints for quick matching when thesis is empty
        sector_keywords = {
            "technology": ["tech", "software", "it", "cloud", "digital", "ai", "semiconductor", "chip"],
            "banking_finance": ["bank", "rate", "interest", "rbi", "fed", "npa", "credit", "loan", "nbfc"],
            "energy_utilities": ["oil", "crude", "gas", "power", "energy", "coal", "solar", "renewab"],
            "automobiles": ["auto", "car", "ev", "vehicle", "electric"],
            "metals_mining": ["steel", "metal", "copper", "aluminium", "iron", "mining"],
            "aviation": ["flight", "airline", "aviation", "atf", "jet"],
            "pharmaceuticals": ["pharma", "drug", "medicine", "api", "fda", "approval"],
            "infrastructure": ["infra", "construction", "capex", "budget", "roads"],
            "paints": ["paint", "crude", "raw material", "pigment"],
            "consumer_fmcg": ["fmcg", "consumer", "food", "beverage", "rural"],
        }

        for holding in holdings:
            if not holding.thesis:
                continue

            thesis_lower = holding.thesis.lower()
            thesis_words = [w.strip(".,;:") for w in thesis_lower.split() if len(w) > 3]

            # Step 1: Check if event text overlaps meaningfully with holding thesis
            matched_keywords = [word for word in thesis_words if word in event_text]

            if not matched_keywords:
                # Fallback: Try sector-level keyword matching
                sector_key = self._map_sector_to_node_id(None)
                for sec, kws in sector_keywords.items():
                    for kw in kws:
                        if kw in thesis_lower and kw in event_text:
                            matched_keywords.append(kw)
                            break

            if not matched_keywords:
                # Event does not touch this holding's thesis at all — skip
                continue

            # Step 2: Determine sentiment direction of thesis
            positive_thesis_words = ["growth", "expansion", "rise", "boost", "cut", "benefit", "strong",
                                      "increase", "recover", "gain", "upside", "rally", "demand", "inflow"]
            negative_thesis_words = ["risk", "decline", "fall", "hike", "slowdown", "pressure", "stress",
                                      "loss", "decrease", "downside", "sell", "bear", "weak", "concern"]

            thesis_is_positive = any(pw in thesis_lower for pw in positive_thesis_words)
            thesis_is_negative = any(nw in thesis_lower for nw in negative_thesis_words)

            # Step 3: Calculate drift delta
            delta = 0.0
            decay_factor = event_severity * 15.0     # Max ~15% decay per high-severity event
            heal_factor = event_severity * 6.0        # Max ~6% heal per supportive event

            if thesis_is_positive and is_event_negative:
                # Thesis says "grow", event says "crisis" → decay
                delta = -decay_factor
            elif thesis_is_positive and is_event_positive:
                # Thesis says "grow", event says "rally" → strengthen
                delta = +heal_factor
            elif thesis_is_negative and is_event_positive:
                # Thesis says "risk", event says "rally" → thesis was wrong, no action
                delta = 0.0
            elif thesis_is_negative and is_event_negative:
                # Thesis says "risk", event confirms risk → thesis validated
                delta = +heal_factor * 0.5

            if delta == 0.0:
                continue

            # Step 4: Apply bounded update
            new_health = max(10.0, min(100.0, holding.thesis_health + delta))
            if abs(new_health - holding.thesis_health) < 0.5:
                continue

            holding.thesis_health = round(new_health, 1)
            logger.info(
                "thesis_drift_update",
                ticker=holding.ticker,
                matched=matched_keywords[:3],
                delta=round(delta, 2),
                new_health=holding.thesis_health,
            )
            await self._holding_repo.save(holding)

