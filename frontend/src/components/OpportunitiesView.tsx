"use client";

import React, { useEffect, useState } from "react";
import { Compass, RefreshCw, AlertCircle, ArrowUpRight, ArrowDownRight, Share2 } from "lucide-react";
import { api } from "@/lib/api";

export default function OpportunitiesView() {
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedOppId, setSelectedOppId] = useState<string | null>(null);

  async function loadOpportunities() {
    setLoading(true);
    try {
      const data = await api.getOpportunities();
      setOpportunities(data);
      if (data.length > 0 && !selectedOppId) {
        setSelectedOppId(data[0].id);
      }
    } catch (e) {
      console.error("Failed to fetch opportunities", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadOpportunities();
  }, []);

  const selectedOpp = opportunities.find((o) => o.id === selectedOppId);

  return (
    <div className="space-y-8 animate-fade-in text-zinc-900 bg-white">
      <div className="flex items-center justify-between border-b border-zinc-200 pb-4">
        <div>
          <h2 className="text-lg font-bold text-zinc-950 uppercase tracking-wider">Opportunity Alpha Scanner</h2>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wide">
            Traverses the economic graph to identify 1st, 2nd, and 3rd order effects
          </p>
        </div>
        <button
          onClick={loadOpportunities}
          disabled={loading}
          className="flex items-center gap-2 bg-zinc-50 border border-zinc-200 hover:border-zinc-300 text-zinc-700 hover:text-black py-2 px-4 rounded-none text-xs transition-all duration-300"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          <span>{loading ? "Scanning..." : "Rescan Graph"}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: List of Opportunities */}
        <div className="lg:col-span-2 glass-panel p-6 h-[560px] flex flex-col justify-between rounded-none border-zinc-200 bg-white shadow-none">
          <div className="flex items-center gap-2 mb-6 border-b border-zinc-200 pb-2">
            <Compass className="w-5 h-5 text-black" />
            <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider">
              Discovered Opportunities
            </h3>
          </div>

          <div className="overflow-y-auto pr-1 flex-grow space-y-4">
            {opportunities.map((opp) => {
              const isLong = opp.direction === "long";
              const isThird = opp.order === "third_order";
              const isSecond = opp.order === "second_order";
              
              return (
                <div
                  key={opp.id}
                  onClick={() => setSelectedOppId(opp.id)}
                  className={`p-4 rounded-none border cursor-pointer transition-all duration-300 flex justify-between items-center gap-4 ${
                    selectedOppId === opp.id
                      ? "bg-zinc-50 border-zinc-400"
                      : "bg-white border-zinc-200 hover:bg-zinc-50"
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2.5">
                      <span className="font-bold text-zinc-900 text-sm">{opp.company_name}</span>
                      <span className="text-[10px] text-zinc-500 font-mono">({opp.ticker})</span>
                      <span
                        className={`text-[9px] px-1.5 py-0.5 rounded-none uppercase font-mono font-bold ${
                          isThird
                            ? "bg-zinc-200 text-zinc-800 border border-zinc-300"
                            : isSecond
                            ? "bg-zinc-100 text-zinc-800"
                            : "bg-zinc-50 text-zinc-550 border border-zinc-200"
                        }`}
                      >
                        {opp.order.replace("_", " ")}
                      </span>
                    </div>
                    <span className="text-xs text-zinc-650 block truncate max-w-lg">
                      Trigger: {opp.trigger_event_title}
                    </span>
                  </div>

                  <div className="text-right">
                    <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded-none uppercase ${isLong ? "bg-emerald-50 text-emerald-700 border border-emerald-250" : "bg-rose-50 text-rose-700 border border-rose-250"}`}>
                      {opp.direction}
                    </span>
                    <span className="text-[10px] text-zinc-500 block mt-1 font-mono">
                      Conf {(opp.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              );
            })}
            {!opportunities.length && (
              <p className="text-zinc-400 text-xs py-12 text-center">No opportunities matched. Ingesting global news feeds will populate scanner...</p>
            )}
          </div>
        </div>

        {/* Right Column: Reasoning & Trace Chains */}
        <div className="glass-panel p-6 h-[560px] flex flex-col justify-between rounded-none border-zinc-200 bg-white shadow-none">
          {selectedOpp ? (
            <div className="space-y-6 overflow-y-auto pr-1 flex-grow">
              <div>
                <span className="text-[9px] bg-zinc-100 text-zinc-600 border border-zinc-200 px-2 py-0.5 rounded-none font-mono uppercase tracking-wider">
                  Causal Chain
                </span>
                <h3 className="text-base font-bold text-zinc-950 mt-3">
                  {selectedOpp.company_name} ({selectedOpp.ticker})
                </h3>
                <span className="text-[10px] text-zinc-500 font-mono block">
                  Sector: {selectedOpp.sector}
                </span>
              </div>

              {/* expected impact */}
              <div className="flex justify-between items-center bg-zinc-50 p-4 border border-zinc-200 rounded-none">
                <span className="text-xs text-zinc-500 font-bold uppercase">Expected Impact</span>
                <span className={`text-lg font-mono font-bold ${selectedOpp.direction === "long" ? "text-emerald-700" : "text-rose-700"}`}>
                  {selectedOpp.direction === "long" ? "+" : "-"}{selectedOpp.expected_impact_pct}%
                </span>
              </div>

              {/* Trace Path */}
              <div className="space-y-3">
                <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5 border-b border-zinc-100 pb-1">
                  <Share2 className="w-3.5 h-3.5 text-black" />
                  <span>Graph Node Traversal</span>
                </h4>
                
                <div className="relative pl-4 border-l border-zinc-350 space-y-4 py-1.5 text-xs text-zinc-800">
                  {selectedOpp.graph_path.map((step: string) => (
                    <div key={step} className="relative">
                      {/* Node point marker */}
                      <div className="absolute -left-[20.5px] top-1.5 w-2 h-2 rounded-none bg-black" />
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Narrative explanation */}
              <div className="space-y-2">
                <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Reasoning Explanation</h4>
                <p className="text-xs text-zinc-700 leading-relaxed bg-zinc-50 p-3 rounded-none border border-zinc-200">
                  {selectedOpp.reasoning[1]}
                </p>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-zinc-400 text-sm">
              Select an opportunity to view traversal paths and explanations.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
