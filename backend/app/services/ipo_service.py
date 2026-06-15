"""IPO tracking and intelligence service.

Manages upcoming/listed IPO databases and dynamically computes IPO attractiveness
scores across multi-criteria financial weights.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from app.domain.interfaces.repository import IIPORepository
from app.domain.models.ipo import IPO, IPOFinancials, IPOScore, IPOStatus
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


class IPOService:
    """Manages IPO listings and computes analytical scores."""

    def __init__(self, ipo_repository: IIPORepository) -> None:
        self._repository = ipo_repository

    @timed
    async def get_all_ipos(self) -> list[IPO]:
        ipos = await self._repository.get_all()
        has_real_ipo = any(ipo.name == "Clay Craft India Limited" for ipo in ipos)
        if not ipos or not has_real_ipo:
            logger.info("Resetting/seeding real IPOs to populate closed, open, and upcoming pipeline")
            # Clear all old ones first
            for ipo in ipos:
                await self._repository.delete(ipo.id)
            mock_ipos = self._generate_mock_ipos()
            for ipo in mock_ipos:
                ipo.score = self.calculate_score(ipo.financials, ipo.gmp, ipo.price_band_high)
                await self._repository.save(ipo)
            ipos = await self._repository.get_all()
        return ipos

    async def get_ipo(self, ipo_id: str) -> IPO | None:
        return await self._repository.get_by_id(ipo_id)

    def calculate_score(
        self, financials: IPOFinancials, gmp: float, price_band_high: float
    ) -> IPOScore:
        rev_grow = financials.revenue_growth_yoy
        rev_score = min(10.0, max(0.0, rev_grow * 20.0))

        prof_score = min(10.0, max(0.0, financials.net_profit_margin * 40.0))

        debt = financials.debt_to_equity
        debt_score = max(0.0, min(10.0, 10.0 - (debt * 5.0)))

        pe = financials.pe_ratio
        if pe <= 0:
            val_score = 3.0
        else:
            val_score = max(0.0, min(10.0, 12.0 - (pe * 0.15)))

        sector_score = 7.5

        gmp_pct = (gmp / price_band_high) * 100 if price_band_high > 0 else 0.0
        gmp_score = min(10.0, max(0.0, gmp_pct / 4.0))

        return IPOScore(
            revenue_growth_score=round(rev_score, 1),
            profitability_score=round(prof_score, 1),
            debt_score=round(debt_score, 1),
            valuation_score=round(val_score, 1),
            sector_trend_score=round(sector_score, 1),
            gmp_score=round(gmp_score, 1),
        )

    def _generate_mock_ipos(self) -> list[IPO]:
        today = date.today()
        from datetime import timedelta

        return [
            # 1. Mainboard - Open
            IPO(
                name="Advit Jewels Limited",
                ticker="ADVIT",
                status=IPOStatus.OPEN,
                sector="Consumer Goods",
                industry="Gems & Jewellery",
                ipo_type="mainboard",
                price_band_low=130.0,
                price_band_high=138.0,
                lot_size=100,
                issue_size_cr=400.0,
                fresh_issue_cr=300.0,
                ofs_cr=100.0,
                open_date=today - timedelta(days=1),
                close_date=today + timedelta(days=2),
                listing_date=today + timedelta(days=7),
                gmp=45.0,
                subscription_overall=3.4,
                subscription_qib=2.1,
                subscription_hni=4.5,
                subscription_retail=3.8,
                financials=IPOFinancials(
                    revenue=250.0,
                    revenue_growth_yoy=0.35,
                    net_profit=42.0,
                    net_profit_margin=0.168,
                    ebitda_margin=0.22,
                    debt_to_equity=0.1,
                    roe=0.21,
                    cash_flow_from_operations=38.0,
                    pe_ratio=32.0,
                ),
            ),
            # 2. Mainboard - Upcoming
            IPO(
                name="Turtlemint Fintech Solutions Limited",
                ticker="TURTLEMINT",
                status=IPOStatus.UPCOMING,
                sector="Technology",
                industry="Fintech & Insurtech",
                ipo_type="mainboard",
                price_band_low=220.0,
                price_band_high=240.0,
                lot_size=60,
                issue_size_cr=650.0,
                fresh_issue_cr=650.0,
                ofs_cr=0.0,
                open_date=today + timedelta(days=4),
                close_date=today + timedelta(days=7),
                listing_date=today + timedelta(days=13),
                gmp=65.0,
                subscription_overall=0.0,
                subscription_qib=0.0,
                subscription_hni=0.0,
                subscription_retail=0.0,
                financials=IPOFinancials(
                    revenue=85.0,
                    revenue_growth_yoy=0.72,
                    net_profit=2.1,
                    net_profit_margin=0.024,
                    ebitda_margin=0.08,
                    debt_to_equity=0.6,
                    roe=0.08,
                    cash_flow_from_operations=-1.5,
                    pe_ratio=80.0,
                ),
            ),
            # 3. Mainboard - Listed
            IPO(
                name="Hexagon Nutrition Limited",
                ticker="HEXAGON",
                status=IPOStatus.LISTED,
                sector="Healthcare",
                industry="Nutraceuticals & Wellness",
                ipo_type="mainboard",
                price_band_low=45.0,
                price_band_high=45.0,
                lot_size=300,
                issue_size_cr=150.0,
                fresh_issue_cr=100.0,
                ofs_cr=50.0,
                open_date=today - timedelta(days=10),
                close_date=today - timedelta(days=7),
                listing_date=today - timedelta(days=4),
                gmp=3.25,
                subscription_overall=15.6,
                subscription_qib=25.2,
                subscription_hni=12.4,
                subscription_retail=9.8,
                financials=IPOFinancials(
                    revenue=180.0,
                    revenue_growth_yoy=0.15,
                    net_profit=14.2,
                    net_profit_margin=0.079,
                    ebitda_margin=0.15,
                    debt_to_equity=0.25,
                    roe=0.18,
                    cash_flow_from_operations=18.0,
                    pe_ratio=18.0,
                ),
                listing_price=48.25,
                listing_gain_pct=7.22,
            ),
            # 4. Mainboard - Listed 2
            IPO(
                name="CMR Green Technologies Limited",
                ticker="CMRGREEN",
                status=IPOStatus.LISTED,
                sector="Basic Materials",
                industry="Metal Recycling",
                ipo_type="mainboard",
                price_band_low=192.0,
                price_band_high=192.0,
                lot_size=70,
                issue_size_cr=450.0,
                fresh_issue_cr=350.0,
                ofs_cr=100.0,
                open_date=today - timedelta(days=8),
                close_date=today - timedelta(days=5),
                listing_date=today - timedelta(days=1),
                gmp=76.0,
                subscription_overall=28.5,
                subscription_qib=35.1,
                subscription_hni=22.4,
                subscription_retail=18.2,
                financials=IPOFinancials(
                    revenue=340.0,
                    revenue_growth_yoy=0.29,
                    net_profit=38.0,
                    net_profit_margin=0.11,
                    ebitda_margin=0.18,
                    debt_to_equity=0.45,
                    roe=0.24,
                    cash_flow_from_operations=32.0,
                    pe_ratio=24.0,
                ),
                listing_price=268.0,
                listing_gain_pct=39.58,
            ),
            # 5. Mainboard - Closed
            IPO(
                name="Bagmane Prime Office REIT",
                ticker="BAGMANE",
                status=IPOStatus.CLOSED,
                sector="Real Estate",
                industry="Office Space REIT",
                ipo_type="mainboard",
                price_band_low=100.0,
                price_band_high=100.0,
                lot_size=150,
                issue_size_cr=1200.0,
                fresh_issue_cr=1200.0,
                ofs_cr=0.0,
                open_date=today - timedelta(days=12),
                close_date=today - timedelta(days=9),
                listing_date=today + timedelta(days=1),
                gmp=3.5,
                subscription_overall=1.8,
                subscription_qib=2.5,
                subscription_hni=1.2,
                subscription_retail=1.0,
                financials=IPOFinancials(
                    revenue=95.0,
                    revenue_growth_yoy=0.08,
                    net_profit=12.0,
                    net_profit_margin=0.126,
                    ebitda_margin=0.20,
                    debt_to_equity=0.15,
                    roe=0.15,
                    cash_flow_from_operations=24.0,
                    pe_ratio=15.0,
                ),
            ),
            # 6. SME - Upcoming
            IPO(
                name="Clay Craft India Limited",
                ticker="CLAYCRAFT",
                status=IPOStatus.UPCOMING,
                sector="Consumer Goods",
                industry="Ceramic & Tableware",
                ipo_type="sme",
                price_band_low=193.0,
                price_band_high=203.0,
                lot_size=600,
                issue_size_cr=45.0,
                fresh_issue_cr=45.0,
                ofs_cr=0.0,
                open_date=today + timedelta(days=2),
                close_date=today + timedelta(days=4),
                listing_date=today + timedelta(days=9),
                gmp=85.0,
                subscription_overall=0.0,
                subscription_qib=0.0,
                subscription_hni=0.0,
                subscription_retail=0.0,
                financials=IPOFinancials(
                    revenue=68.0,
                    revenue_growth_yoy=0.28,
                    net_profit=8.5,
                    net_profit_margin=0.125,
                    ebitda_margin=0.18,
                    debt_to_equity=0.3,
                    roe=0.22,
                    cash_flow_from_operations=9.5,
                    pe_ratio=16.5,
                ),
            ),
            # 7. SME - Open
            IPO(
                name="Horizon Reclaim (India) Limited",
                ticker="HORIZON",
                status=IPOStatus.OPEN,
                sector="Basic Materials",
                industry="Reclaimed Rubber & Recycling",
                ipo_type="sme",
                price_band_low=98.0,
                price_band_high=103.0,
                lot_size=1200,
                issue_size_cr=54.27,
                fresh_issue_cr=54.27,
                ofs_cr=0.0,
                open_date=today - timedelta(days=3),
                close_date=today + timedelta(days=1),
                listing_date=today + timedelta(days=7),
                gmp=55.0,
                subscription_overall=8.6,
                subscription_qib=2.1,
                subscription_hni=12.4,
                subscription_retail=10.2,
                financials=IPOFinancials(
                    revenue=112.0,
                    revenue_growth_yoy=0.29,
                    net_profit=9.8,
                    net_profit_margin=0.087,
                    ebitda_margin=0.14,
                    debt_to_equity=0.5,
                    roe=0.18,
                    cash_flow_from_operations=5.6,
                    pe_ratio=18.5,
                ),
            ),
            # 8. SME - Closed
            IPO(
                name="Susan Electricals India Limited",
                ticker="SUSAN",
                status=IPOStatus.CLOSED,
                sector="Consumer Goods",
                industry="Electrical Equipment",
                ipo_type="sme",
                price_band_low=120.0,
                price_band_high=127.0,
                lot_size=1000,
                issue_size_cr=70.38,
                fresh_issue_cr=60.22,
                ofs_cr=10.16,
                open_date=today - timedelta(days=4),
                close_date=today,
                listing_date=today + timedelta(days=5),
                gmp=25.0,
                subscription_overall=12.4,
                subscription_qib=3.5,
                subscription_hni=18.2,
                subscription_retail=15.6,
                financials=IPOFinancials(
                    revenue=145.0,
                    revenue_growth_yoy=0.38,
                    net_profit=12.5,
                    net_profit_margin=0.086,
                    ebitda_margin=0.15,
                    debt_to_equity=0.45,
                    roe=0.22,
                    cash_flow_from_operations=8.4,
                    pe_ratio=24.5,
                ),
            ),
            # 9. SME - Upcoming 2
            IPO(
                name="Diksha Polymers Limited",
                ticker="DIKSHA",
                status=IPOStatus.UPCOMING,
                sector="Basic Materials",
                industry="Plastic Polymers",
                ipo_type="sme",
                price_band_low=112.0,
                price_band_high=112.0,
                lot_size=1200,
                issue_size_cr=30.0,
                fresh_issue_cr=30.0,
                ofs_cr=0.0,
                open_date=today + timedelta(days=2),
                close_date=today + timedelta(days=4),
                listing_date=today + timedelta(days=9),
                gmp=18.0,
                subscription_overall=0.0,
                subscription_qib=0.0,
                subscription_hni=0.0,
                subscription_retail=0.0,
                financials=IPOFinancials(
                    revenue=48.0,
                    revenue_growth_yoy=0.18,
                    net_profit=3.2,
                    net_profit_margin=0.066,
                    ebitda_margin=0.12,
                    debt_to_equity=0.2,
                    roe=0.16,
                    cash_flow_from_operations=3.5,
                    pe_ratio=15.0,
                ),
            ),
            # 10. SME - Listed
            IPO(
                name="Utkal Speciality Industries Limited",
                ticker="UTKAL",
                status=IPOStatus.LISTED,
                sector="Basic Materials",
                industry="Industrial Specialities",
                ipo_type="sme",
                price_band_low=60.0,
                price_band_high=65.0,
                lot_size=2000,
                issue_size_cr=35.2,
                fresh_issue_cr=35.2,
                ofs_cr=0.0,
                open_date=today - timedelta(days=5),
                close_date=today - timedelta(days=3),
                listing_date=today - timedelta(days=1),
                gmp=15.0,
                subscription_overall=1.57,
                subscription_qib=1.0,
                subscription_hni=1.2,
                subscription_retail=2.1,
                financials=IPOFinancials(
                    revenue=42.0,
                    revenue_growth_yoy=0.22,
                    net_profit=3.8,
                    net_profit_margin=0.09,
                    ebitda_margin=0.12,
                    debt_to_equity=0.25,
                    roe=0.15,
                    cash_flow_from_operations=3.1,
                    pe_ratio=12.5,
                ),
                listing_price=80.0,
                listing_gain_pct=23.0,
            ),
        ]
