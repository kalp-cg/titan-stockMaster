"""Port interface for the stakeholder data provider."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from app.domain.models.stakeholder import (
    BlockDeal,
    BulkDeal,
    InsiderTrade,
    InstitutionalFlow,
    ShareholdingPattern,
    SmartMoneySignal,
)


class IStakeholderDataProvider(Protocol):
    """
    Interface for fetching stakeholder data from NSE/BSE.

    Any adapter (scraper, paid API, mock) that implements this
    protocol can be dropped in without changing any service code.
    """

    async def get_shareholding_pattern(self, ticker: str) -> ShareholdingPattern:
        """
        Fetch the most recent quarterly shareholding pattern.

        Args:
            ticker: NSE ticker symbol (e.g., "RELIANCE").
        """
        ...

    async def get_shareholding_history(
        self,
        ticker: str,
        *,
        quarters: int = 8,
    ) -> list[ShareholdingPattern]:
        """
        Fetch shareholding history for the last N quarters.

        Returns chronologically ordered list (oldest first).
        """
        ...

    async def get_bulk_deals(
        self,
        ticker: str | None = None,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[BulkDeal]:
        """
        Fetch bulk deal disclosures.

        Args:
            ticker: Filter to a specific ticker; None = all market deals.
            date_from: Inclusive start date filter.
            date_to: Inclusive end date filter.
        """
        ...

    async def get_block_deals(
        self,
        ticker: str | None = None,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[BlockDeal]:
        """Fetch block deal disclosures."""
        ...

    async def get_insider_trades(
        self,
        ticker: str | None = None,
        *,
        days: int = 90,
    ) -> list[InsiderTrade]:
        """
        Fetch recent insider trading disclosures.

        Args:
            ticker: Filter to a specific ticker; None = all companies.
            days: Look back this many calendar days.
        """
        ...

    async def get_institutional_flows(
        self,
        *,
        days: int = 30,
    ) -> list[InstitutionalFlow]:
        """
        Fetch daily FII/DII aggregate market flows.

        Returns list ordered by date ascending.
        """
        ...
