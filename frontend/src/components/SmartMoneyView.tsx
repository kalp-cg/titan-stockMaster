"use client";

import React, { useEffect, useState } from "react";
import { TrendingUp, RefreshCw, Layers, ShieldAlert, Award, FileText, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { api } from "@/lib/api";

export default function SmartMoneyView() {
  const [scores, setScores] = useState<any[]>([]);
  const [flows, setFlows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    try {
      const portfolioScores = await api.getSmartMoneyPortfolio();
      setScores(portfolioScores);
      if (portfolioScores.length > 0 && !selectedTicker) {
        setSelectedTicker(portfolioScores[0].ticker);
      }

      const flowData = await api.getInstitutionalFlows();
      setFlows(flowData);
    } catch (e) {
      console.error("Failed to load smart money data", e);
    } finally {
      setLoading(false);
    }
  }

  async function handleRefresh() {
    setLoading(true);
    setMessage("Triggering NSE API data refresh...");
    try {
      await api.refreshSmartMoney();
      setMessage("NSE data successfully refreshed. Recalculating scores...");
      const portfolioScores = await api.getSmartMoneyPortfolio();
      setScores(portfolioScores);
      setMessage("Refresh complete!");
      setTimeout(() => setMessage(null), 3000);
    } catch (e: any) {
      setMessage(`Error: ${e.message || "Failed to refresh data"}`);
      setTimeout(() => setMessage(null), 5000);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const selectedScore = scores.find((s) => s.ticker === selectedTicker);

  return (
    <div className="space-y-8 animate-fade-in text-zinc-900 bg-white">
      {/* Page Header */}
      <div className="flex items-center justify-between border-b border-zinc-200 pb-4">
        <div>
          <h2 className="text-lg font-bold text-zinc-950 uppercase tracking-wider">Smart Money Accumulation Tracker</h2>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wide">
            Aggregates FII, DII, block/bulk deals, and promoter trades to score institutional direction
          </p>
        </div>
        <div className="flex items-center gap-4">
          {message && (
            <span className="text-xs text-zinc-650 bg-zinc-100 border border-zinc-200 px-3 py-1.5 font-mono">
              {message}
            </span>
          )}
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="flex items-center gap-2 bg-black text-white hover:bg-zinc-800 disabled:bg-zinc-400 py-2 px-4 rounded-none text-xs transition-all duration-300 border border-black"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            <span>{loading ? "Refreshing..." : "Sync NSE Data"}</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Columns: Portfolio Scores List */}
        <div className="lg:col-span-2 glass-panel p-6 h-[580px] flex flex-col justify-between rounded-none border-zinc-200 bg-white shadow-none">
          <div className="flex items-center gap-2 mb-6 border-b border-zinc-200 pb-2">
            <Layers className="w-5 h-5 text-black" />
            <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider">
              Holdings Scorecard
            </h3>
          </div>

          <div className="overflow-y-auto pr-1 flex-grow space-y-4">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-zinc-200 text-zinc-500 uppercase tracking-wider text-[10px]">
                  <th className="py-2 font-bold">Company</th>
                  <th className="py-2 font-bold text-center">Score</th>
                  <th className="py-2 font-bold text-center">Signal</th>
                  <th className="py-2 font-bold text-right">Bulk Deals (5d)</th>
                  <th className="py-2 font-bold text-right">FII Net (3d)</th>
                  <th className="py-2 font-bold text-right">Insider</th>
                </tr>
              </thead>
              <tbody>
                {scores.map((s) => {
                  const isAccum = s.label === "ACCUMULATING";
                  const isDist = s.label === "DISTRIBUTING";
                  const isSelected = selectedTicker === s.ticker;

                  return (
                    <tr
                      key={s.ticker}
                      onClick={() => setSelectedTicker(s.ticker)}
                      className={`border-b border-zinc-100 cursor-pointer transition-colors duration-200 ${
                        isSelected ? "bg-zinc-50 font-bold" : "hover:bg-zinc-50/50"
                      }`}
                    >
                      <td className="py-3.5">
                        <span className="text-zinc-900 block font-bold">{s.company_name}</span>
                        <span className="text-[10px] text-zinc-500 font-mono">{s.ticker}</span>
                      </td>
                      <td className="py-3.5 text-center font-mono font-bold">
                        <span
                          className={`px-2 py-0.5 border ${
                            isAccum
                              ? "bg-emerald-50 text-emerald-800 border-emerald-350"
                              : isDist
                              ? "bg-rose-50 text-rose-800 border-rose-350"
                              : "bg-zinc-150 text-zinc-800 border-zinc-250"
                          }`}
                        >
                          {s.score}
                        </span>
                      </td>
                      <td className="py-3.5 text-center font-mono font-bold text-[10px]">
                        <span
                          className={
                            isAccum
                              ? "text-emerald-700"
                              : isDist
                              ? "text-rose-700"
                              : "text-zinc-500"
                          }
                        >
                          {s.label}
                        </span>
                      </td>
                      <td className={`py-3.5 text-right font-mono ${s.bulk_deal_net_qty > 0 ? "text-emerald-700" : s.bulk_deal_net_qty < 0 ? "text-rose-700" : "text-zinc-500"}`}>
                        {s.bulk_deal_net_qty !== 0
                          ? `${s.bulk_deal_net_qty > 0 ? "+" : ""}${s.bulk_deal_net_qty.toLocaleString()}`
                          : "—"}
                      </td>
                      <td className={`py-3.5 text-right font-mono ${s.fii_net_3day_cr > 0 ? "text-emerald-700" : s.fii_net_3day_cr < 0 ? "text-rose-700" : "text-zinc-500"}`}>
                        {s.fii_net_3day_cr !== 0
                          ? `${s.fii_net_3day_cr > 0 ? "+" : ""}₹${s.fii_net_3day_cr.toFixed(1)} Cr`
                          : "—"}
                      </td>
                      <td className="py-3.5 text-right font-mono capitalize">
                        {s.insider_direction !== "none" ? (
                          <span className={s.insider_direction === "buying" ? "text-emerald-700" : "text-rose-700"}>
                            {s.insider_direction}
                          </span>
                        ) : (
                          <span className="text-zinc-400">Neutral</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {scores.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-zinc-400">
                      No holdings in portfolio yet. Add stocks in Portfolio Vault to see scores.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Score Breakdown & Evidence */}
        <div className="glass-panel p-6 h-[580px] flex flex-col justify-between rounded-none border-zinc-200 bg-white shadow-none">
          {selectedScore ? (
            <div className="space-y-6 overflow-y-auto pr-1 flex-grow">
              <div>
                <span className="text-[9px] bg-zinc-100 text-zinc-650 border border-zinc-250 px-2 py-0.5 rounded-none font-mono uppercase tracking-wider">
                  Signal Infiltration
                </span>
                <h3 className="text-base font-bold text-zinc-950 mt-3">
                  {selectedScore.company_name}
                </h3>
                <span className="text-[10px] text-zinc-500 font-mono block">
                  Ticker: {selectedScore.ticker}
                </span>
              </div>

              {/* Score breakdown banner */}
              <div className="border border-zinc-200 p-4 rounded-none bg-zinc-50 flex justify-between items-center">
                <div>
                  <span className="text-[9px] text-zinc-500 uppercase font-bold font-mono">Consolidated Score</span>
                  <div className="text-2xl font-mono font-bold mt-1 text-black">
                    {selectedScore.score}
                    <span className="text-xs text-zinc-500 font-sans font-medium ml-2 uppercase">/ 100</span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[9px] text-zinc-500 uppercase font-bold font-mono">Classification</span>
                  <div className="text-sm font-bold uppercase mt-2 text-zinc-900">
                    {selectedScore.label}
                  </div>
                </div>
              </div>

              {/* Evidence list */}
              <div className="space-y-3">
                <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5 border-b border-zinc-150 pb-1">
                  <ShieldAlert className="w-3.5 h-3.5 text-black" />
                  <span>Signals & Evidence</span>
                </h4>
                
                <div className="space-y-3.5">
                  {selectedScore.evidence.map((e: any, idx: number) => {
                    const isPositive = e.direction === "accumulation";
                    return (
                      <div key={idx} className="p-3 border border-zinc-200 rounded-none text-xs bg-white space-y-1">
                        <div className="flex justify-between items-center">
                          <span className="font-bold uppercase font-mono text-[9px] bg-zinc-100 px-1.5 py-0.5 text-zinc-650 border border-zinc-200">
                            {e.source.replace("_", " ")}
                          </span>
                          <span className={`text-[10px] font-mono font-bold ${isPositive ? "text-emerald-700" : "text-rose-700"}`}>
                            {isPositive ? "Accumulation" : "Distribution"}
                          </span>
                        </div>
                        <p className="text-zinc-800 leading-normal font-sans pt-1">
                          {e.description}
                        </p>
                      </div>
                    );
                  })}
                  {selectedScore.evidence.length === 0 && (
                    <div className="p-4 border border-zinc-200 border-dashed text-center text-zinc-400 text-xs rounded-none">
                      No significant smart money signals detected for this holding recently.
                    </div>
                  )}
                </div>
              </div>

              <div className="text-[10px] text-zinc-400 font-mono text-right pt-4 border-t border-zinc-100">
                LAST CALCULATION: {new Date(selectedScore.computed_at).toLocaleString()}
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-zinc-400 text-sm">
              Select a holding to view institutional scoring breakdown and source evidence.
            </div>
          )}
        </div>
      </div>

      {/* Daily Flows Overview Section */}
      <div className="glass-panel p-6 rounded-none border-zinc-200 bg-white shadow-none space-y-4">
        <div className="flex items-center gap-2 border-b border-zinc-250 pb-2">
          <TrendingUp className="w-5 h-5 text-black" />
          <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider">
            NSE Institutional Flows History (Daily net buys in ₹ Crores)
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-zinc-200 text-zinc-500 uppercase tracking-wider text-[10px]">
                <th className="py-2 font-bold">Trading Date</th>
                <th className="py-2 font-bold text-right">FII Net Flow</th>
                <th className="py-2 font-bold text-right">DII Net Flow</th>
                <th className="py-2 font-bold text-right">FII Buy</th>
                <th className="py-2 font-bold text-right">FII Sell</th>
                <th className="py-2 font-bold text-right">DII Buy</th>
                <th className="py-2 font-bold text-right">DII Sell</th>
                <th className="py-2 font-bold text-center">Market Regime</th>
              </tr>
            </thead>
            <tbody>
              {flows.map((f) => {
                const fiiNet = f.fii_buy_cr - f.fii_sell_cr;
                const diiNet = f.dii_buy_cr - f.dii_sell_cr;
                return (
                  <tr key={f.id} className="border-b border-zinc-100 hover:bg-zinc-50/50">
                    <td className="py-3 font-mono font-bold text-zinc-800">{f.date}</td>
                    <td className={`py-3 text-right font-mono font-bold ${fiiNet > 0 ? "text-emerald-700" : fiiNet < 0 ? "text-rose-700" : "text-zinc-500"}`}>
                      {fiiNet > 0 ? "+" : ""}₹{fiiNet.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr
                    </td>
                    <td className={`py-3 text-right font-mono font-bold ${diiNet > 0 ? "text-emerald-700" : diiNet < 0 ? "text-rose-700" : "text-zinc-500"}`}>
                      {diiNet > 0 ? "+" : ""}₹{diiNet.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Cr
                    </td>
                    <td className="py-3 text-right font-mono text-zinc-600">₹{f.fii_buy_cr.toLocaleString()} Cr</td>
                    <td className="py-3 text-right font-mono text-zinc-600">₹{f.fii_sell_cr.toLocaleString()} Cr</td>
                    <td className="py-3 text-right font-mono text-zinc-600">₹{f.dii_buy_cr.toLocaleString()} Cr</td>
                    <td className="py-3 text-right font-mono text-zinc-600">₹{f.dii_sell_cr.toLocaleString()} Cr</td>
                    <td className="py-3 text-center">
                      <span className={`px-2 py-0.5 border text-[9px] font-mono uppercase font-bold ${
                        f.market_regime === "bullish" 
                          ? "bg-emerald-50 text-emerald-800 border-emerald-250" 
                          : f.market_regime === "bearish" 
                          ? "bg-rose-50 text-rose-800 border-rose-250" 
                          : "bg-zinc-100 text-zinc-800 border-zinc-200"
                      }`}>
                        {f.market_regime}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {flows.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-zinc-400">
                    No institutional flow records available yet. Sync with NSE to fetch flow history.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
