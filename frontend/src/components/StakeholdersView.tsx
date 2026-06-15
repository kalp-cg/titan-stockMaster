"use client";

import React, { useEffect, useState, useRef } from "react";
import { Users, TrendingUp, DollarSign, RefreshCw, BarChart2, ShieldAlert, Search, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

export default function StakeholdersView() {
  const [selectedTicker, setSelectedTicker] = useState("RELIANCE.NS");
  const [shareholding, setShareholding] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [bulkDeals, setBulkDeals] = useState<any[]>([]);
  const [insiderTrades, setInsiderTrades] = useState<any[]>([]);
  const [flows, setFlows] = useState<any[]>([]);
  const [smartMoney, setSmartMoney] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);

  const trackers = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"];

  // Autocomplete states
  const [tickerQuery, setTickerQuery] = useState("");
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [lastSelected, setLastSelected] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (tickerQuery === lastSelected) {
      setSuggestions([]);
      return;
    }
    if (tickerQuery.trim().length < 2) {
      setSuggestions([]);
      return;
    }

    const delayDebounceFn = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await api.searchTickers(tickerQuery);
        setSuggestions(results || []);
      } catch (err) {
        console.error("Error fetching autocomplete suggestions:", err);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [tickerQuery, lastSelected]);

  const handleSelectSuggestion = (item: any) => {
    setSelectedTicker(item.symbol);
    setTickerQuery(item.symbol);
    setLastSelected(item.symbol);
    setSuggestions([]);
    setShowDropdown(false);
  };

  async function loadStakeholderDetails() {
    setRefreshing(true);
    try {
      const sh = await api.getShareholding(selectedTicker);
      setShareholding(sh);
      
      const hist = await api.getShareholdingHistory(selectedTicker, 4);
      setHistory(hist);

      const sm = await api.getSmartMoney(selectedTicker);
      setSmartMoney(sm);

      const bulk = await api.getBulkDeals(selectedTicker);
      setBulkDeals(bulk);

      const insider = await api.getInsiderTrades(selectedTicker);
      setInsiderTrades(insider);

      const fl = await api.getInstitutionalFlows();
      setFlows(fl);
    } catch (e) {
      console.error("Failed to load stakeholder intelligence", e);
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadStakeholderDetails();
  }, [selectedTicker]);

  return (
    <div className="space-y-8 animate-fade-in text-zinc-900 bg-white">
      {/* Usability Warning Banner */}
      <div className="border border-zinc-200 bg-zinc-50 p-4 rounded-none flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-black shrink-0 mt-0.5" />
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-950 font-mono">Simulated Dataset Disclaimer</h4>
          <p className="text-[10px] text-zinc-500 font-mono mt-1 leading-relaxed">
            Corporate shareholding distributions are modeled based on public exchange disclosures. However, high-frequency transactions (Bulk/Block deals, daily insider trades, and flows) are simulated statistical projections for research purposes and should not be used as direct buy/sell investment advice.
          </p>
        </div>
      </div>
      {/* Ticker Selector & Refresh */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex gap-2.5 overflow-x-auto py-1 scrollbar-none">
            {trackers.map((t) => (
              <button
                key={t}
                onClick={() => {
                  setSelectedTicker(t);
                  setTickerQuery("");
                }}
                className={`px-4 py-2 text-xs font-semibold rounded-none border transition-all duration-300 ${
                  selectedTicker === t
                    ? "bg-black text-white border-black"
                    : "bg-zinc-50 text-zinc-650 border-zinc-200 hover:text-black hover:bg-zinc-100"
                }`}
              >
                {t.replace(".NS", "")}
              </button>
            ))}
          </div>

          {/* Autocomplete Search input */}
          <div className="relative" ref={dropdownRef}>
            <div className="relative w-48">
              <input
                type="text"
                placeholder="Search other share..."
                value={tickerQuery}
                onChange={(e) => {
                  setTickerQuery(e.target.value);
                  if (lastSelected) setLastSelected(null);
                  setShowDropdown(true);
                }}
                onFocus={() => setShowDropdown(true)}
                className="w-full bg-zinc-50 border border-zinc-200 rounded-none py-1.5 pl-8 pr-3 text-xs text-zinc-900 focus:outline-none focus:border-black transition-all duration-300"
                autoComplete="off"
              />
              <Search className="absolute left-2.5 top-2 w-3.5 h-3.5 text-zinc-400" />
            </div>

            {showDropdown && (tickerQuery.trim().length >= 2 || isSearching) && (
              <div className="absolute top-full left-0 w-80 mt-2 z-50 rounded-none border border-zinc-200 bg-white shadow-lg overflow-hidden max-h-60 overflow-y-auto">
                {isSearching ? (
                  <div className="p-3 flex items-center justify-center gap-2 text-xs text-zinc-500">
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-black" />
                    <span>Searching markets...</span>
                  </div>
                ) : suggestions.length > 0 ? (
                  <ul className="divide-y divide-zinc-100">
                    {suggestions.map((item) => (
                      <li key={item.symbol}>
                        <button
                          type="button"
                          onClick={() => handleSelectSuggestion(item)}
                          className="w-full text-left px-3 py-2 hover:bg-zinc-50 active:bg-zinc-100 transition-all duration-150 flex items-center justify-between group"
                        >
                          <div className="flex flex-col min-w-0 pr-2">
                            <span className="font-bold text-xs text-zinc-950 group-hover:underline truncate">
                              {item.symbol}
                            </span>
                            <span className="text-[10px] text-zinc-500 truncate">
                              {item.name}
                            </span>
                          </div>
                          <span className="text-[8px] font-bold px-1.5 py-0.5 rounded-none bg-zinc-100 text-zinc-650 border border-zinc-200 uppercase shrink-0">
                            {item.exchange}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="p-3 text-center text-xs text-zinc-400">
                    No tickers found matching "{tickerQuery}"
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <button
          onClick={loadStakeholderDetails}
          disabled={refreshing}
          className="flex items-center gap-2 bg-zinc-50 border border-zinc-200 hover:border-zinc-300 text-zinc-700 hover:text-black py-2 px-4 rounded-none text-xs transition-all duration-300"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
          <span>{refreshing ? "Refreshing..." : "Sync Filings"}</span>
        </button>
      </div>

      {/* Row 1: Smart Money Conviction & Shareholding Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Smart money composite signals */}
        <div className="glass-panel p-6 flex flex-col justify-between h-80 rounded-none border-zinc-200 bg-white shadow-none">
          <div>
            <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider mb-2">
              Smart Money Conviction
            </h3>
            <p className="text-[10px] text-zinc-500 leading-relaxed uppercase">
              Composite signal of insider buys, FII accumulation, and promoter pledging
            </p>
          </div>

          {smartMoney ? (
            <div className="space-y-6">
              {/* Dial gauge */}
              <div className="flex justify-between items-center gap-4 bg-zinc-50 p-4 border border-zinc-200 rounded-none">
                <div>
                  <span className="text-[10px] text-zinc-500 font-bold block uppercase tracking-wider">Conviction Level</span>
                  <span className={`text-xl font-bold uppercase ${(smartMoney.conviction_level || "low") === "high" ? "text-emerald-700" : "text-rose-700"}`}>
                    {smartMoney.conviction_level || "low"} Conviction
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-zinc-500 font-bold block uppercase tracking-wider">Net Score</span>
                  <span className={`text-xl font-mono font-bold ${(smartMoney.net_score ?? 0) >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                    {(smartMoney.net_score ?? 0) >= 0 ? "+" : ""}{(smartMoney.net_score ?? 0).toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Acc vs Dist scores */}
              <div className="space-y-2">
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-emerald-700 font-semibold">Accumulation Pressure</span>
                    <span className="text-zinc-600 font-mono">{((smartMoney.accumulation_score ?? 0) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-zinc-100 h-2 rounded-none overflow-hidden border border-zinc-200">
                    <div style={{ width: `${(smartMoney.accumulation_score ?? 0) * 100}%` }} className="bg-emerald-600 h-full rounded-none" />
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-rose-700 font-semibold">Distribution Pressure</span>
                    <span className="text-zinc-600 font-mono">{((smartMoney.distribution_score ?? 0) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-zinc-100 h-2 rounded-none overflow-hidden border border-zinc-200">
                    <div style={{ width: `${(smartMoney.distribution_score ?? 0) * 100}%` }} className="bg-rose-600 h-full rounded-none" />
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center text-xs text-zinc-400">No signals computed.</div>
          )}
        </div>

        {/* Shareholding Breakdown patterns */}
        <div className="lg:col-span-2 glass-panel p-6 flex flex-col justify-between h-80 rounded-none border-zinc-200 bg-white shadow-none">
          <div>
            <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider mb-4 border-b border-zinc-200 pb-2">
              Filings Shareholding Pattern (Clause 31)
            </h3>
            
            {shareholding ? (
              <div className="space-y-6">
                {/* Horizontal bar pattern breakdown */}
                <div className="w-full h-8 rounded-none overflow-hidden flex font-mono text-[10px] text-zinc-950 font-bold border border-zinc-400">
                  <div style={{ width: `${shareholding.promoter_pct ?? 0}%` }} className="bg-zinc-800 text-white flex items-center justify-center truncate px-1" title={`Promoter: ${shareholding.promoter_pct ?? 0}%`}>
                    PROM ({(shareholding.promoter_pct ?? 0).toFixed(0)}%)
                  </div>
                  <div style={{ width: `${shareholding.fii_pct ?? 0}%` }} className="bg-zinc-600 text-white flex items-center justify-center truncate px-1" title={`FII: ${shareholding.fii_pct ?? 0}%`}>
                    FII ({(shareholding.fii_pct ?? 0).toFixed(0)}%)
                  </div>
                  <div style={{ width: `${shareholding.dii_pct ?? 0}%` }} className="bg-zinc-400 text-zinc-950 flex items-center justify-center truncate px-1" title={`DII: ${shareholding.dii_pct ?? 0}%`}>
                    DII ({(shareholding.dii_pct ?? 0).toFixed(0)}%)
                  </div>
                  <div style={{ width: `${shareholding.retail_pct ?? 0}%` }} className="bg-zinc-200 text-zinc-950 flex items-center justify-center truncate px-1" title={`Retail: ${shareholding.retail_pct ?? 0}%`}>
                    RTL ({(shareholding.retail_pct ?? 0).toFixed(0)}%)
                  </div>
                  <div style={{ width: `${Math.max(0, 100 - ((shareholding.promoter_pct ?? 0) + (shareholding.fii_pct ?? 0) + (shareholding.dii_pct ?? 0) + (shareholding.retail_pct ?? 0)))}%` }} className="bg-zinc-100 text-zinc-950 flex items-center justify-center truncate px-1" title="Other">
                    OTH
                  </div>
                </div>

                {/* Significant QoQ changes panel */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-zinc-50 p-3.5 border border-zinc-200 rounded-none text-center">
                    <span className="text-[10px] text-zinc-500 font-bold block uppercase">Promoter Change</span>
                    <span className={`text-base font-mono font-bold ${(shareholding.promoter_delta ?? 0) >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                      {(shareholding.promoter_delta ?? 0) >= 0 ? "+" : ""}{(shareholding.promoter_delta ?? 0).toFixed(2)}%
                    </span>
                  </div>
                  <div className="bg-zinc-50 p-3.5 border border-zinc-200 rounded-none text-center">
                    <span className="text-[10px] text-zinc-500 font-bold block uppercase">FII Flows Change</span>
                    <span className={`text-base font-mono font-bold ${(shareholding.fii_delta ?? 0) >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                      {(shareholding.fii_delta ?? 0) >= 0 ? "+" : ""}{(shareholding.fii_delta ?? 0).toFixed(2)}%
                    </span>
                  </div>
                  <div className="bg-zinc-50 p-3.5 border border-zinc-200 rounded-none text-center">
                    <span className="text-[10px] text-zinc-500 font-bold block uppercase">Promoter Pledge</span>
                    <span className={`text-base font-mono font-bold ${(shareholding.promoter_pledge_pct ?? 0) > 0 ? "text-rose-600" : "text-zinc-500"}`}>
                      {(shareholding.promoter_pledge_pct ?? 0).toFixed(2)}%
                    </span>
                  </div>
                </div>

                {/* Divergence alert banner if any */}
                {(smartMoney?.has_divergence || (smartMoney?.divergence_alerts && smartMoney.divergence_alerts.length > 0)) && (
                  <div className="bg-rose-50 border border-rose-200 p-3 rounded-none flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
                    <span className="text-xs text-rose-700 font-semibold">{smartMoney.divergence_alerts[0]}</span>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-zinc-400 text-xs py-8">Fetching shareholding disclosures...</p>
            )}
          </div>
        </div>
      </div>

      {/* Row 2: Bulk Deals, Insider Trades & Significant Shareholders */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Bulk deals feed */}
        <div className="glass-panel p-6 h-96 flex flex-col justify-between rounded-none border-zinc-200 bg-white shadow-none">
          <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider mb-4 border-b border-zinc-200 pb-2">
            Bulk & Block Deals Log
          </h3>
          <div className="overflow-y-auto pr-1 flex-grow space-y-3">
            {bulkDeals.map((deal) => {
              const isBuy = deal.deal_type === "buy";
              return (
                <div key={deal.id} className="p-3 bg-zinc-50 border border-zinc-200 rounded-none flex justify-between items-center text-xs">
                  <div>
                    <span className="font-bold text-zinc-900 block">{deal.client_name}</span>
                    <span className="text-[10px] text-zinc-500 font-mono uppercase">
                      {deal.date} | {deal.exchange}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className={`font-mono font-semibold block ${isBuy ? "text-emerald-700" : "text-rose-700"}`}>
                      {isBuy ? "BUY" : "SELL"} {(deal.quantity ?? 0).toLocaleString("en-IN")} @ ₹{deal.price ?? 0}
                    </span>
                    <span className="text-[10px] text-zinc-500 font-mono">
                      Val: ₹{(((deal.quantity ?? 0) * (deal.price ?? 0)) / 1e7).toFixed(2)} Cr
                    </span>
                  </div>
                </div>
              );
            })}
            {!bulkDeals.length && (
              <p className="text-zinc-400 text-xs text-center py-12">No bulk deals in the last 30 days.</p>
            )}
          </div>
        </div>

        {/* Insider Trades */}
        <div className="glass-panel p-6 h-96 flex flex-col justify-between rounded-none border-zinc-200 bg-white shadow-none">
          <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider mb-4 border-b border-zinc-200 pb-2">
            Insider Trading Disclosures
          </h3>
          <div className="overflow-y-auto pr-1 flex-grow space-y-3">
            {insiderTrades.map((trade) => {
              const isBuy = trade.trade_type === "buy";
              return (
                <div key={trade.id} className="p-3 bg-zinc-50 border border-zinc-200 rounded-none flex justify-between items-center text-xs">
                  <div>
                    <span className="font-bold text-zinc-900 block">{trade.insider_name}</span>
                    <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-mono">
                      {trade.designation} | {trade.date}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className={`font-mono font-semibold block ${isBuy ? "text-emerald-700" : "text-rose-700"}`}>
                      {isBuy ? "BOUGHT" : "SOLD"} {(trade.quantity ?? 0).toLocaleString("en-IN")} @ ₹{trade.price ?? 0}
                    </span>
                    <span className="text-[10px] text-zinc-500 font-mono">
                      Val: ₹{trade.total_value ? (trade.total_value/1e5).toFixed(1) : (((trade.quantity ?? 0) * (trade.price ?? 0)) / 1e5).toFixed(1)} Lakhs
                    </span>
                  </div>
                </div>
              );
            })}
            {!insiderTrades.length && (
              <p className="text-zinc-400 text-xs text-center py-12">No insider disclosures filed in the last 90 days.</p>
            )}
          </div>
        </div>

        {/* Significant Shareholders */}
        <div className="glass-panel p-6 h-96 flex flex-col justify-between rounded-none border-zinc-200 bg-white shadow-none">
          <div className="flex items-center gap-2 mb-4 border-b border-zinc-200 pb-2">
            <Users className="w-5 h-5 text-black" />
            <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider">
              Significant Shareholders
            </h3>
          </div>
          
          <div className="overflow-y-auto pr-1 flex-grow space-y-3">
            {shareholding && shareholding.top_holders && shareholding.top_holders.length > 0 ? (
              shareholding.top_holders.map((holder: any, idx: number) => {
                const change = holder.change_vs_prev_quarter ?? holder.change ?? 0;
                const isAccumulating = change > 0;
                
                const catLabels: Record<string, { label: string, style: string }> = {
                  promoter: { label: "Promoter", style: "bg-zinc-800 text-white border-zinc-800" },
                  fii: { label: "FII", style: "bg-zinc-100 text-zinc-800 border-zinc-200" },
                  dii: { label: "DII", style: "bg-zinc-100 text-zinc-800 border-zinc-200" },
                  mutual_fund: { label: "Mutual Fund", style: "bg-zinc-100 text-zinc-800 border-zinc-200" },
                  insurance: { label: "Insurance", style: "bg-zinc-100 text-zinc-800 border-zinc-200" },
                  retail: { label: "Retail", style: "bg-zinc-50 text-zinc-600 border-zinc-200" },
                };
                
                const catInfo = catLabels[holder.category?.toLowerCase()] || {
                  label: holder.category || "Institutional",
                  style: "bg-zinc-50 text-zinc-600 border-zinc-200"
                };

                return (
                  <div key={idx} className="p-3 bg-zinc-50 border border-zinc-200 rounded-none flex justify-between items-center text-xs">
                    <div className="space-y-1">
                      <span className="font-bold text-zinc-900 block">{holder.name}</span>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`inline-block text-[9px] px-1.5 py-0.5 border font-semibold rounded-none ${catInfo.style}`}>
                          {catInfo.label}
                        </span>
                        {holder.shares_held > 0 && (
                          <span className="text-[10px] text-zinc-500 font-mono">
                            {(holder.shares_held / 10_000_000).toFixed(2)} Cr shares
                          </span>
                        )}
                        {holder.profit_cr !== undefined && holder.profit_cr > 0 && (
                          <span className="text-[10px] font-semibold font-mono text-emerald-700">
                            Profit: +₹{holder.profit_cr.toLocaleString()} Cr
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-right flex flex-col justify-between h-9 items-end shrink-0">
                      <span className="font-mono font-bold text-zinc-900">
                        {(holder.holding_pct ?? 0).toFixed(2)}%
                      </span>
                      {change !== 0 ? (
                        <span className={`text-[10px] font-semibold flex items-center gap-0.5 ${
                          isAccumulating ? "text-emerald-700" : "text-rose-700"
                        }`}>
                          {isAccumulating ? "▲" : "▼"} {Math.abs(change).toFixed(2)}%
                        </span>
                      ) : (
                        <span className="text-[10px] text-zinc-400 font-medium">
                          No change
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            ) : (
              <p className="text-zinc-400 text-xs text-center py-12">No significant shareholders reported.</p>
            )}
          </div>
        </div>
      </div>

      {/* Row 3: Daily FII/DII Net Flows */}
      <div className="glass-panel p-6 h-[260px] flex flex-col justify-between rounded-none border-zinc-200 bg-white shadow-none">
        <div>
          <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider mb-1">
            FII & DII Rolling Flows (INR Crores)
          </h3>
          <p className="text-[10px] text-zinc-500 uppercase">Daily net buying and selling aggregates across NSE cash market</p>
        </div>

        <div className="flex items-end justify-between gap-1.5 h-32 pt-4 border-b border-zinc-200">
          {flows.slice(-15).map((f) => {
            const isPos = f.fii_net_cr >= 0;
            const height = Math.min(100, (Math.abs(f.fii_net_cr) / 3000) * 100);
            return (
              <div key={f.date} className="flex-grow flex flex-col items-center group relative h-full">
                <div className="w-full flex flex-col justify-end h-full">
                  <div
                    style={{ height: `${height}%` }}
                    className={`w-full rounded-none transition-all duration-300 ${isPos ? "bg-emerald-600/70 group-hover:bg-emerald-600" : "bg-rose-600/70 group-hover:bg-rose-600"}`}
                  />
                </div>
                {/* Tooltip details */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 bg-white border border-zinc-200 p-2 rounded-none opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10 text-[9px] whitespace-nowrap space-y-0.5 shadow-md">
                  <span className="font-bold font-mono text-zinc-900 block">{f.date}</span>
                  <span className="text-emerald-700 block font-mono">DII Net: +{f.dii_net_cr} Cr</span>
                  <span className="text-rose-700 block font-mono">FII Net: {f.fii_net_cr} Cr</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
