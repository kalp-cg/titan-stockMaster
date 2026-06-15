"""Risk radar monitoring service.

Scans portfolio holdings for governance issues, leverage hikes, promoter pledges,
and heavy insider dump disclosures.
"""

from __future__ import annotations

from typing import Any

from app.domain.interfaces.repository import IRiskAlertRepository
from app.domain.models.risk import RiskAlert, RiskFactor, RiskSeverity
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


class RiskService:
    """Monitors portfolio holdings for governance, debt, and stakeholder risks."""

    def __init__(
        self,
        risk_repository: IRiskAlertRepository,
        portfolio_service: Any,
        stakeholder_service: Any,
        market_provider: Any,
    ) -> None:
        self._repository = risk_repository
        self._portfolio_service = portfolio_service
        self._stakeholder_service = stakeholder_service
        self._market_provider = market_provider

    @timed
    async def get_recent_alerts(self, *, limit: int = 20) -> list[RiskAlert]:
        alerts = await self._repository.get_recent(limit=limit)
        if not alerts:
            await self.scan_portfolio_risk()
            alerts = await self._repository.get_recent(limit=limit)
        return alerts

    @timed
    async def scan_portfolio_risk(self) -> list[RiskAlert]:
        logger.info("Starting portfolio risk scan")
        portfolio = await self._portfolio_service.get_portfolio()
        generated_alerts = []

        if not portfolio.holdings:
            return []

        for h in portfolio.holdings:
            try:
                pattern = await self._stakeholder_service.get_shareholding_pattern(h.ticker)
                if pattern:
                    if pattern.promoter_pledge_pct > 25.0:
                        severity = (
                            RiskSeverity.CRITICAL
                            if pattern.promoter_pledge_pct > 50.0
                            else RiskSeverity.HIGH
                        )
                        alert = RiskAlert(
                            ticker=h.ticker,
                            company_name=h.company_name,
                            factor=RiskFactor.PROMOTER_PLEDGE_INCREASE,
                            severity=severity,
                            description=f"Promoter pledge ratio is dangerously high at {pattern.promoter_pledge_pct}%.",
                            supporting_evidence=[
                                f"Latest filing quarter: {pattern.quarter}.",
                                f"Promoter pledge ratio: {pattern.promoter_pledge_pct}% of promoter holding.",
                            ],
                            source="NSE Corporate Disclosures",
                        )
                        await self._repository.save(alert)
                        generated_alerts.append(alert)

                    if pattern.promoter_delta < -1.5:
                        alert = RiskAlert(
                            ticker=h.ticker,
                            company_name=h.company_name,
                            factor=RiskFactor.PROMOTER_SELLING,
                            severity=RiskSeverity.HIGH,
                            description=f"Promoters diluted their holding by {abs(pattern.promoter_delta)}% in {pattern.quarter}.",
                            supporting_evidence=[
                                f"Promoter holding decreased from {pattern.promoter_pct - pattern.promoter_delta:.2f}% to {pattern.promoter_pct:.2f}%.",
                            ],
                            source="NSE Shareholding Pattern Disclosures",
                        )
                        await self._repository.save(alert)
                        generated_alerts.append(alert)

                trades = await self._stakeholder_service.get_insider_trades(h.ticker, days=30)
                insider_sales_value = 0.0
                evidence = []
                for t in trades:
                    if t.trade_type.value == "sell":
                        insider_sales_value += t.total_value
                        evidence.append(
                            f"{t.insider_name} ({t.designation}) sold {t.quantity} shares at ₹{t.price} on {t.date}."
                        )

                if insider_sales_value > 5_000_000:
                    severity = RiskSeverity.MEDIUM
                    if insider_sales_value > 50_000_000:
                        severity = RiskSeverity.HIGH

                    alert = RiskAlert(
                        ticker=h.ticker,
                        company_name=h.company_name,
                        factor=RiskFactor.INSIDER_SELLING,
                        severity=severity,
                        description=f"Significant insider selling detected in the last 30 days totaling ₹{insider_sales_value/1e7:.2f} Crore.",
                        supporting_evidence=evidence[:3],
                        source="SEBI Insider Trade Disclosures",
                    )
                    await self._repository.save(alert)
                    generated_alerts.append(alert)

                company_info = await self._market_provider.get_company_info(h.ticker)
                if company_info and company_info.debt_to_equity > 2.0:
                    severity = (
                        RiskSeverity.CRITICAL
                        if company_info.debt_to_equity > 3.0
                        else RiskSeverity.HIGH
                    )
                    alert = RiskAlert(
                        ticker=h.ticker,
                        company_name=h.company_name,
                        factor=RiskFactor.DEBT_SPIKE,
                        severity=severity,
                        description=f"Company is highly leveraged with Debt-to-Equity ratio of {company_info.debt_to_equity:.2f}.",
                        supporting_evidence=[
                            f"Total Debt-to-Equity: {company_info.debt_to_equity:.2f} (ideal < 1.0).",
                        ],
                        source="Fundamental Statements",
                    )
                    await self._repository.save(alert)
                    generated_alerts.append(alert)

            except Exception as e:
                logger.error("Failed to scan risk", ticker=h.ticker, error=str(e))

        logger.info("Portfolio risk scan complete", alerts_generated=len(generated_alerts))
        return generated_alerts
