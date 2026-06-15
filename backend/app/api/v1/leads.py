"""Alpha Leads API endpoints.

Exposes algorithmically generated trading leads to the frontend.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_lead_service
from app.services.lead_service import LeadService

router = APIRouter()


@router.get("")
async def get_active_leads(
    lead_service: LeadService = Depends(get_lead_service),
):
    """Return all active (non-expired) alpha leads, sorted by conviction descending."""
    leads = await lead_service.get_active_leads(limit=20)
    return [
        {
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
        }
        for lead in leads
    ]


@router.get("/{ticker}")
async def get_leads_for_ticker(
    ticker: str,
    lead_service: LeadService = Depends(get_lead_service),
):
    """Return active leads for a specific ticker."""
    leads = await lead_service.get_leads_for_ticker(ticker)
    return [
        {
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
        }
        for lead in leads
    ]
