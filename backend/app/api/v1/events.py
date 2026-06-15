"""Events router.

Exposes REST endpoints for querying classified market events and propagating graph impacts.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_event_repository, get_impact_service, get_memory_engine, get_causal_chain_service
from app.domain.interfaces.repository import IEventRepository
from app.services.impact_service import ImpactService

router = APIRouter()


@router.get("")
async def get_events(
    category: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    repo: IEventRepository = Depends(get_event_repository),
):
    if category:
        return await repo.get_by_category(category, limit=limit)
    return await repo.get_recent(limit=limit)


@router.get("/{event_id}")
async def get_event(
    event_id: str,
    repo: IEventRepository = Depends(get_event_repository),
):
    event = await repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/{event_id}/impact")
async def get_event_impact(
    event_id: str,
    repo: IEventRepository = Depends(get_event_repository),
    impact_service: ImpactService = Depends(get_impact_service),
):
    event = await repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return await impact_service.process_event_impact(event)


@router.get("/{event_id}/historical-analogy")
async def get_event_historical_analogy(
    event_id: str,
    repo: IEventRepository = Depends(get_event_repository),
    memory_engine = Depends(get_memory_engine),
):
    event = await repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    query_text = f"{event.title}. {event.summary}"
    result = memory_engine.find_analogies(query_text)
    
    return {
        "event_title": result.event_title,
        "avg_expected_impact_30d": result.avg_expected_impact_30d,
        "avg_expected_impact_60d": result.avg_expected_impact_60d,
        "confidence": result.confidence,
        "summary": result.summary,
        "analogies": [
            {
                "event_id": a.event_id,
                "year": a.year,
                "title": a.title,
                "similarity_score": a.similarity_score,
                "nifty_impact_30d": a.nifty_impact_30d,
                "nifty_impact_60d": a.nifty_impact_60d,
                "best_sectors": a.best_sectors,
                "worst_sectors": a.worst_sectors,
                "description": a.description,
            }
            for a in result.analogies
        ]
    }


@router.get("/{event_id}/causal-chain")
async def get_event_causal_chain(
    event_id: str,
    repo: IEventRepository = Depends(get_event_repository),
    causal_service = Depends(get_causal_chain_service),
):
    event = await repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    chains = causal_service.trace_event(event)
    return [
        {
            "trigger_node": c.trigger_node,
            "trigger_label": c.trigger_label,
            "base_impact": c.base_impact,
            "chain": [
                {
                    "node_id": node.node_id,
                    "label": node.label,
                    "node_type": node.node_type,
                    "depth": node.depth,
                    "impact": node.impact,
                    "direction": node.direction,
                    "reason": node.reason,
                    "path": node.path,
                }
                for node in c.chain
            ]
        }
        for c in chains
    ]


