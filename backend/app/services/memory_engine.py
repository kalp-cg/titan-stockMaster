"""
Memory Engine — Historical Analogy Search

Maintains a curated corpus of ~50 high-impact market events from Indian
and global history, each pre-embedded as a dense vector.

Algorithm:
  1. On startup: embed all corpus events (one-time, ~5 seconds)
  2. On new event: cosine-search corpus → top-5 analogies
  3. Return weighted average expected impact and sector playbook

Design principle: Seeded in code — admin can extend via API later.
"""

from __future__ import annotations

import numpy as np
from typing import Any

from app.domain.models.memory import (
    HistoricalAnalogy,
    HistoricalAnalysisResult,
    HistoricalEvent,
    HistoricalMarketImpact,
)
from app.utils.logging import get_logger
from app.utils.timing import timed

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# HISTORICAL EVENT CORPUS
# ~50 curated high-impact events (Indian + Global, 1991–2025)
# ---------------------------------------------------------------------------

RAW_CORPUS = [
    # ── Indian Economic/Policy Events ──────────────────────────────────────
    {
        "id": "hist_001", "year": 1991, "title": "India Balance of Payments Crisis & LPG Reforms",
        "category": "economic",
        "description": "India's foreign exchange reserves fell to near-zero. IMF bailout and historic economic liberalisation began under Manmohan Singh.",
        "keywords": ["forex", "reserves", "imf", "liberalisation", "reforms", "crisis"],
        "impact": {"nifty_30d": -8.0, "nifty_60d": 12.0,
                   "best": ["technology", "consumer_fmcg"], "worst": ["banking_finance", "infrastructure"],
                   "sectors": {"technology": 15, "banking_finance": -12}}
    },
    {
        "id": "hist_002", "year": 2008, "title": "Global Financial Crisis — Lehman Brothers Collapse",
        "category": "geopolitical",
        "description": "Lehman Brothers filed for bankruptcy. Global credit markets froze. Indian markets crashed 60% peak-to-trough.",
        "keywords": ["lehman", "bankruptcy", "credit", "crisis", "recession", "bank", "global"],
        "impact": {"nifty_30d": -25.0, "nifty_60d": -35.0,
                   "best": ["gold"], "worst": ["banking_finance", "real_estate", "technology"],
                   "sectors": {"banking_finance": -40, "technology": -35, "metals_mining": -30}}
    },
    {
        "id": "hist_003", "year": 2016, "title": "India Demonetization — ₹500 and ₹1000 Notes Banned",
        "category": "regulatory",
        "description": "PM Modi announced overnight cancellation of ₹500 and ₹1000 currency notes, removing 86% of cash in circulation.",
        "keywords": ["demonetization", "currency", "cash", "ban", "modi", "rbi", "notes"],
        "impact": {"nifty_30d": -8.0, "nifty_60d": -5.0,
                   "best": ["banking_finance", "fintech"], "worst": ["consumer_fmcg", "jewellery", "real_estate"],
                   "sectors": {"banking_finance": 5, "consumer_fmcg": -15, "jewellery": -25}}
    },
    {
        "id": "hist_004", "year": 2019, "title": "India Corporate Tax Cut — Rate Slashed to 22%",
        "category": "regulatory",
        "description": "FM Nirmala Sitharaman announced surprise cut in corporate tax rate from 30% to 22%, and new manufacturing firms to 15%.",
        "keywords": ["tax", "corporate", "rate", "cut", "fiscal", "stimulus", "manufacturing"],
        "impact": {"nifty_30d": 5.0, "nifty_60d": 8.0,
                   "best": ["automobiles", "metals_mining", "consumer_fmcg"], "worst": [],
                   "sectors": {"automobiles": 12, "banking_finance": 8, "consumer_fmcg": 6}}
    },
    {
        "id": "hist_005", "year": 2020, "title": "COVID-19 India Lockdown Announced",
        "category": "geopolitical",
        "description": "India imposed one of the world's strictest lockdowns. Economy came to a standstill. Markets crashed 40%.",
        "keywords": ["covid", "pandemic", "lockdown", "virus", "health", "shutdown", "corona"],
        "impact": {"nifty_30d": -28.0, "nifty_60d": -15.0,
                   "best": ["pharmaceuticals", "technology"], "worst": ["aviation", "hospitality", "retail"],
                   "sectors": {"pharmaceuticals": 20, "technology": 10, "aviation": -55, "hospitality": -50}}
    },
    {
        "id": "hist_006", "year": 2020, "title": "COVID Vaccine Announcement — Phase 3 Success (Pfizer)",
        "category": "economic",
        "description": "Pfizer announced 90% efficacy in Phase 3 trials. Global markets rallied sharply. Reopening trade began.",
        "keywords": ["vaccine", "covid", "pfizer", "recovery", "reopening", "immunity", "trial"],
        "impact": {"nifty_30d": 10.0, "nifty_60d": 18.0,
                   "best": ["aviation", "hospitality", "consumer_fmcg"], "worst": ["pharmaceuticals"],
                   "sectors": {"aviation": 20, "hospitality": 25, "pharmaceuticals": -10}}
    },
    {
        "id": "hist_007", "year": 2021, "title": "India Union Budget — Record Infrastructure Capex ₹5.54 Lakh Cr",
        "category": "regulatory",
        "description": "FM announced record capital expenditure for infrastructure. Roads, railways, defence manufacturing benefited.",
        "keywords": ["budget", "capex", "infrastructure", "roads", "railways", "defence", "spending"],
        "impact": {"nifty_30d": 3.0, "nifty_60d": 7.0,
                   "best": ["infrastructure", "defense_aerospace", "cement", "metals_mining"], "worst": [],
                   "sectors": {"infrastructure": 15, "defense_aerospace": 18, "cement": 10}}
    },
    {
        "id": "hist_008", "year": 2023, "title": "Adani Group Hindenburg Short Report",
        "category": "company",
        "description": "US short-seller Hindenburg Research published a damning report on Adani Group, alleging fraud and stock manipulation.",
        "keywords": ["adani", "hindenburg", "short", "fraud", "manipulation", "report", "conglomerate"],
        "impact": {"nifty_30d": -5.0, "nifty_60d": -2.0,
                   "best": ["banking_finance"], "worst": ["infrastructure", "energy_utilities"],
                   "sectors": {"infrastructure": -20, "energy_utilities": -15}}
    },
    {
        "id": "hist_009", "year": 2019, "title": "India-Pakistan Balakot Air Strike Tension",
        "category": "geopolitical",
        "description": "India conducted air strikes in Balakot after Pulwama terror attack. Military escalation feared. Markets initially fell then recovered.",
        "keywords": ["pakistan", "india", "airstrip", "military", "war", "tension", "geopolitical", "defence"],
        "impact": {"nifty_30d": -3.0, "nifty_60d": 5.0,
                   "best": ["defense_aerospace"], "worst": ["aviation", "banking_finance"],
                   "sectors": {"defense_aerospace": 8, "aviation": -6}}
    },
    {
        "id": "hist_010", "year": 2022, "title": "Russia-Ukraine War Begins",
        "category": "geopolitical",
        "description": "Russia launched full-scale invasion of Ukraine. Crude oil spiked to $130. European gas crisis followed. Inflation surged globally.",
        "keywords": ["russia", "ukraine", "war", "oil", "crude", "gas", "inflation", "invasion", "conflict"],
        "impact": {"nifty_30d": -8.0, "nifty_60d": -4.0,
                   "best": ["energy_utilities", "defense_aerospace", "metals_mining"], "worst": ["aviation", "paints", "consumer_fmcg"],
                   "sectors": {"energy_utilities": 15, "defense_aerospace": 12, "aviation": -20, "paints": -18}}
    },
    {
        "id": "hist_011", "year": 2022, "title": "US Federal Reserve — Fastest Rate Hike Cycle in 40 Years",
        "category": "economic",
        "description": "Fed raised rates 11 times in 18 months, from 0.25% to 5.5%. FII outflows from emerging markets including India exceeded ₹2 lakh crore.",
        "keywords": ["fed", "interest", "rate", "hike", "fii", "outflow", "dollar", "inflation", "powell"],
        "impact": {"nifty_30d": -7.0, "nifty_60d": -5.0,
                   "best": ["banking_finance"], "worst": ["technology", "real_estate"],
                   "sectors": {"banking_finance": 5, "technology": -15, "real_estate": -12}}
    },
    {
        "id": "hist_012", "year": 2014, "title": "Narendra Modi — BJP Wins Landslide General Election",
        "category": "regulatory",
        "description": "BJP won 282 seats, first single-party majority in 30 years. Markets surged on reform hopes and Modi premium.",
        "keywords": ["modi", "bjp", "election", "majority", "reform", "government", "mandate"],
        "impact": {"nifty_30d": 8.0, "nifty_60d": 15.0,
                   "best": ["infrastructure", "defense_aerospace", "banking_finance"], "worst": [],
                   "sectors": {"infrastructure": 20, "defense_aerospace": 15, "banking_finance": 12}}
    },
    {
        "id": "hist_013", "year": 2024, "title": "India General Election — NDA Wins But with Reduced Majority",
        "category": "regulatory",
        "description": "BJP won 240 seats, below 272 majority. Coalition government formed. Markets fell sharply on election day results, then recovered.",
        "keywords": ["election", "modi", "bjp", "nda", "coalition", "majority", "result", "vote"],
        "impact": {"nifty_30d": -2.0, "nifty_60d": 5.0,
                   "best": ["consumer_fmcg", "pharmaceuticals"], "worst": ["defense_aerospace", "infrastructure"],
                   "sectors": {"consumer_fmcg": 6, "defense_aerospace": -8}}
    },
    {
        "id": "hist_014", "year": 2013, "title": "Taper Tantrum — Ben Bernanke Fed Tapering Announcement",
        "category": "economic",
        "description": "Fed signaled end of quantitative easing. Rupee crashed to 68. FII outflows were severe. Indian market fell 15% in weeks.",
        "keywords": ["fed", "taper", "qe", "dollar", "rupee", "outflow", "bernanke", "liquidity", "emerging market"],
        "impact": {"nifty_30d": -12.0, "nifty_60d": -8.0,
                   "best": ["it_exports"], "worst": ["real_estate", "banking_finance"],
                   "sectors": {"technology": 8, "banking_finance": -15, "real_estate": -20}}
    },
    {
        "id": "hist_015", "year": 2020, "title": "India-China Galwan Valley Military Clash",
        "category": "geopolitical",
        "description": "Indian and Chinese soldiers clashed in Galwan Valley, Ladakh. 20 Indian soldiers killed. Boycott China sentiment surged.",
        "keywords": ["china", "india", "border", "military", "galwan", "clash", "ladakh", "defence"],
        "impact": {"nifty_30d": -3.0, "nifty_60d": 4.0,
                   "best": ["defense_aerospace", "pharmaceuticals"], "worst": ["consumer_fmcg"],
                   "sectors": {"defense_aerospace": 10, "pharmaceuticals": 6}}
    },
    {
        "id": "hist_016", "year": 2023, "title": "Silicon Valley Bank Collapse",
        "category": "economic",
        "description": "SVB failed in 48 hours — fastest bank run in history. US regional banking crisis spread. Global risk-off sentiment.",
        "keywords": ["bank", "failure", "svb", "deposits", "crisis", "fintech", "startup", "liquidity"],
        "impact": {"nifty_30d": -3.0, "nifty_60d": 2.0,
                   "best": ["large_cap_banks"], "worst": ["technology", "startup"],
                   "sectors": {"banking_finance": -5, "technology": -8}}
    },
    {
        "id": "hist_017", "year": 2020, "title": "Crude Oil Price Goes Negative — WTI Futures",
        "category": "economic",
        "description": "WTI crude futures traded at -$37/barrel for the first time in history due to storage crisis and demand collapse.",
        "keywords": ["oil", "crude", "negative", "wti", "storage", "demand", "opec", "energy"],
        "impact": {"nifty_30d": -5.0, "nifty_60d": 3.0,
                   "best": ["aviation", "paints", "consumer_fmcg"], "worst": ["energy_utilities"],
                   "sectors": {"aviation": 8, "paints": 6, "energy_utilities": -20}}
    },
    {
        "id": "hist_018", "year": 2021, "title": "India Second COVID Wave — Healthcare System Overwhelmed",
        "category": "geopolitical",
        "description": "India's second COVID wave caused 4 lakh daily cases. Oxygen shortage. Partial lockdowns. Market fell on economic fear.",
        "keywords": ["covid", "wave", "lockdown", "health", "oxygen", "hospital", "pandemic"],
        "impact": {"nifty_30d": -4.0, "nifty_60d": 6.0,
                   "best": ["pharmaceuticals", "technology"], "worst": ["aviation", "hospitality"],
                   "sectors": {"pharmaceuticals": 12, "technology": 5, "aviation": -15}}
    },
    {
        "id": "hist_019", "year": 2018, "title": "IL&FS Default — NBFC Liquidity Crisis India",
        "category": "economic",
        "description": "Infrastructure Leasing & Financial Services defaulted on ₹91,000 crore debt. NBFC sector frozen. Mutual fund redemption fears.",
        "keywords": ["nbfc", "default", "credit", "liquidity", "debt", "ilfs", "crisis", "shadow bank"],
        "impact": {"nifty_30d": -8.0, "nifty_60d": -5.0,
                   "best": [], "worst": ["banking_finance", "real_estate", "infrastructure"],
                   "sectors": {"banking_finance": -15, "real_estate": -20, "infrastructure": -12}}
    },
    {
        "id": "hist_020", "year": 2011, "title": "India Anti-Corruption Movement — Anna Hazare Fast",
        "category": "regulatory",
        "description": "Anna Hazare's hunger strike demanded Lokpal Bill. Political uncertainty. Foreign investors concerned about governance.",
        "keywords": ["corruption", "government", "reform", "lokpal", "anna", "political", "governance"],
        "impact": {"nifty_30d": -4.0, "nifty_60d": -2.0,
                   "best": [], "worst": ["banking_finance", "infrastructure"],
                   "sectors": {"banking_finance": -5, "infrastructure": -8}}
    },
    {
        "id": "hist_021", "year": 2017, "title": "GST Implementation in India",
        "category": "regulatory",
        "description": "Goods and Services Tax launched July 1, 2017. Replaced 17 central and state taxes. Short-term disruption; long-term positive.",
        "keywords": ["gst", "tax", "reform", "goods", "services", "indirect", "consumption"],
        "impact": {"nifty_30d": 2.0, "nifty_60d": 4.0,
                   "best": ["consumer_fmcg", "logistics"], "worst": ["jewellery", "real_estate"],
                   "sectors": {"consumer_fmcg": 5, "logistics": 8, "jewellery": -6}}
    },
    {
        "id": "hist_022", "year": 2015, "title": "China Stock Market Crash — Shanghai Composite Falls 45%",
        "category": "economic",
        "description": "China's bubble burst. Shanghai fell 45% in 3 months. FII outflows from all emerging markets. India fell 15%.",
        "keywords": ["china", "market", "crash", "bubble", "emerging", "outflow", "commodity"],
        "impact": {"nifty_30d": -10.0, "nifty_60d": -12.0,
                   "best": [], "worst": ["metals_mining", "energy_utilities", "banking_finance"],
                   "sectors": {"metals_mining": -25, "energy_utilities": -20}}
    },
    {
        "id": "hist_023", "year": 2024, "title": "US Presidential Election — Trump Wins",
        "category": "geopolitical",
        "description": "Donald Trump won 2024 US Presidential election. Tariff expectations surged. Dollar strengthened. Tech and defense outperformed.",
        "keywords": ["trump", "election", "tariff", "dollar", "us", "president", "policy", "trade"],
        "impact": {"nifty_30d": -2.0, "nifty_60d": 3.0,
                   "best": ["defense_aerospace", "it_exports"], "worst": ["consumer_fmcg", "pharmaceuticals"],
                   "sectors": {"defense_aerospace": 10, "technology": 6, "pharmaceuticals": -8}}
    },
    {
        "id": "hist_024", "year": 2019, "title": "RBI Repo Rate Cut Cycle Begins — 135 bps in 2019",
        "category": "economic",
        "description": "RBI cut repo rate five times in 2019, total 135 bps. Liquidity improved. Real estate and NBFCs benefited.",
        "keywords": ["rbi", "rate", "cut", "repo", "interest", "liquidity", "monetary", "easing"],
        "impact": {"nifty_30d": 3.0, "nifty_60d": 6.0,
                   "best": ["banking_finance", "real_estate", "infrastructure"], "worst": [],
                   "sectors": {"banking_finance": 8, "real_estate": 6, "infrastructure": 5}}
    },
    {
        "id": "hist_025", "year": 2022, "title": "India RBI Emergency Rate Hike — Off-Cycle 40 bps",
        "category": "economic",
        "description": "RBI convened an emergency MPC meeting and hiked repo by 40 bps to combat inflation. Markets fell sharply.",
        "keywords": ["rbi", "rate", "hike", "emergency", "inflation", "repo", "monetary", "mpc"],
        "impact": {"nifty_30d": -4.0, "nifty_60d": -2.0,
                   "best": [], "worst": ["real_estate", "banking_finance", "consumer"],
                   "sectors": {"real_estate": -8, "banking_finance": -6}}
    },
    {
        "id": "hist_026", "year": 2005, "title": "India — Sensex Crosses 10,000 for First Time",
        "category": "economic",
        "description": "BSE Sensex crossed 10,000 points for first time, driven by FII inflows, strong GDP growth, and technology boom.",
        "keywords": ["sensex", "bull", "market", "rally", "growth", "fii", "inflow", "milestone"],
        "impact": {"nifty_30d": 5.0, "nifty_60d": 10.0,
                   "best": ["technology", "banking_finance"], "worst": [],
                   "sectors": {"technology": 15, "banking_finance": 12}}
    },
    {
        "id": "hist_027", "year": 2001, "title": "9/11 Attacks — US Terror Attack",
        "category": "geopolitical",
        "description": "Al-Qaeda attacks on World Trade Center. Global markets halted and crashed. Aviation sector devastated.",
        "keywords": ["terror", "attack", "war", "geopolitical", "us", "security", "oil", "aviation"],
        "impact": {"nifty_30d": -12.0, "nifty_60d": -8.0,
                   "best": ["defense_aerospace"], "worst": ["aviation", "tourism", "insurance"],
                   "sectors": {"defense_aerospace": 15, "aviation": -40}}
    },
    {
        "id": "hist_028", "year": 2003, "title": "Iraq War Begins — US Invasion",
        "category": "geopolitical",
        "description": "US-led coalition invaded Iraq. Oil markets volatile. Defense spending surged. Global uncertainty.",
        "keywords": ["iraq", "war", "oil", "us", "invasion", "military", "crude", "defense"],
        "impact": {"nifty_30d": 3.0, "nifty_60d": 8.0,
                   "best": ["energy_utilities", "defense_aerospace"], "worst": ["aviation"],
                   "sectors": {"energy_utilities": 12, "defense_aerospace": 10, "aviation": -8}}
    },
    {
        "id": "hist_029", "year": 2020, "title": "India Telecom Sector AGR Crisis — SC Ruling",
        "category": "regulatory",
        "description": "Supreme Court upheld AGR dues of ₹1.3 lakh crore for telecom companies. Vodafone-Idea near collapse.",
        "keywords": ["telecom", "agr", "court", "spectrum", "vodafone", "airtel", "debt", "regulatory"],
        "impact": {"nifty_30d": -2.0, "nifty_60d": 1.0,
                   "best": ["reliance_jio"], "worst": ["telecom"],
                   "sectors": {"technology": 3}}
    },
    {
        "id": "hist_030", "year": 2021, "title": "Crypto Market Crash — Bitcoin Falls 50% from ATH",
        "category": "economic",
        "description": "Bitcoin fell from $65,000 to $30,000. Crypto regulatory fears. Risk-off sentiment impacted growth stocks.",
        "keywords": ["crypto", "bitcoin", "blockchain", "digital", "currency", "crash", "regulation"],
        "impact": {"nifty_30d": -2.0, "nifty_60d": 1.0,
                   "best": [], "worst": ["technology"],
                   "sectors": {"technology": -5}}
    },
    {
        "id": "hist_031", "year": 2022, "title": "India-Canada Diplomatic Row — Trade Tension",
        "category": "geopolitical",
        "description": "Relations between India and Canada deteriorated over Sikh separatism allegations. Trade talks stalled.",
        "keywords": ["canada", "india", "diplomatic", "trade", "tension", "relations", "exports"],
        "impact": {"nifty_30d": -0.5, "nifty_60d": 0.5,
                   "best": [], "worst": [],
                   "sectors": {}}
    },
    {
        "id": "hist_032", "year": 2023, "title": "India G20 Presidency — New Delhi Summit",
        "category": "regulatory",
        "description": "India hosted G20 Summit in New Delhi. Diplomatic wins. Digital public infrastructure highlighted globally.",
        "keywords": ["g20", "india", "summit", "diplomacy", "trade", "global", "presidency"],
        "impact": {"nifty_30d": 2.0, "nifty_60d": 4.0,
                   "best": ["technology", "infrastructure", "tourism"], "worst": [],
                   "sectors": {"technology": 5, "infrastructure": 4}}
    },
    {
        "id": "hist_033", "year": 2021, "title": "Suez Canal Blocked — Ever Given Container Ship",
        "category": "geopolitical",
        "description": "Container ship blocked Suez Canal for 6 days. Global supply chain disrupted. Shipping costs surged.",
        "keywords": ["suez", "canal", "shipping", "supply", "chain", "container", "logistics", "trade"],
        "impact": {"nifty_30d": 0.5, "nifty_60d": 1.0,
                   "best": ["logistics", "shipping"], "worst": ["consumer_fmcg"],
                   "sectors": {"logistics": 8}}
    },
    {
        "id": "hist_034", "year": 2024, "title": "Iran-Israel Direct Military Exchange",
        "category": "geopolitical",
        "description": "Iran launched 300+ drones and missiles at Israel. Israel retaliated. Regional escalation feared. Oil and gold spiked.",
        "keywords": ["iran", "israel", "war", "middle", "east", "oil", "drone", "missile", "conflict", "gold"],
        "impact": {"nifty_30d": -3.0, "nifty_60d": -1.0,
                   "best": ["defense_aerospace", "energy_utilities"], "worst": ["aviation", "consumer"],
                   "sectors": {"defense_aerospace": 8, "energy_utilities": 10, "aviation": -12}}
    },
    {
        "id": "hist_035", "year": 2020, "title": "India Atmanirbhar Bharat Stimulus Package — ₹20 Lakh Cr",
        "category": "regulatory",
        "description": "PM Modi announced ₹20 lakh crore economic stimulus. Focus on self-reliance, manufacturing, MSMEs, agriculture.",
        "keywords": ["atmanirbhar", "stimulus", "manufacturing", "msme", "relief", "package", "fiscal"],
        "impact": {"nifty_30d": 5.0, "nifty_60d": 10.0,
                   "best": ["manufacturing", "infrastructure", "consumer_fmcg"], "worst": [],
                   "sectors": {"infrastructure": 10, "consumer_fmcg": 8, "pharmaceuticals": 6}}
    },
    {
        "id": "hist_036", "year": 2023, "title": "AI Boom — ChatGPT Triggers Global Tech Rally",
        "category": "economic",
        "description": "ChatGPT reached 100 million users in 2 months. AI investment boom began. NVIDIA, Microsoft surged. Indian IT benefited.",
        "keywords": ["ai", "chatgpt", "artificial", "intelligence", "technology", "nvidia", "software", "it"],
        "impact": {"nifty_30d": 3.0, "nifty_60d": 7.0,
                   "best": ["technology"], "worst": [],
                   "sectors": {"technology": 15}}
    },
    {
        "id": "hist_037", "year": 2025, "title": "US Reciprocal Tariffs on India — April 2025",
        "category": "geopolitical",
        "description": "Trump announced 26% reciprocal tariffs on Indian goods. Markets fell sharply. IT exports and pharma most at risk.",
        "keywords": ["tariff", "trump", "us", "india", "trade", "export", "import", "duty", "reciprocal"],
        "impact": {"nifty_30d": -8.0, "nifty_60d": -3.0,
                   "best": [], "worst": ["pharmaceuticals", "technology", "consumer_fmcg"],
                   "sectors": {"pharmaceuticals": -12, "technology": -10}}
    },
    {
        "id": "hist_038", "year": 2019, "title": "India Budget — Surcharge on Super-Rich Triggers FII Sell-off",
        "category": "regulatory",
        "description": "FM announced surcharge on FPI structured as trusts and AOP. FIIs sold ₹70,000 crore. Nifty fell 6% in weeks.",
        "keywords": ["budget", "tax", "surcharge", "fii", "sell", "outflow", "fiscal", "foreigninvestors"],
        "impact": {"nifty_30d": -6.0, "nifty_60d": -4.0,
                   "best": [], "worst": ["banking_finance", "technology"],
                   "sectors": {"banking_finance": -8, "technology": -7}}
    },
    {
        "id": "hist_039", "year": 2004, "title": "UPA Election Win — Congress Shocks Markets",
        "category": "regulatory",
        "description": "Congress-led UPA won unexpectedly. NDA lost despite India Shining campaign. Markets hit lower circuit. Recovered in months.",
        "keywords": ["election", "congress", "shock", "circuit", "upa", "policy", "government", "surprise"],
        "impact": {"nifty_30d": -8.0, "nifty_60d": 5.0,
                   "best": [], "worst": [],
                   "sectors": {}}
    },
    {
        "id": "hist_040", "year": 2021, "title": "Zomato IPO — India New-Age Tech Company Boom",
        "category": "economic",
        "description": "Zomato's IPO subscribed 38x. Listed at 51% premium. Marked the beginning of India's startup IPO supercycle.",
        "keywords": ["ipo", "zomato", "startup", "listing", "tech", "new", "age", "subscription"],
        "impact": {"nifty_30d": 2.0, "nifty_60d": 4.0,
                   "best": ["technology", "consumer"], "worst": [],
                   "sectors": {"technology": 5}}
    },
    {
        "id": "hist_041", "year": 2022, "title": "India Wheat Export Ban — Food Security Crisis",
        "category": "regulatory",
        "description": "India banned wheat exports after heat wave destroyed crops and global shortage due to Ukraine war. Food inflation surged.",
        "keywords": ["wheat", "export", "ban", "food", "inflation", "agriculture", "crop", "shortage"],
        "impact": {"nifty_30d": -1.0, "nifty_60d": 0.5,
                   "best": ["agriculture"], "worst": ["consumer_fmcg"],
                   "sectors": {"consumer_fmcg": -5}}
    },
    {
        "id": "hist_042", "year": 2014, "title": "Oil Price Crash — Brent Falls from $115 to $50",
        "category": "economic",
        "description": "OPEC refused to cut production. Oil fell 55% in 6 months. Oil importers like India benefited massively. CAD improved.",
        "keywords": ["oil", "crude", "fall", "opec", "brent", "price", "drop", "energy", "deficit"],
        "impact": {"nifty_30d": 4.0, "nifty_60d": 8.0,
                   "best": ["aviation", "paints", "consumer_fmcg", "consumer"], "worst": ["energy_utilities"],
                   "sectors": {"aviation": 15, "paints": 12, "consumer_fmcg": 8, "energy_utilities": -20}}
    },
    {
        "id": "hist_043", "year": 2023, "title": "India-China Trade Normalization Signals",
        "category": "geopolitical",
        "description": "Gradual diplomatic thaw between India and China. Business visas resumed. Tech collaboration discussions started.",
        "keywords": ["china", "india", "trade", "normalization", "diplomatic", "thaw", "bilateral"],
        "impact": {"nifty_30d": 1.5, "nifty_60d": 3.0,
                   "best": ["technology", "consumer_fmcg"], "worst": [],
                   "sectors": {"technology": 4, "consumer_fmcg": 3}}
    },
    {
        "id": "hist_044", "year": 2023, "title": "Chandrayaan-3 Mission Success — India on Moon",
        "category": "regulatory",
        "description": "India became 4th country to land on Moon. ISRO's Vikram lander touched down near South Pole. Space sector enthusiasm surged.",
        "keywords": ["isro", "chandrayaan", "moon", "space", "science", "technology", "india", "mission"],
        "impact": {"nifty_30d": 2.0, "nifty_60d": 3.0,
                   "best": ["defense_aerospace", "technology"], "worst": [],
                   "sectors": {"defense_aerospace": 5, "technology": 3}}
    },
    {
        "id": "hist_045", "year": 2016, "title": "Brexit Vote — UK Votes to Leave EU",
        "category": "geopolitical",
        "description": "UK voted 52-48 to leave EU. Sterling crashed. Global markets fell. Indian IT with UK exposure impacted.",
        "keywords": ["brexit", "uk", "eu", "europe", "referendum", "pound", "sterling", "trade"],
        "impact": {"nifty_30d": -3.0, "nifty_60d": 1.0,
                   "best": [], "worst": ["technology"],
                   "sectors": {"technology": -6}}
    },
    {
        "id": "hist_046", "year": 2025, "title": "India-Pakistan Pahalgam Terror Attack Military Escalation",
        "category": "geopolitical",
        "description": "Terror attack in Pahalgam killed 26 tourists. India launched Operation Sindoor targeting Pakistan terror camps. Ceasefire followed.",
        "keywords": ["pakistan", "india", "terror", "military", "attack", "war", "operation", "ceasefire", "border"],
        "impact": {"nifty_30d": -2.0, "nifty_60d": 3.0,
                   "best": ["defense_aerospace"], "worst": ["aviation", "tourism"],
                   "sectors": {"defense_aerospace": 12, "aviation": -8}}
    },
    {
        "id": "hist_047", "year": 2024, "title": "RBI MPC — Pause Cycle Ends, Rate Cut Begins",
        "category": "economic",
        "description": "RBI began rate cutting cycle after 18 months of pause. Repo cut 25 bps to 6.25%. Growth-supportive stance.",
        "keywords": ["rbi", "rate", "cut", "repo", "mpc", "easing", "monetary", "growth", "policy"],
        "impact": {"nifty_30d": 2.5, "nifty_60d": 5.0,
                   "best": ["banking_finance", "real_estate", "consumer"], "worst": [],
                   "sectors": {"banking_finance": 6, "real_estate": 5, "consumer_fmcg": 4}}
    },
    {
        "id": "hist_048", "year": 2020, "title": "Reliance Jio — Rights Issue & Meta Investment",
        "category": "company",
        "description": "Reliance raised ₹1.5 lakh crore via rights issue and strategic investments from Facebook, Google, KKR. India's largest ever equity raise.",
        "keywords": ["reliance", "jio", "facebook", "google", "investment", "fundraise", "rights", "issue"],
        "impact": {"nifty_30d": 4.0, "nifty_60d": 8.0,
                   "best": ["technology", "consumer"], "worst": [],
                   "sectors": {"technology": 8, "consumer_fmcg": 5}}
    },
    {
        "id": "hist_049", "year": 2007, "title": "Global Commodity Super-Cycle Peak",
        "category": "economic",
        "description": "Commodity prices hit all-time highs. Crude at $147, metals at peaks. Emerging market boom fueled by China demand.",
        "keywords": ["commodity", "super", "cycle", "crude", "metal", "china", "demand", "peak", "raw material"],
        "impact": {"nifty_30d": 3.0, "nifty_60d": 5.0,
                   "best": ["metals_mining", "energy_utilities"], "worst": ["consumer_fmcg", "aviation"],
                   "sectors": {"metals_mining": 20, "energy_utilities": 15, "aviation": -10}}
    },
    {
        "id": "hist_050", "year": 2021, "title": "India PLI Scheme — Production Linked Incentive for 13 Sectors",
        "category": "regulatory",
        "description": "India announced PLI scheme for mobile phones, pharma, solar, food processing, auto, textiles. ₹1.97 lakh crore incentive pool.",
        "keywords": ["pli", "manufacturing", "production", "incentive", "atmanirbhar", "export", "mobile", "pharma"],
        "impact": {"nifty_30d": 3.0, "nifty_60d": 6.0,
                   "best": ["pharmaceuticals", "technology", "consumer_fmcg", "automobiles"], "worst": [],
                   "sectors": {"pharmaceuticals": 8, "automobiles": 7, "technology": 6}}
    },
]


