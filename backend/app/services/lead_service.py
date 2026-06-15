"""Alpha Lead Generation Service.

Custom 5-signal scoring engine that processes every incoming news event,
scores it against multiple signal dimensions, and outputs actionable
BUY / SELL / ACCUMULATE / EXIT leads for specific tickers.

Signal weights:
  - News Sentiment Spike:  30%
  - Key Voice Amplifier:   20%
  - Sector Momentum:       20%
  - Graph Propagation:     15%
  - Smart Money Confluence: 15%
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable
from uuid import uuid4

from app.domain.interfaces.knowledge_graph import IKnowledgeGraph
from app.domain.interfaces.repository import IEventRepository
from app.domain.models.event import MarketEvent, SentimentLabel, EventCategory
from app.domain.models.lead import AlphaLead, LeadAction
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)

# ------------------------------------------------------------------ #
# Constants                                                            #
# ------------------------------------------------------------------ #

CONVICTION_THRESHOLD = 0.12
LEAD_EXPIRY_HOURS = 24

# Signal weights (must sum to 1.0)
W_NEWS = 0.30
W_VOICE = 0.20
W_SECTOR = 0.20
W_GRAPH = 0.15
W_SMART = 0.15

# Key voice profiles: leader_id → {weight, sectors they influence}
KEY_VOICES = {
    "donald_trump": {
        "name": "Donald Trump",
        "weight": 0.9,
        "sectors": {"technology": -0.4, "energy_utilities": 0.6, "defense_aerospace": 0.5, "metals_mining": 0.3},
    },
    "narendra_modi": {
        "name": "Narendra Modi",
        "weight": 0.85,
        "sectors": {"infrastructure": 0.8, "energy_utilities": 0.7, "banking_finance": 0.5, "defense_aerospace": 0.4},
    },
    "jerome_powell": {
        "name": "Jerome Powell",
        "weight": 0.95,
        "sectors": {"banking_finance": 0.9, "consumer_fmcg": 0.3, "technology": 0.2},
    },
    "elon_musk": {
        "name": "Elon Musk",
        "weight": 0.8,
        "sectors": {"technology": 0.8, "automobiles": 0.7, "energy_utilities": 0.5, "metals_mining": 0.4},
    },
}

# Ticker → sector mapping for all tracked stocks
TICKER_SECTORS = {
    "TCS.NS": "technology", "INFY.NS": "technology", "WIPRO.NS": "technology",
    "TECHM.NS": "technology", "HCLTECH.NS": "technology",
    "HDFCBANK.NS": "banking_finance", "ICICIBANK.NS": "banking_finance",
    "SBIN.NS": "banking_finance", "KOTAKBANK.NS": "banking_finance",
    "AXISBANK.NS": "banking_finance", "BAJFINANCE.NS": "banking_finance",
    "RELIANCE.NS": "energy_utilities", "ONGC.NS": "energy_utilities",
    "NTPC.NS": "energy_utilities", "POWERGRID.NS": "energy_utilities",
    "COALINDIA.NS": "energy_utilities",
    "HINDUNILVR.NS": "consumer_fmcg", "ITC.NS": "consumer_fmcg",
    "NESTLEIND.NS": "consumer_fmcg",
    "MARUTI.NS": "automobiles", "TITAN.NS": "consumer_fmcg",
    "LT.NS": "infrastructure", "ULTRACEMCO.NS": "infrastructure",
    "ASIANPAINT.NS": "paints",
    "SUNPHARMA.NS": "pharmaceuticals",
    "HAL.NS": "defense_aerospace", "BEL.NS": "defense_aerospace",
    "INDIGO.NS": "aviation",
    "TATASTEEL.NS": "metals_mining",
    "BHARTIARTL.NS": "technology",
}

# Ticker → company name for display
TICKER_NAMES = {
    "TCS.NS": "Tata Consultancy Services", "INFY.NS": "Infosys",
    "WIPRO.NS": "Wipro", "TECHM.NS": "Tech Mahindra",
    "HCLTECH.NS": "HCL Technologies",
    "HDFCBANK.NS": "HDFC Bank", "ICICIBANK.NS": "ICICI Bank",
    "SBIN.NS": "State Bank of India", "KOTAKBANK.NS": "Kotak Mahindra Bank",
    "AXISBANK.NS": "Axis Bank", "BAJFINANCE.NS": "Bajaj Finance",
    "RELIANCE.NS": "Reliance Industries", "ONGC.NS": "Oil & Natural Gas Corp",
    "NTPC.NS": "NTPC Ltd", "POWERGRID.NS": "Power Grid Corp",
    "COALINDIA.NS": "Coal India",
    "HINDUNILVR.NS": "Hindustan Unilever", "ITC.NS": "ITC Ltd",
    "NESTLEIND.NS": "Nestle India",
    "MARUTI.NS": "Maruti Suzuki", "TITAN.NS": "Titan Company",
    "LT.NS": "Larsen & Toubro", "ULTRACEMCO.NS": "UltraTech Cement",
    "ASIANPAINT.NS": "Asian Paints",
    "SUNPHARMA.NS": "Sun Pharma",
    "HAL.NS": "Hindustan Aeronautics", "BEL.NS": "Bharat Electronics",
    "INDIGO.NS": "IndiGo Airlines",
    "TATASTEEL.NS": "Tata Steel",
    "BHARTIARTL.NS": "Bharti Airtel",
}


class LeadService:
    """Orchestrates the 5-signal alpha lead generation algorithm."""

    def __init__(
        self,
        lead_repository: Any,
        knowledge_graph: IKnowledgeGraph,
        event_repository: IEventRepository,
        stakeholder_service: Any = None,
        broadcast_callback: Callable[[dict], Any] | None = None,
    ) -> None:
        self._lead_repo = lead_repository
        self._graph = knowledge_graph
        self._event_repo = event_repository
        self._stakeholder_service = stakeholder_service
        self._broadcast_callback = broadcast_callback
        self._recent_sector_scores: dict[str, float] = {}

    def _compute_news_signal(self, event: MarketEvent) -> float:
        """Signal 1: News sentiment × severity (30% weight)."""
        factor = 1.0
        if event.sentiment == SentimentLabel.NEGATIVE:
            factor = -1.0
        elif event.sentiment == SentimentLabel.NEUTRAL:
            factor = 0.2
        return event.severity * factor

    def _detect_key_voice(self, event: MarketEvent) -> tuple[str | None, dict]:
        """Signal 2: Detect if a key voice is in the event entities."""
        for ent in event.entities:
            norm = ent.normalized_name.lower()
            if norm in KEY_VOICES:
                return norm, KEY_VOICES[norm]
        # Fallback: check raw text
        text = (event.title + " " + event.raw_text).lower()
        for voice_id, profile in KEY_VOICES.items():
            name_parts = profile["name"].lower().split()
            if any(part in text for part in name_parts):
                return voice_id, profile
        return None, {}

    def _compute_voice_signal(self, event: MarketEvent, ticker_sector: str, voice_profile: dict) -> float:
        """Signal 2: Key voice amplifier (20% weight)."""
        if not voice_profile:
            return 0.0
        base_weight = voice_profile.get("weight", 0.5)
        sector_influence = voice_profile.get("sectors", {}).get(ticker_sector, 0.1)
        sentiment_dir = 1.0 if event.sentiment != SentimentLabel.NEGATIVE else -1.0
        return base_weight * sector_influence * event.severity * sentiment_dir

    def _compute_sector_momentum(self, events: list[MarketEvent], ticker_sector: str) -> float:
        """Signal 3: Accumulated sector momentum from recent events (20% weight)."""
        if not ticker_sector:
            return 0.0

        sector_score = 0.0
        for ev in events[:15]:
            base = ev.severity
            if ev.sentiment == SentimentLabel.NEGATIVE:
                base = -ev.severity
            elif ev.sentiment == SentimentLabel.NEUTRAL:
                base *= 0.2

            for ent in ev.entities:
                norm = ent.normalized_name.lower()
                if norm == ticker_sector:
                    sector_score += base * 1.0
                # Cross-entity sector inference
                if norm in KEY_VOICES:
                    voice_sectors = KEY_VOICES[norm].get("sectors", {})
                    if ticker_sector in voice_sectors:
                        sector_score += base * voice_sectors[ticker_sector] * 0.5

        return max(-1.0, min(1.0, sector_score))

    def _compute_graph_signal(self, event: MarketEvent, ticker: str) -> tuple[float, float]:
        """Signal 4: Graph propagation impact (15% weight).
        Returns (direction × magnitude, expected_move_pct).
        """
        start_nodes = []
        for ent in event.entities:
            node_id = ent.normalized_name.lower()
            if self._graph.get_node(node_id):
                start_nodes.append((node_id, ent.confidence))

        cat_node = event.category.value.lower()
        if self._graph.get_node(cat_node):
            start_nodes.append((cat_node, 0.5))

        if not start_nodes:
            return 0.0, 0.0

        best_impact = 0.0
        best_move = 0.0
        for node_id, conf in start_nodes:
            base_score = event.severity
            if event.sentiment == SentimentLabel.NEGATIVE:
                base_score = -event.severity

            propagation = self._graph.propagate_impact(node_id, base_score * conf, max_depth=3)
            for comp in propagation.affected_companies:
                if comp.ticker == ticker:
                    impact = comp.direction * comp.magnitude
                    if abs(impact) > abs(best_impact):
                        best_impact = impact
                        best_move = impact * 4.0
        return best_impact, best_move

    async def _compute_smart_money_signal(self, ticker: str) -> float:
        """Signal 5: Smart money confluence (15% weight)."""
        if not self._stakeholder_service:
            return 0.0
        try:
            sm_sig = await self._stakeholder_service.get_smart_money_signal(ticker)
            if sm_sig:
                return sm_sig.net_score
        except Exception:
            pass
        return 0.0

    @timed
    async def generate_leads(self, event: MarketEvent) -> list[AlphaLead]:
        """Core algorithm: generate alpha leads from a single market event."""
        # Filter: skip unclassified events with no entities
        if event.category == EventCategory.UNKNOWN and not event.entities:
            logger.debug("Skipping lead generation for unclassified event", event_id=event.id)
            return []

        logger.info("Running lead generation algorithm", event_id=event.id, title=event.title)

        # Get recent events for sector momentum calculation
        try:
            recent_events = await self._event_repo.get_recent(limit=15)
        except Exception:
            recent_events = [event]

        # Detect key voice
        voice_id, voice_profile = self._detect_key_voice(event)

        # Compute news signal (common across all tickers)
        news_signal = self._compute_news_signal(event)

        leads: list[AlphaLead] = []

        for ticker, sector in TICKER_SECTORS.items():
            # Signal 1: News
            s_news = news_signal

            # Signal 2: Key Voice
            s_voice = self._compute_voice_signal(event, sector, voice_profile)

            # Signal 3: Sector Momentum
            s_sector = self._compute_sector_momentum(recent_events, sector)

            # Signal 4: Graph Propagation
            s_graph, expected_move = self._compute_graph_signal(event, ticker)

            # Signal 5: Smart Money
            s_smart = await self._compute_smart_money_signal(ticker)

            # Composite conviction score
            conviction = (
                (s_news * W_NEWS) +
                (s_voice * W_VOICE) +
                (s_sector * W_SECTOR) +
                (s_graph * W_GRAPH) +
                (s_smart * W_SMART)
            )

            # Only emit leads above threshold
            if abs(conviction) < CONVICTION_THRESHOLD:
                continue

            # Determine action
            if conviction >= 0.7:
                action = LeadAction.ACCUMULATE
            elif conviction > 0:
                action = LeadAction.BUY
            elif conviction <= -0.7:
                action = LeadAction.EXIT
            else:
                action = LeadAction.SELL

            # Build reasoning chain
            reasoning = []
            if abs(s_news) > 0.1:
                direction = "bullish" if s_news > 0 else "bearish"
                reasoning.append(f"News signal: {direction} sentiment (severity {event.severity:.2f}) → score {s_news:+.3f}")
            if abs(s_voice) > 0.01 and voice_id:
                reasoning.append(f"Key voice: {KEY_VOICES[voice_id]['name']} speech amplifying {sector} → score {s_voice:+.3f}")
            if abs(s_sector) > 0.05:
                reasoning.append(f"Sector momentum: {sector} trending {'up' if s_sector > 0 else 'down'} → score {s_sector:+.3f}")
            if abs(s_graph) > 0.01:
                reasoning.append(f"Graph propagation: economic chain impact → score {s_graph:+.3f}")
            if abs(s_smart) > 0.01:
                reasoning.append(f"Smart money: institutional {'accumulation' if s_smart > 0 else 'distribution'} → score {s_smart:+.3f}")

            if not reasoning:
                reasoning.append(f"Composite multi-signal analysis triggered {action.value.upper()} conviction.")

            # If expected_move wasn't computed from graph, estimate from conviction
            if abs(expected_move) < 0.01:
                expected_move = conviction * 3.0

            lead = AlphaLead(
                id=str(uuid4()),
                ticker=ticker,
                company_name=TICKER_NAMES.get(ticker, ticker),
                action=action,
                conviction=round(abs(conviction), 3),
                expected_move_pct=round(expected_move, 2),
                trigger_event_id=event.id,
                trigger_event_title=event.title,
                reasoning=reasoning,
                signals={
                    "news": round(s_news, 3),
                    "voice": round(s_voice, 3),
                    "sector": round(s_sector, 3),
                    "graph": round(s_graph, 3),
                    "smart_money": round(s_smart, 3),
                },
                sector=sector,
                key_voice=KEY_VOICES[voice_id]["name"] if voice_id else None,
                expires_at=datetime.utcnow() + timedelta(hours=LEAD_EXPIRY_HOURS),
                timestamp=datetime.utcnow(),
            )

            # Persist
            try:
                await self._lead_repo.save(lead)
            except Exception as e:
                logger.error("Failed to persist lead", ticker=ticker, error=str(e))
                continue

            leads.append(lead)

            # Broadcast via WebSocket
            if self._broadcast_callback:
                try:
                    await self._broadcast_callback({
                        "type": "new_lead",
                        "data": {
                            "id": lead.id,
                            "ticker": lead.ticker,
                            "company_name": lead.company_name,
                            "action": lead.action.value,
                            "conviction": lead.conviction,
                            "expected_move_pct": lead.expected_move_pct,
                            "trigger_event_id": lead.trigger_event_id,
                            "trigger_event_title": lead.trigger_event_title,
                            "reasoning": lead.reasoning,
                            "signals": lead.signals,
                            "sector": lead.sector,
                            "key_voice": lead.key_voice,
                            "expires_at": lead.expires_at.isoformat(),
                            "timestamp": lead.timestamp.isoformat(),
                        },
                    })
                except Exception as e:
                    logger.error("Failed to broadcast lead", ticker=ticker, error=str(e))

        logger.info("Lead generation complete", event_id=event.id, leads_generated=len(leads))
        return leads

    async def get_active_leads(self, *, limit: int = 20) -> list[AlphaLead]:
        """Return currently active (non-expired) leads sorted by conviction."""
        return await self._lead_repo.get_active(limit=limit)

    async def get_leads_for_ticker(self, ticker: str) -> list[AlphaLead]:
        """Return active leads for a specific ticker."""
        return await self._lead_repo.get_by_ticker(ticker)

    async def cleanup_expired(self) -> int:
        """Remove expired leads from the database."""
        count = await self._lead_repo.expire_stale()
        if count > 0:
            logger.info("Cleaned up expired leads", count=count)
        return count
