"use client";

import React, { useEffect, useState } from "react";
import { Briefcase, AlertTriangle, ArrowUpRight, ArrowDownRight, Radio, Zap, TrendingUp, TrendingDown, ChevronDown, ChevronUp, Clock } from "lucide-react";
import { api } from "@/lib/api";

interface DashboardViewProps {
  events: any[];
  leads?: any[];
  onSelectEvent: (event: any) => void;
  prices?: Record<string, any>;
}

const leadersConfig = {
  narendra_modi: { name: "Narendra Modi", role: "Prime Minister of India", icon: "[IN]", fallback: "Stable capex and green energy push." },
  donald_trump: { name: "Donald Trump", role: "US Leader", icon: "[US]", fallback: "Tariffs and trade policy focus." },
  jerome_powell: { name: "Jerome Powell", role: "Fed Chairman", icon: "[US]", fallback: "Monetary policy and rate regime tracker." },
  elon_musk: { name: "Elon Musk", role: "CEO, Tesla & SpaceX", icon: "[TSLA]", fallback: "Tech and EV market driver." }
};

const actionConfig = {
  buy: { label: "BUY", bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-300", glow: "" },
  sell: { label: "SELL", bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-300", glow: "" },
  accumulate: { label: "ACCUMULATE", bg: "bg-emerald-50/50", text: "text-emerald-600", border: "border-emerald-200", glow: "" },
  exit: { label: "EXIT", bg: "bg-rose-50/50", text: "text-rose-600", border: "border-rose-200", glow: "" },
};

const signalLabels: Record<string, string> = {
  news: "News",
  voice: "Voice",
  sector: "Sector",
  graph: "Graph",
  smart_money: "Smart Money",
};

export default function DashboardView({ events, leads = [], onSelectEvent, prices = {} }: DashboardViewProps) {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [exposures, setExposures] = useState<any[]>([]);
  const [livePortfolio, setLivePortfolio] = useState<any>(null);
  const [expandedLead, setExpandedLead] = useState<string | null>(null);
  const [predictions, setPredictions] = useState<Record<string, any>>({});
  const [selectedHoldingTicker, setSelectedHoldingTicker] = useState<string>("");

  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    setNow(Date.now());
    const interval = setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        const port = await api.getPortfolio();
        setPortfolio(port);
        const opps = await api.getOpportunities();
        setOpportunities(opps);
        const expo = await api.getExposure();
        setExposures(expo);
        const preds = await api.getPortfolioPredictions();
        setPredictions(preds);
      } catch (e) {
        console.error("Dashboard failed to load stats", e);
      }
    }
    loadData();
  }, [events]);

  useEffect(() => {
    if (!portfolio) {
      setLivePortfolio(null);
      return;
    }
    
    let updatedTotalValue = 0;
    let updatedTotalInvested = 0;
    
    const updatedHoldings = portfolio.holdings?.map((h: any) => {
      const liveData = prices[h.ticker];
      const currentPrice = liveData ? (liveData.price ?? h.current_price) : h.current_price;
      const holdingValue = currentPrice * h.quantity;
      const holdingCost = h.avg_buy_price * h.quantity;
      updatedTotalValue += holdingValue;
      updatedTotalInvested += holdingCost;
      
      const holdingPnl = holdingValue - holdingCost;
      const holdingPnlPct = h.avg_buy_price !== 0 ? ((currentPrice - h.avg_buy_price) / h.avg_buy_price) * 100 : 0;
      
      return {
        ...h,
        current_price: currentPrice,
        pnl: holdingPnl,
        pnl_pct: holdingPnlPct
      };
    }) || [];
    
    const overallPnl = updatedTotalValue - updatedTotalInvested;
    const overallPnlPct = updatedTotalInvested !== 0 ? (overallPnl / updatedTotalInvested) * 100 : 0;
    
    setLivePortfolio({
      holdings: updatedHoldings,
      total_value: updatedTotalValue,
      total_invested: updatedTotalInvested,
      overall_pnl: overallPnl,
      overall_pnl_pct: overallPnlPct
    });
  }, [portfolio, prices]);

  const holdingsList = livePortfolio?.holdings || [];
  
  useEffect(() => {
    if (holdingsList.length > 0 && (!selectedHoldingTicker || !holdingsList.some((h: any) => h.ticker === selectedHoldingTicker))) {
      setSelectedHoldingTicker(holdingsList[0].ticker);
    }
  }, [holdingsList, selectedHoldingTicker]);

  const pnl = livePortfolio ? livePortfolio.overall_pnl : (portfolio?.overall_pnl || 0);
  const pnlPct = livePortfolio ? livePortfolio.overall_pnl_pct : (portfolio?.overall_pnl_pct || 0);
  const totalValue = livePortfolio ? livePortfolio.total_value : (portfolio?.total_value || 0);
  const totalInvested = livePortfolio ? livePortfolio.total_invested : (portfolio?.total_invested || 0);
  const isProfit = pnl >= 0;

  const getLiveSectorImpacts = () => {
    const sectorMap: Record<string, number> = {
      "Technology": 0.0,
      "Banking & Finance": 0.0,
      "Energy & Utilities": 0.0,
      "Aviation": 0.0,
      "Paints": 0.0,
      "Metals & Mining": 0.0,
      "Infrastructure": 0.0,
      "Defense & Aerospace": 0.0,
    };

    const activeEvents = events.slice(0, 15);
    activeEvents.forEach((ev) => {
      let baseScore = ev.severity || 0.3;
      const sentiment = (ev.sentiment || "neutral").toLowerCase();
      if (sentiment === "negative") {
        baseScore = -baseScore;
      } else if (sentiment === "neutral") {
        baseScore = baseScore * 0.2;
      }

      ev.entities?.forEach((ent: any) => {
        const norm = (ent.normalized_name || "").toLowerCase();
        if (norm === "technology") sectorMap["Technology"] += baseScore * 1.0;
        if (norm === "banking_finance") sectorMap["Banking & Finance"] += baseScore * 1.0;
        if (norm === "energy_utilities") sectorMap["Energy & Utilities"] += baseScore * 1.0;
        if (norm === "aviation") sectorMap["Aviation"] += baseScore * 1.0;
        if (norm === "paints") sectorMap["Paints"] += baseScore * 1.0;
        if (norm === "metals_mining") sectorMap["Metals & Mining"] += baseScore * 1.0;
        if (norm === "infrastructure") sectorMap["Infrastructure"] += baseScore * 1.0;
        if (norm === "defense_aerospace") sectorMap["Defense & Aerospace"] += baseScore * 1.0;

        if (norm === "donald_trump") {
          sectorMap["Technology"] += baseScore * -0.4;
          sectorMap["Energy & Utilities"] += baseScore * 0.6;
        }
        if (norm === "narendra_modi") {
          sectorMap["Infrastructure"] += baseScore * 0.8;
          sectorMap["Energy & Utilities"] += baseScore * 0.7;
        }
        if (norm === "jerome_powell") {
          sectorMap["Banking & Finance"] += baseScore * 0.9;
        }
        if (norm === "elon_musk") {
          sectorMap["Technology"] += baseScore * 0.8;
        }

        if (norm === "crude_oil" || norm === "oil") {
          sectorMap["Energy & Utilities"] += baseScore * 0.6;
          sectorMap["Aviation"] += baseScore * -0.8;
          sectorMap["Paints"] += baseScore * -0.7;
        }
        if (norm === "natural_gas" || norm === "gas") {
          sectorMap["Energy & Utilities"] += baseScore * 0.5;
        }
        if (norm === "coal") {
          sectorMap["Energy & Utilities"] += baseScore * 0.7;
        }
        if (norm === "steel" || norm === "iron") {
          sectorMap["Infrastructure"] += baseScore * -0.5;
          sectorMap["Metals & Mining"] += baseScore * 0.8;
        }
        if (norm === "copper") {
          sectorMap["Technology"] += baseScore * -0.2;
          sectorMap["Metals & Mining"] += baseScore * 0.7;
        }
        if (norm === "semiconductors") {
          sectorMap["Technology"] += baseScore * 0.8;
        }
      });

      const category = (ev.category || "").toLowerCase();
      const subCategory = (ev.sub_category || "").toLowerCase();

      if (category === "geopolitical") {
        if (subCategory === "war") {
          sectorMap["Aviation"] += baseScore * -0.5;
          sectorMap["Defense & Aerospace"] += Math.abs(baseScore) * 0.8;
        }
      }
      if (category === "economic") {
        if (subCategory === "interest_rate") {
          sectorMap["Banking & Finance"] += baseScore * 0.8;
        }
      }
    });

    return Object.entries(sectorMap).map(([name, rawScore]) => {
      const impact = Math.max(-1.0, Math.min(1.0, rawScore));
      return { name, impact };
    });
  };

  const sectors = getLiveSectorImpacts();

  // Dynamic Risk Radar calculated based on recent news severity
  const recentEvents = events.slice(0, 10);
  const avgSeverity = recentEvents.length > 0 
    ? recentEvents.reduce((acc, ev) => acc + (ev.severity || 0), 0) / recentEvents.length 
    : 0.2;

  let riskLevel = "Low";
  let riskColor = "text-emerald-700";
  let riskSub = "STABLE REGIME";
  if (avgSeverity >= 0.6) {
    riskLevel = "Extreme";
    riskColor = "text-rose-700";
    riskSub = "CRITICAL VOLATILITY";
  } else if (avgSeverity >= 0.45) {
    riskLevel = "High";
    riskColor = "text-rose-600";
    riskSub = "HIGH VOLATILITY";
  } else if (avgSeverity >= 0.3) {
    riskLevel = "Moderate";
    riskColor = "text-zinc-700";
    riskSub = "MODERATE VOLATILITY";
  }

  // Helper: format time remaining
  const getTimeRemaining = (expiresAt: string) => {
    if (!now) return "Calculating...";
    const diff = new Date(expiresAt).getTime() - now;
    if (diff <= 0) return "Expired";
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}h ${mins}m`;
  };

  return (
    <div className="space-y-8 animate-fade-in text-zinc-900 bg-white">
      {/* Portfolio overview row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="glass-panel p-6 flex flex-col justify-between h-36 rounded-none border-zinc-200 bg-white shadow-none">
          <div className="flex justify-between items-center text-zinc-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Portfolio Value</span>
            <Briefcase className="w-5 h-5 text-black" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-zinc-950 font-mono">
              ₹{totalValue.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
            </h3>
            <span className="text-[10px] text-zinc-400">REAL-TIME VALUATION</span>
          </div>
        </div>

        <div className="glass-panel p-6 flex flex-col justify-between h-36 rounded-none border-zinc-200 bg-white shadow-none">
          <div className="flex justify-between items-center text-zinc-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Invested Capital</span>
            <Briefcase className="w-5 h-5 text-zinc-400" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-zinc-800 font-mono">
              ₹{totalInvested.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
            </h3>
            <span className="text-[10px] text-zinc-400">ACQUISITION COST</span>
          </div>
        </div>

        <div className="glass-panel p-6 flex flex-col justify-between h-36 rounded-none border-zinc-200 bg-white shadow-none">
          <div className="flex justify-between items-center text-zinc-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Total P&L</span>
            {isProfit ? (
              <ArrowUpRight className="w-5 h-5 text-emerald-600" />
            ) : (
              <ArrowDownRight className="w-5 h-5 text-rose-600" />
            )}
          </div>
          <div>
            <h3 className={`text-2xl font-bold font-mono ${isProfit ? "text-emerald-700" : "text-rose-700"}`}>
              ₹{pnl.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
            </h3>
            <span className={`text-xs font-mono font-bold ${isProfit ? "text-emerald-600" : "text-rose-600"}`}>
              {isProfit ? "+" : ""}{pnlPct.toFixed(2)}%
            </span>
          </div>
        </div>

        <div className="glass-panel p-6 flex flex-col justify-between h-36 rounded-none border-zinc-200 bg-white shadow-none">
          <div className="flex justify-between items-center text-zinc-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Risk Radar</span>
            <AlertTriangle className={`w-5 h-5 ${riskColor}`} />
          </div>
          <div>
            <h3 className={`text-2xl font-bold font-mono ${riskColor}`}>
              {riskLevel}
            </h3>
            <span className={`text-[10px] font-bold tracking-wider text-zinc-500`}>{riskSub}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Real-time event stream */}
        <div className="glass-panel lg:col-span-1 p-6 flex flex-col h-[620px] rounded-none border-zinc-200 bg-white">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Radio className="w-5 h-5 text-black" />
              <h3 className="text-base font-bold text-zinc-950 uppercase tracking-wider">Live Feed</h3>
            </div>
            <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono">Live</span>
          </div>
          
          <div className="overflow-y-auto pr-2 flex-grow space-y-3">
            {events.length === 0 ? (
              <div className="h-full flex items-center justify-center text-zinc-400 text-sm">
                No events received yet. Live intelligence warming up...
              </div>
            ) : (
              events.map((ev) => {
                const borderColors = {
                  geopolitical: "border-l-rose-600",
                  economic: "border-l-zinc-700",
                  company: "border-l-emerald-600",
                  regulatory: "border-l-zinc-800",
                  market: "border-l-zinc-900",
                  unknown: "border-l-zinc-400",
                };
                const cat = (ev.category || "unknown").toLowerCase() as keyof typeof borderColors;
                return (
                  <div
                    key={ev.id}
                    onClick={() => onSelectEvent(ev)}
                    className={`p-3 bg-zinc-50 hover:bg-zinc-100 border border-zinc-200 border-l-4 ${borderColors[cat] || "border-l-zinc-400"} rounded-none cursor-pointer transition-all duration-300`}
                  >
                    <div className="flex justify-between items-start mb-1.5">
                      <span className="text-[9px] uppercase font-bold tracking-wider text-zinc-700 bg-zinc-200 px-1.5 py-0.5 rounded-none">
                        {ev.category}
                      </span>
                      <span className="text-[10px] text-zinc-400 font-mono">
                        {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <h4 className="text-xs font-bold text-zinc-950 mb-1 hover:underline transition-colors duration-200 line-clamp-2">
                      {ev.title}
                    </h4>
                    <div className="flex justify-between items-center">
                      <div className="flex gap-1">
                        {ev.affected_regions?.slice(0, 2).map((reg: string) => (
                          <span key={reg} className="text-[8px] bg-zinc-200 text-zinc-650 px-1 py-0.5 rounded-none uppercase font-mono">
                            {reg}
                          </span>
                        ))}
                      </div>
                      <span className="text-[9px] font-mono text-zinc-950 font-bold">
                        {(ev.severity * 10).toFixed(1)}/10
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Alpha Lead Generator — center column */}
        <div className="glass-panel lg:col-span-2 p-6 flex flex-col h-[620px] rounded-none border-zinc-200 bg-white">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-black" />
              <h3 className="text-base font-bold text-zinc-950 uppercase tracking-wider">Alpha Lead Generator</h3>
            </div>
            <div className="flex items-center gap-2">
              {leads.length > 0 && (
                <span className="text-[10px] font-bold bg-zinc-100 text-zinc-800 border border-zinc-350 px-2 py-0.5 rounded-none">
                  {leads.length} ACTIVE
                </span>
              )}
              <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono">Scanning</span>
            </div>
          </div>

          <div className="overflow-y-auto pr-2 flex-grow space-y-3">
            {leads.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-zinc-400 gap-4">
                <div className="w-12 h-12 border border-zinc-300 flex items-center justify-center">
                  <Zap className="w-6 h-6 text-zinc-400" />
                </div>
                <div className="text-center">
                  <p className="text-xs font-medium text-zinc-600">Scanning global feeds...</p>
                  <p className="text-[10px] text-zinc-400 mt-1">Leads will stream in real-time</p>
                </div>
              </div>
            ) : (
              leads.map((lead, idx) => {
                const config = actionConfig[lead.action as keyof typeof actionConfig] || actionConfig.buy;
                const isExpanded = expandedLead === lead.id;
                const convictionPct = Math.round((lead.conviction || 0) * 100);

                return (
                  <div
                    key={lead.id}
                    className={`p-4 bg-white border border-zinc-200 rounded-none transition-all duration-300 hover:bg-zinc-50`}
                  >
                    {/* Header row */}
                    <div className="flex justify-between items-center mb-3">
                      <div className="flex items-center gap-2.5">
                        <div className={`${config.bg} border ${config.border} px-2 py-0.5 rounded-none flex items-center gap-1`}>
                          {lead.action === "buy" || lead.action === "accumulate" ? (
                            <TrendingUp className={`w-3 h-3 ${config.text}`} />
                          ) : (
                            <TrendingDown className={`w-3 h-3 ${config.text}`} />
                          )}
                          <span className={`text-[10px] font-bold tracking-wider ${config.text}`}>
                            {config.label}
                          </span>
                        </div>
                        <div>
                          <span className="text-sm font-bold text-zinc-950">{lead.ticker?.replace(".NS", "")}</span>
                          <span className="text-[10px] text-zinc-500 ml-1.5">{lead.company_name}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {lead.key_voice && (
                          <span className="text-[9px] bg-zinc-100 text-zinc-800 border border-zinc-200 px-1.5 py-0.5 rounded-none font-mono">
                            Voice: {lead.key_voice.split(" ").pop()}
                          </span>
                        )}
                        <span className={`text-xs font-mono font-bold ${lead.expected_move_pct >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                          {lead.expected_move_pct >= 0 ? "+" : ""}{lead.expected_move_pct?.toFixed(1)}%
                        </span>
                      </div>
                    </div>

                    {/* Conviction bar */}
                    <div className="mb-3">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">Conviction</span>
                        <span className={`text-xs font-mono font-bold text-zinc-800`}>
                          {convictionPct}%
                        </span>
                      </div>
                      <div className="w-full bg-zinc-100 rounded-none h-2 overflow-hidden border border-zinc-250">
                        <div
                          className={`h-full rounded-none transition-all duration-700 ${
                            lead.action === "buy" || lead.action === "accumulate"
                              ? "bg-emerald-600"
                              : "bg-rose-600"
                          }`}
                          style={{ width: `${convictionPct}%` }}
                        />
                      </div>
                    </div>

                    {/* Signal breakdown mini-bars */}
                    {lead.signals && (
                      <div className="grid grid-cols-5 gap-1.5 mb-3">
                        {Object.entries(lead.signals).map(([key, val]) => {
                          const absVal = Math.abs(val as number);
                          const barPct = Math.min(Math.round(absVal * 100), 100);
                          const isPos = (val as number) >= 0;
                          return (
                            <div key={key} className="text-center">
                              <div className="text-[8px] text-zinc-500 mb-0.5 truncate">{signalLabels[key] || key}</div>
                              <div className="w-full bg-zinc-100 rounded-none h-1 overflow-hidden">
                                <div
                                  className={`h-full rounded-none transition-all duration-500 ${isPos ? "bg-emerald-600" : "bg-rose-600"}`}
                                  style={{ width: `${Math.max(barPct, 3)}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Trigger event */}
                    <div className="flex justify-between items-center mb-2">
                      <span
                        onClick={() => lead.trigger_event_id && onSelectEvent({ id: lead.trigger_event_id, title: lead.trigger_event_title })}
                        className="text-[10px] text-zinc-700 hover:underline cursor-pointer transition-colors duration-200 line-clamp-1 flex-1 mr-2 font-medium"
                      >
                        {lead.trigger_event_title}
                      </span>
                      <div className="flex items-center gap-1 text-[9px] text-zinc-500 font-mono shrink-0">
                        <Clock className="w-3 h-3" />
                        {getTimeRemaining(lead.expires_at)}
                      </div>
                    </div>

                    {/* Expandable reasoning */}
                    {lead.reasoning && lead.reasoning.length > 0 && (
                      <div>
                        <button
                          onClick={() => setExpandedLead(isExpanded ? null : lead.id)}
                          className="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-zinc-800 transition-colors duration-200 font-semibold"
                        >
                          {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                          {isExpanded ? "Hide Details" : "Show Details"} ({lead.reasoning.length})
                        </button>
                        {isExpanded && (
                          <div className="mt-2 space-y-1 pl-2 border-l border-zinc-300">
                            {lead.reasoning.map((r: string, i: number) => (
                              <p key={i} className="text-[10px] text-zinc-650 leading-relaxed">
                                {r}
                              </p>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Key Voices & Speech Tracker column */}
        <div className="glass-panel p-6 h-[620px] flex flex-col rounded-none border-zinc-200 bg-white">
          <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider mb-4 border-b border-zinc-200 pb-2">
            Key Voices & Speech
          </h3>
          <div className="space-y-4 flex-grow overflow-y-auto pr-1">
            {Object.entries(leadersConfig).map(([id, leader]) => {
              const matchedEvents = events.filter(ev => {
                const hasEntity = ev.entities?.some((ent: any) => ent.normalized_name === id);
                const hasText = ev.title?.toLowerCase().includes(leader.name.toLowerCase().split(" ")[1] || leader.name.toLowerCase());
                return hasEntity || hasText;
              });

              let latestEvent = null;
              if (matchedEvents.length > 0) {
                matchedEvents.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
                latestEvent = matchedEvents[0];
              }

              let sentiment = "neutral";
              let severity = 0.0;
              let title = leader.fallback;
              let dateStr = "";
              let impactVal = 0.0;

              if (latestEvent) {
                sentiment = (latestEvent.sentiment || "neutral").toLowerCase();
                severity = latestEvent.severity || 0.0;
                title = latestEvent.title;
                dateStr = new Date(latestEvent.timestamp).toLocaleDateString([], { month: "short", day: "numeric" });
                
                let factor = 0.2;
                if (sentiment === "positive") factor = 1.0;
                if (sentiment === "negative") factor = -1.0;
                impactVal = severity * 10 * factor;
              }

              const isPos = impactVal >= 0;
              const strengthPct = Math.min(Math.round(severity * 100), 100);

              const badgeColor = sentiment === "positive" 
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : sentiment === "negative"
                ? "bg-rose-50 text-rose-700 border-rose-200"
                : "bg-zinc-100 text-zinc-700 border-zinc-200";

              return (
                <div 
                  key={id} 
                  className="p-3 bg-zinc-50 border border-zinc-200 rounded-none space-y-2 hover:bg-zinc-100 transition-all duration-300"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-zinc-500 leading-none">{leader.icon}</span>
                      <div>
                        <h4 className="text-xs font-bold text-zinc-950 leading-tight">{leader.name}</h4>
                        <span className="text-[10px] text-zinc-500 leading-none">{leader.role}</span>
                      </div>
                    </div>
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 border rounded-none ${badgeColor}`}>
                      {isPos ? "+" : ""}{impactVal.toFixed(1)} Stance
                    </span>
                  </div>

                  <div 
                    onClick={() => latestEvent && onSelectEvent(latestEvent)}
                    className={`text-[11px] leading-snug font-medium text-zinc-800 line-clamp-2 ${latestEvent ? "cursor-pointer hover:underline" : ""}`}
                  >
                    {latestEvent ? `"${title}"` : title}
                  </div>

                  {latestEvent && (
                    <div className="flex justify-between items-center text-[9px] text-zinc-500 font-mono">
                      <span>{dateStr} via {latestEvent.source}</span>
                      <span>Strength: {strengthPct}%</span>
                    </div>
                  )}

                  <div className="w-full bg-zinc-200 rounded-none h-1 overflow-hidden">
                    <div 
                      className={`h-full rounded-none transition-all duration-500 ${isPos ? "bg-emerald-600" : "bg-rose-600"}`}
                      style={{ width: `${strengthPct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Sector Impact Map */}
          <div className="mt-4 pt-4 border-t border-zinc-200">
            <h3 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2">
              Sector Impact Map
            </h3>
            <div className="grid grid-cols-2 gap-1.5">
              {sectors.map((sec) => {
                const isPos = sec.impact >= 0;
                const score = Math.abs(sec.impact);
                const bg = isPos 
                  ? `rgba(16, 185, 129, ${0.03 + score * 0.08})`
                  : `rgba(239, 68, 68, ${0.03 + score * 0.08})`;
                const border = isPos
                  ? `rgba(16, 185, 129, 0.2)`
                  : `rgba(239, 68, 68, 0.2)`;
                const text = isPos ? "text-emerald-700 font-bold" : "text-rose-700 font-bold";

                return (
                  <div
                    key={sec.name}
                    style={{ backgroundColor: bg, borderColor: border }}
                    className="border p-2 rounded-none flex justify-between items-center transition-all duration-300"
                  >
                    <span className="text-[8px] font-bold text-zinc-800 leading-tight">{sec.name}</span>
                    <span className={`text-[9px] font-mono ${text}`}>
                      {isPos ? "+" : ""}{(sec.impact * 10).toFixed(1)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Holdings & Causal timeline row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 pt-4">
        {/* Left Column: My Vault Positions */}
        <div className="glass-panel p-6 flex flex-col h-[400px] rounded-none border-zinc-200 bg-white">
          <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider mb-4 border-b border-zinc-200 pb-2">
            My Vault Positions
          </h3>
          <div className="overflow-y-auto flex-grow">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-zinc-200 text-[10px] font-bold text-zinc-500 tracking-wider">
                  <th className="pb-2 text-left">TICKER</th>
                  <th className="pb-2 text-right">QUANTITY</th>
                  <th className="pb-2 text-right">AVG COST</th>
                  <th className="pb-2 text-right">LIVE PRICE</th>
                  <th className="pb-2 text-right">P&L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {holdingsList.map((h: any) => {
                  const isPos = h.pnl >= 0;
                  const isActive = selectedHoldingTicker === h.ticker;
                  return (
                    <tr
                      key={h.ticker}
                      onClick={() => setSelectedHoldingTicker(h.ticker)}
                      className={`text-xs cursor-pointer hover:bg-zinc-50 transition-colors duration-150 ${
                        isActive ? "bg-zinc-100 font-semibold" : ""
                      }`}
                    >
                      <td className="py-3">
                        <span className="font-bold text-zinc-950 block">{h.ticker?.replace(".NS", "")}</span>
                        <span className="text-[10px] text-zinc-500 block truncate max-w-[120px]">{h.company_name}</span>
                      </td>
                      <td className="py-3 text-right font-mono text-zinc-800">{h.quantity}</td>
                      <td className="py-3 text-right font-mono text-zinc-800">
                        ₹{h.avg_buy_price?.toFixed(1)}
                      </td>
                      <td className="py-3 text-right font-mono text-zinc-800">
                        ₹{h.current_price?.toFixed(1)}
                      </td>
                      <td className={`py-3 text-right font-mono font-bold ${isPos ? "text-emerald-700" : "text-rose-700"}`}>
                        {isPos ? "+" : ""}
                        {h.pnl_pct?.toFixed(1)}%
                      </td>
                    </tr>
                  );
                })}
                {holdingsList.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-zinc-400">
                      No vault positions found. Add positions in Portfolio Vault tab.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Holding Thesis & Causal Timeline */}
        <div className="glass-panel p-6 flex flex-col h-[400px] rounded-none border-zinc-200 bg-white">
          <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider mb-4 border-b border-zinc-200 pb-2">
            Holding Thesis & Causal Timeline
          </h3>
          <div className="overflow-y-auto flex-grow space-y-4">
            {selectedHoldingTicker ? (
              (() => {
                const currentHolding = holdingsList.find((h: any) => h.ticker === selectedHoldingTicker);
                const pred = predictions[selectedHoldingTicker];
                
                // Find news events relevant to this holding (matching ticker or company name or sector)
                const relevantEvents = events.filter((ev: any) => {
                  const titleLower = ev.title?.toLowerCase() || "";
                  const contentLower = ev.raw_text?.toLowerCase() || "";
                  const tickerNorm = selectedHoldingTicker.replace(".NS", "").toLowerCase();
                  const compNorm = currentHolding?.company_name?.toLowerCase() || "";
                  const sectorNorm = (currentHolding?.sector || "").toLowerCase();
                  
                  return (
                    titleLower.includes(tickerNorm) ||
                    contentLower.includes(tickerNorm) ||
                    (compNorm && (titleLower.includes(compNorm) || contentLower.includes(compNorm))) ||
                    (sectorNorm && (titleLower.includes(sectorNorm) || contentLower.includes(sectorNorm))) ||
                    (ev.entities && ev.entities.some((ent: any) => {
                      const entName = ent.normalized_name?.toLowerCase() || "";
                      return entName === tickerNorm || entName === sectorNorm || entName === compNorm;
                    }))
                  );
                });

                return (
                  <div className="space-y-4">
                    {/* Thesis Drift Radar — Custom Thesis + Health Score */}
                    {currentHolding?.thesis ? (
                      <div className="bg-zinc-50 border border-zinc-200 p-3.5 space-y-3 rounded-none">
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                            Your Investment Thesis
                          </span>
                          <span className={`text-[9px] font-bold px-2 py-0.5 border uppercase tracking-wide rounded-none ${
                            (currentHolding.thesis_health ?? 100) >= 75
                              ? "bg-white text-zinc-800 border-zinc-300"
                              : (currentHolding.thesis_health ?? 100) >= 45
                              ? "bg-zinc-100 text-zinc-600 border-zinc-300"
                              : "bg-zinc-50 text-zinc-400 border-zinc-200"
                          }`}>
                            {(currentHolding.thesis_health ?? 100) >= 75 ? "ON TRACK" :
                             (currentHolding.thesis_health ?? 100) >= 45 ? "DRIFTING" : "AT RISK"}
                          </span>
                        </div>
                        <p className="text-xs text-zinc-800 leading-relaxed italic">
                          &ldquo;{currentHolding.thesis}&rdquo;
                        </p>
                        <div className="space-y-1">
                          <div className="flex justify-between items-center">
                            <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">Thesis Health</span>
                            <span className="text-xs font-mono font-bold text-zinc-800">
                              {(currentHolding.thesis_health ?? 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="w-full bg-zinc-200 h-1.5 rounded-none overflow-hidden">
                            <div
                              style={{ width: `${currentHolding.thesis_health ?? 100}%` }}
                              className={`h-full rounded-none transition-all duration-700 ${
                                (currentHolding.thesis_health ?? 100) >= 75 ? "bg-black" :
                                (currentHolding.thesis_health ?? 100) >= 45 ? "bg-zinc-500" :
                                "bg-zinc-300"
                              }`}
                            />
                          </div>
                          <p className="text-[9px] text-zinc-400 pt-0.5">
                            Updated automatically as market events are processed. Score decays when news contradicts your thesis.
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="bg-zinc-50 border border-zinc-200 p-3.5 text-xs text-zinc-800 rounded-none">
                        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block mb-1">
                          Holding Thesis
                        </span>
                        {pred && pred.reasoning_chain && pred.reasoning_chain.length > 0 ? (
                          <ul className="list-disc pl-4 space-y-1">
                            {pred.reasoning_chain.map((reason: string, i: number) => (
                              <li key={i}>{reason}</li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-zinc-600 italic">
                            No custom thesis set for {selectedHoldingTicker?.replace(".NS", "")}. Add one in Portfolio Vault when adding this position.
                          </p>
                        )}
                      </div>
                    )}


                    {/* Causal News Timeline */}
                    <div className="space-y-2">
                      <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">
                        Causal News History
                      </span>
                      {relevantEvents.length > 0 ? (
                        <div className="space-y-2">
                          {relevantEvents.slice(0, 5).map((ev: any) => {
                            const isPos = ev.sentiment === "positive";
                            const isNeg = ev.sentiment === "negative";
                            const sentimentColor = isPos ? "text-emerald-700 bg-emerald-50 border-emerald-200" : isNeg ? "text-rose-700 bg-rose-50 border-rose-200" : "text-zinc-700 bg-zinc-100 border-zinc-200";
                            return (
                              <div key={ev.id} className="p-3 border border-zinc-200 flex justify-between gap-4 bg-white rounded-none">
                                <div className="space-y-1">
                                  <div className="flex items-center gap-2">
                                    <span className="text-[9px] font-mono text-zinc-400">
                                      {new Date(ev.timestamp).toLocaleDateString([], { month: "short", day: "numeric" })}
                                    </span>
                                    <span className={`text-[8px] font-bold px-1.5 py-0.5 border uppercase rounded-none ${sentimentColor}`}>
                                      {ev.sentiment}
                                    </span>
                                  </div>
                                  <h4 className="text-xs font-bold text-zinc-950 leading-snug">{ev.title}</h4>
                                  <p className="text-[10px] text-zinc-600 leading-relaxed">{ev.summary}</p>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <p className="text-xs text-zinc-400 italic">No direct historical events recorded for this position.</p>
                      )}
                    </div>
                  </div>
                );
              })()
            ) : (
              <p className="text-xs text-zinc-400 italic text-center py-12">Select a position from the left table to view its thesis and news timeline.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
