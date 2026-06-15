"""Search router.

Exposes endpoints for text search across events and market intelligence.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_event_repository, get_impact_service
from app.domain.interfaces.repository import IEventRepository
from app.services.impact_service import ImpactService

router = APIRouter()


@router.get("")
async def search(
    q: str = Query(default=""),
    repo: IEventRepository = Depends(get_event_repository),
    impact_service: ImpactService = Depends(get_impact_service),
):
    if not q:
        return []

    events = await repo.get_recent(limit=100)
    q_lower = q.lower()

    matches = []
    for event in events:
        if (
            q_lower in event.title.lower()
            or q_lower in event.raw_text.lower()
            or q_lower in event.category.value.lower()
        ):
            matches.append(event)

    # If no matching events found in database, generate a hypothetical event on-the-fly
    if not matches:
        from app.domain.models.event import MarketEvent, EventCategory, EventSubCategory, SentimentLabel
        from app.domain.models.entity import ExtractedEntity, EntityType
        from datetime import datetime
        
        # 1. Classify sentiment and severity based on search query keywords
        sentiment = SentimentLabel.NEUTRAL
        severity = 0.4
        
        if any(w in q_lower for w in ["war", "crisis", "crash", "hike", "drop", "fall", "conflict", "clash", "sanction", "spikes", "spike"]):
            sentiment = SentimentLabel.NEGATIVE
            severity = 0.75 if any(w in q_lower for w in ["war", "crash", "crisis"]) else 0.55
        elif any(w in q_lower for w in ["rally", "peace", "rise", "deal", "up", "surge", "growth", "boost"]):
            sentiment = SentimentLabel.POSITIVE
            severity = 0.50
            
        # 2. Determine category and subcategory
        category = EventCategory.UNKNOWN
        sub_category = EventSubCategory.UNKNOWN
        
        if any(w in q_lower for w in ["war", "iran", "geopolitical", "conflict", "sanctions", "border", "middle east", "russia", "military"]):
            category = EventCategory.GEOPOLITICAL
            if "war" in q_lower or "conflict" in q_lower:
                sub_category = EventSubCategory.WAR
            elif "sanction" in q_lower:
                sub_category = EventSubCategory.SANCTIONS
        elif any(w in q_lower for w in ["interest", "rate", "inflation", "gdp", "economic", "growth", "crude", "oil", "gas", "commodity"]):
            category = EventCategory.ECONOMIC
            if "rate" in q_lower or "interest" in q_lower:
                sub_category = EventSubCategory.INTEREST_RATE
            elif "gdp" in q_lower:
                sub_category = EventSubCategory.GDP
            elif any(w in q_lower for w in ["oil", "gas", "coal", "commodity"]):
                sub_category = EventSubCategory.COMMODITY_SHOCK
        elif any(w in q_lower for w in ["ipo", "sme", "earnings", "merger", "acquisition"]):
            category = EventCategory.COMPANY
            if "ipo" in q_lower:
                category = EventCategory.MARKET
                sub_category = EventSubCategory.IPO
                
        # 3. Map query to knowledge graph entities via robust synonym maps
        synonyms = {
            "middle_east": ["iran", "iraq", "israel", "middle east", "gaza", "suez", "persian"],
            "usa": ["usa", "us", "america", "united states", "fed", "wall st", "nasdaq"],
            "china": ["china", "chinese", "beijing"],
            "india": ["india", "indian", "delhi", "mumbai"],
            "russia": ["russia", "russian", "moscow"],
            "germany": ["germany", "german", "berlin"],
            "crude_oil": ["oil", "crude", "petroleum", "brent", "wti"],
            "natural_gas": ["gas", "lng", "cng"],
            "coal": ["coal", "coke", "coking"],
            "gold": ["gold", "jewel", "jewellery"],
            "silver": ["silver"],
            "steel": ["steel", "iron"],
            "copper": ["copper"],
            "semiconductors": ["semiconductor", "chip", "chips", "processor", "electronics"],
            "api_ingredients": ["api", "ingredient"],
            "agricultural_products": ["agri", "agriculture", "wheat", "rice", "crop", "sugar"],
            "technology": ["tech", "technology", "software", "it services"],
            "banking_finance": ["bank", "banking", "finance", "fii", "dii", "interest", "rate", "inflation", "rbi", "fed"],
            "energy_utilities": ["energy", "power", "utility", "solar", "renewable"],
            "consumer_fmcg": ["fmcg", "consumer", "food", "beverage", "tobacco"],
            "automobiles": ["auto", "car", "vehicle", "electric vehicle", "ev", "motors"],
            "metals_mining": ["metal", "mining", "aluminium", "copper", "iron"],
            "defense_aerospace": ["defense", "aerospace", "military"],
            "aviation": ["aviation", "airline", "flight"],
            "pharmaceuticals": ["pharma", "pharmaceutical", "drug", "medicine"],
            "infrastructure": ["infra", "infrastructure", "construction"],
            "paints": ["paint", "paints"],
            "cement": ["cement"],
            "jewellery": ["jewel", "jewellery", "gold", "silver"],
            "donald_trump": ["trump", "donald trump", "donald_trump", "donald"],
            "narendra_modi": ["modi", "narendra modi", "narendra_modi", "pm modi"],
            "jerome_powell": ["powell", "jerome powell", "jerome_powell", "fed chair"],
            "elon_musk": ["musk", "elon musk", "elon_musk", "tesla ceo"],
        }
        
        entities = []
        from app.infrastructure.graph.graph_seed import MACRO_NODES
        for node_id, syns in synonyms.items():
            if any(s in q_lower for s in syns):
                label = node_id.replace("_", " ").title()
                ntype = "concept"
                for nid, nt, lbl in MACRO_NODES:
                    if nid == node_id:
                        label = lbl
                        ntype = nt
                        break
                
                etype = EntityType.UNKNOWN
                if ntype == "country":
                    etype = EntityType.COUNTRY
                elif ntype == "commodity":
                    etype = EntityType.COMMODITY
                elif ntype == "person":
                    etype = EntityType.PERSON
                elif ntype == "sector":
                    etype = EntityType.SECTOR
                elif ntype == "company":
                    etype = EntityType.COMPANY
                
                entities.append(ExtractedEntity(
                    text=label,
                    entity_type=etype,
                    confidence=0.95,
                    normalized_name=node_id
                ))

        # 4. Instantiate and save the simulated event
        hypo_event = MarketEvent(
            title=q.strip().title(),
            raw_text=f"Simulated market event generated for search query: '{q}'",
            source="Simulator",
            category=category,
            sub_category=sub_category,
            sentiment=sentiment,
            severity=severity,
            confidence=0.85,
            summary=f"Simulated news report generated to evaluate the downstream stock market impact of: '{q}'.",
            entities=entities,
            timestamp=datetime.utcnow()
        )
        
        # Save to database (commits automatically via FastAPI dependency get_db session lifecycle)
        await repo.save(hypo_event)
        
        # Process and propagate downstream company impacts
        await impact_service.process_event_impact(hypo_event)
        matches.append(hypo_event)

    return matches[:15]