class MemoryEngine:
    """
    Searches historical event corpus for analogies to current events.

    Uses the platform's existing SimilarityEngine (FAISS or in-memory
    cosine search) to find top-K historically similar events and returns
    expected market impact based on what happened after those events.
    """

    def __init__(self, embedder: Any, similarity_engine: Any) -> None:
        self._embedder = embedder
        self._similarity = similarity_engine
        self._corpus: list[HistoricalEvent] = []
        self._embedded = False

    def initialize(self) -> None:
        """
        Pre-embed all corpus events.
        Call once at application startup. Runs synchronously — takes ~3 seconds.
        """
        if self._embedded:
            return

        logger.info("MemoryEngine: embedding historical corpus", count=len(RAW_CORPUS))
        for raw in RAW_CORPUS:
            # Build a rich text representation for embedding
            text = f"{raw['title']}. {raw['description']}. Keywords: {', '.join(raw['keywords'])}"
            try:
                embedding = self._embedder.embed(text)
            except Exception as e:
                logger.warning("Failed to embed historical event", id=raw["id"], error=str(e))
                embedding = []

            impact_data = raw["impact"]
            event = HistoricalEvent(
                id=raw["id"],
                year=raw["year"],
                title=raw["title"],
                description=raw["description"],
                category=raw["category"],
                keywords=raw["keywords"],
                embedding=embedding,
                market_impact=HistoricalMarketImpact(
                    nifty_30d=impact_data["nifty_30d"],
                    nifty_60d=impact_data["nifty_60d"],
                    best_sectors=impact_data.get("best", []),
                    worst_sectors=impact_data.get("worst", []),
                    sector_impacts=impact_data.get("sectors", {}),
                ),
            )
            self._corpus.append(event)

            # Store in vector store for fast future retrieval
            if embedding:
                try:
                    self._similarity.store_embedding(
                        f"hist_{raw['id']}",
                        embedding,
                        metadata={"title": raw["title"], "year": raw["year"], "type": "historical"}
                    )
                except Exception:
                    pass  # Corpus still usable even if vector store fails

        self._embedded = True
        logger.info("MemoryEngine: corpus ready", events=len(self._corpus))

    @timed
    def find_analogies(self, event_text: str, k: int = 5) -> HistoricalAnalysisResult:
        """
        Find top-k historically similar events using cosine similarity.
        Returns weighted expected impact across all analogies.
        """
        if not self._embedded or not self._corpus:
            return self._empty_result(event_text)

        try:
            query_embedding = self._embedder.embed(event_text)
        except Exception as e:
            logger.warning("MemoryEngine: embedding failed for query", error=str(e))
            return self._empty_result(event_text)

        # Manual cosine search across corpus (deterministic, no external dep)
        scored: list[tuple[float, HistoricalEvent]] = []
        query_arr = np.array(query_embedding)
        query_norm = np.linalg.norm(query_arr)
        if query_norm == 0:
            return self._empty_result(event_text)

        for hist_event in self._corpus:
            if not hist_event.embedding:
                continue
            hist_arr = np.array(hist_event.embedding)
            hist_norm = np.linalg.norm(hist_arr)
            if hist_norm == 0:
                continue
            cosine = float(np.dot(query_arr, hist_arr) / (query_norm * hist_norm))
            scored.append((cosine, hist_event))

        # Top-k by similarity
        scored.sort(key=lambda x: x[0], reverse=True)
        top_k = scored[:k]

        if not top_k:
            return self._empty_result(event_text)

        analogies: list[HistoricalAnalogy] = []
        for sim_score, h in top_k:
            if sim_score < 0.3:  # Threshold — below this, too different
                break
            analogies.append(HistoricalAnalogy(
                event_id=h.id,
                year=h.year,
                title=h.title,
                similarity_score=round(sim_score, 3),
                nifty_impact_30d=h.market_impact.nifty_30d,
                nifty_impact_60d=h.market_impact.nifty_60d,
                best_sectors=h.market_impact.best_sectors[:3],
                worst_sectors=h.market_impact.worst_sectors[:3],
                description=h.description,
            ))

        if not analogies:
            return self._empty_result(event_text)

        # Weighted average impact
        weights = [a.similarity_score for a in analogies]
        total_w = sum(weights)
        avg_30d = sum(a.nifty_impact_30d * w for a, w in zip(analogies, weights)) / total_w
        avg_60d = sum(a.nifty_impact_60d * w for a, w in zip(analogies, weights)) / total_w
        avg_conf = sum(weights) / len(weights)

        # Summary sentence
        direction = "positive" if avg_30d > 0 else "negative"
        summary = (
            f"Based on {len(analogies)} similar historical events, "
            f"markets showed an average {direction} reaction of "
            f"{abs(avg_30d):.1f}% in 30 days. "
            f"Closest analogy: {analogies[0].year} — {analogies[0].title}."
        )

        return HistoricalAnalysisResult(
            event_title=event_text[:120],
            analogies=analogies,
            avg_expected_impact_30d=round(avg_30d, 2),
            avg_expected_impact_60d=round(avg_60d, 2),
            confidence=round(avg_conf, 3),
            summary=summary,
        )

    def _empty_result(self, title: str) -> HistoricalAnalysisResult:
        return HistoricalAnalysisResult(
            event_title=title[:120],
            analogies=[],
            avg_expected_impact_30d=0.0,
            avg_expected_impact_60d=0.0,
            confidence=0.0,
            summary="No historically similar events found in the archive.",
        )
