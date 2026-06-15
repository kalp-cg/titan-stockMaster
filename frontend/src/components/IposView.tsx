"use client";

import React, { useEffect, useState } from "react";
import { FileText, Award, Layers, TrendingUp, BarChart2, Users, Calendar, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";

export default function IposView() {
  const [ipos, setIpos] = useState<any[]>([]);
  const [selectedIpoId, setSelectedIpoId] = useState<string | null>(null);
  const [activeSegment, setActiveSegment] = useState<"all" | "mainboard" | "sme">("all");

  useEffect(() => {
    async function loadIpos() {
      try {
        const data = await api.getIPOs();
        setIpos(data);
        if (data.length > 0 && !selectedIpoId) {
          setSelectedIpoId(data[0].id);
        }
      } catch (e) {
        console.error("Failed to load IPO pipeline", e);
      }
    }
    loadIpos();
  }, []);

  const handleSegmentChange = (segment: "all" | "mainboard" | "sme") => {
    setActiveSegment(segment);
    const filtered = ipos.filter((ipo) => {
      if (segment === "all") return true;
      return (ipo.ipo_type || "mainboard").toLowerCase() === segment;
    });
    if (filtered.length > 0) {
      const exists = filtered.some((ipo) => ipo.id === selectedIpoId);
      if (!exists) {
        setSelectedIpoId(filtered[0].id);
      }
    } else {
      setSelectedIpoId(null);
    }
  };

  const filteredIpos = ipos.filter((ipo) => {
    if (activeSegment === "all") return true;
    return (ipo.ipo_type || "mainboard").toLowerCase() === activeSegment;
  });

  const selectedIpo = ipos.find((i) => i.id === selectedIpoId);

  return (
    <div className="space-y-8 animate-fade-in text-zinc-900 bg-white">
      {/* Usability Warning Banner */}
      <div className="border border-zinc-200 bg-zinc-50 p-4 rounded-none flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-black shrink-0 mt-0.5" />
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-950 font-mono">Simulated IPO Valuation & GMP Disclaimer</h4>
          <p className="text-[10px] text-zinc-500 font-mono mt-1 leading-relaxed">
            Financial statements are parsed from draft Red Herring prospectuses (DRHP). However, Grey Market Premium (GMP) updates and final Analytical Strength Scores are simulated projection models designed for mock tracking. Do not treat these values as active bidding recommendations.
          </p>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: IPO Pipeline List */}
        <div className="lg:col-span-2 glass-panel p-6 h-[680px] flex flex-col justify-between rounded-none border-zinc-200 bg-white shadow-none">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 border-b border-zinc-200 pb-4">
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-black" />
              <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider">
                IPO Pipeline Disclosures
              </h3>
            </div>
            <div className="flex bg-zinc-150 p-1 rounded-none border border-zinc-200 text-xs font-semibold self-start sm:self-auto">
              {(["all", "mainboard", "sme"] as const).map((seg) => (
                <button
                  key={seg}
                  onClick={() => handleSegmentChange(seg)}
                  className={`px-3 py-1 rounded-none transition-all duration-200 capitalize ${
                    activeSegment === seg
                      ? "bg-black text-white"
                      : "text-zinc-650 hover:text-black border border-transparent"
                  }`}
                >
                  {seg === "all" ? "All IPOs" : seg}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-y-auto pr-1 flex-grow space-y-4">
            {filteredIpos.map((ipo) => {
              const statusColors = {
                upcoming: "bg-zinc-100 text-zinc-700 border border-zinc-350",
                open: "bg-emerald-50 text-emerald-700 border border-emerald-300",
                closed: "bg-rose-50 text-rose-700 border border-rose-300",
                listed: "bg-zinc-150 text-zinc-800 border border-zinc-300",
                withdrawn: "bg-zinc-200 text-zinc-500 border border-zinc-300",
              };
              const status = (ipo.status || "upcoming").toLowerCase() as keyof typeof statusColors;
              
              return (
                <div
                  key={ipo.id}
                  onClick={() => setSelectedIpoId(ipo.id)}
                  className={`p-4 rounded-none border cursor-pointer transition-all duration-300 flex justify-between items-center gap-4 ${
                    selectedIpoId === ipo.id
                      ? "bg-zinc-50 border-zinc-400"
                      : "bg-white border-zinc-200 hover:bg-zinc-50"
                  }`}
                >
                  <div>
                    <span className="font-bold text-zinc-900 text-sm">{ipo.name}</span>
                    <div className="flex gap-2 items-center mt-1.5 text-[10px] text-zinc-500 font-mono">
                      <span>₹{ipo.price_band_low} - ₹{ipo.price_band_high}</span>
                      <span>•</span>
                      <span>Lot: {ipo.lot_size}</span>
                      <span>•</span>
                      <span>Issue: ₹{ipo.issue_size_cr} Cr</span>
                    </div>
                  </div>

                  <div className="text-right flex flex-col justify-between h-[44px] items-end shrink-0">
                    <div className="flex gap-1.5 items-center">
                      <span className={`text-[9px] px-1.5 py-0.5 rounded-none border font-bold uppercase ${
                        (ipo.ipo_type || "mainboard").toLowerCase() === "sme"
                          ? "bg-zinc-100 text-zinc-805 border-zinc-300"
                          : "bg-zinc-200 text-zinc-900 border-zinc-400"
                      }`}>
                        {ipo.ipo_type === "sme" ? "SME" : "Mainboard"}
                      </span>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded-none border font-bold uppercase ${statusColors[status] || "bg-zinc-100"}`}>
                        {ipo.status}
                      </span>
                    </div>
                    {ipo.score && ipo.score.composite !== undefined && (
                      <span className="text-xs font-mono font-bold text-zinc-900">
                        Score {(ipo.score.composite ?? 0).toFixed(1)}/10
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
            {filteredIpos.length === 0 && (
              <div className="h-full flex items-center justify-center text-zinc-400 text-sm py-12">
                No IPOs found in this segment.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Attractiveness scorecard */}
        <div className="glass-panel p-6 h-[680px] flex flex-col justify-between rounded-none border-zinc-200 bg-white shadow-none">
          {selectedIpo ? (
            <div className="space-y-6 overflow-y-auto pr-1 flex-grow">
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-[9px] bg-zinc-100 text-zinc-600 border border-zinc-200 px-2 py-0.5 rounded-none font-mono uppercase tracking-wider">
                    Attractiveness Rating
                  </span>
                  <span className={`text-[9px] px-2 py-0.5 rounded-none border font-bold uppercase ${
                    (selectedIpo.ipo_type || "mainboard").toLowerCase() === "sme"
                      ? "bg-zinc-100 text-zinc-800 border-zinc-300"
                      : "bg-zinc-200 text-zinc-950 border-zinc-450"
                  }`}>
                    {selectedIpo.ipo_type === "sme" ? "SME" : "Mainboard"}
                  </span>
                </div>
                <h3 className="text-base font-bold text-zinc-950 mt-1 leading-snug">
                  {selectedIpo.name}
                </h3>
                <span className="text-[10px] text-zinc-500 font-mono block">
                  {selectedIpo.sector} | {selectedIpo.industry}
                </span>
              </div>

              {/* Premium GMP & Listing Estimate Card */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-zinc-50 border border-zinc-200 rounded-none p-4 flex flex-col justify-between">
                  <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider block mb-1">
                    {selectedIpo.status === "listed" ? "Listing Gain" : "Grey Market Premium (GMP)"}
                  </span>
                  <div className="flex items-baseline gap-2">
                    {selectedIpo.status === "listed" ? (
                      <span className="text-xl font-bold font-mono text-emerald-700">
                        {selectedIpo.listing_gain_pct ? `+${selectedIpo.listing_gain_pct}%` : "N/A"}
                      </span>
                    ) : (
                      <>
                        <span className="text-xl font-bold font-mono text-emerald-700">
                          ₹{selectedIpo.gmp ?? 0}
                        </span>
                        <span className="text-xs font-semibold text-emerald-600">
                          +{((selectedIpo.gmp ?? 0) / (selectedIpo.price_band_high || 1) * 100).toFixed(1)}%
                        </span>
                      </>
                    )}
                  </div>
                </div>
                
                <div className="bg-zinc-50 border border-zinc-200 rounded-none p-4 flex flex-col justify-between">
                  <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider block mb-1">
                    {selectedIpo.status === "listed" ? "Actual Listing Price" : "Est. Listing Price"}
                  </span>
                  <span className="text-xl font-bold font-mono text-zinc-950">
                    ₹{selectedIpo.status === "listed" 
                      ? (selectedIpo.listing_price ?? (selectedIpo.price_band_high + (selectedIpo.gmp ?? 0))).toFixed(1)
                      : (selectedIpo.price_band_high + (selectedIpo.gmp ?? 0)).toFixed(1)
                    }
                  </span>
                </div>
              </div>

              {/* Important Timeline / Dates widget */}
              <div className="bg-zinc-50 border border-zinc-200 rounded-none p-4 text-xs">
                <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2 flex items-center gap-1.5 border-b border-zinc-200 pb-1">
                  <Calendar className="w-3.5 h-3.5 text-black" />
                  <span>IPO Calendar Timeline</span>
                </h4>
                <div className="space-y-2 font-mono text-zinc-800">
                  <div className="flex justify-between">
                    <span className="text-zinc-500 font-sans">Issue Opens:</span>
                    <span>{selectedIpo.open_date ? new Date(selectedIpo.open_date).toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' }) : "TBA"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500 font-sans">Issue Closes:</span>
                    <span>{selectedIpo.close_date ? new Date(selectedIpo.close_date).toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' }) : "TBA"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500 font-sans">Expected Listing:</span>
                    <span>{selectedIpo.listing_date ? new Date(selectedIpo.listing_date).toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' }) : "TBA"}</span>
                  </div>
                </div>
              </div>

              {/* Score breakdown metrics */}
              {selectedIpo.score ? (
                <div className="space-y-4">
                  <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
                    <Award className="w-4 h-4 text-black" />
                    <span>Composite Score Breakdown</span>
                  </h4>

                  <div className="space-y-3 text-xs">
                    {/* Revenue Growth Score */}
                    <div className="space-y-1">
                      <div className="flex justify-between">
                        <span className="text-zinc-650">YoY Revenue Growth</span>
                        <span className="font-mono text-zinc-800">{selectedIpo.score.revenue_growth_score}/10</span>
                      </div>
                      <div className="w-full bg-zinc-100 h-1.5 rounded-none overflow-hidden border border-zinc-200">
                        <div style={{ width: `${selectedIpo.score.revenue_growth_score * 10}%` }} className="bg-black h-full rounded-none" />
                      </div>
                    </div>

                    {/* Profitability */}
                    <div className="space-y-1">
                      <div className="flex justify-between">
                        <span className="text-zinc-655">Operating Margins</span>
                        <span className="font-mono text-zinc-800">{selectedIpo.score.profitability_score}/10</span>
                      </div>
                      <div className="w-full bg-zinc-100 h-1.5 rounded-none overflow-hidden border border-zinc-200">
                        <div style={{ width: `${selectedIpo.score.profitability_score * 10}%` }} className="bg-black h-full rounded-none" />
                      </div>
                    </div>

                    {/* Balance sheet debt */}
                    <div className="space-y-1">
                      <div className="flex justify-between">
                        <span className="text-zinc-650">Leverage Strength</span>
                        <span className="font-mono text-zinc-800">{selectedIpo.score.debt_score}/10</span>
                      </div>
                      <div className="w-full bg-zinc-100 h-1.5 rounded-none overflow-hidden border border-zinc-200">
                        <div style={{ width: `${selectedIpo.score.debt_score * 10}%` }} className="bg-black h-full rounded-none" />
                      </div>
                    </div>

                    {/* Valuations */}
                    <div className="space-y-1">
                      <div className="flex justify-between">
                        <span className="text-zinc-650">Valuation Pricing</span>
                        <span className="font-mono text-zinc-800">{selectedIpo.score.valuation_score}/10</span>
                      </div>
                      <div className="w-full bg-zinc-100 h-1.5 rounded-none overflow-hidden border border-zinc-200">
                        <div style={{ width: `${selectedIpo.score.valuation_score * 10}%` }} className="bg-black h-full rounded-none" />
                      </div>
                    </div>

                    {/* Grey Market Premium GMP */}
                    <div className="space-y-1">
                      <div className="flex justify-between">
                        <span className="text-zinc-650">GMP Demand Premium</span>
                        <span className="font-mono text-zinc-800">{selectedIpo.score.gmp_score}/10</span>
                      </div>
                      <div className="w-full bg-zinc-100 h-1.5 rounded-none overflow-hidden border border-zinc-200">
                        <div style={{ width: `${selectedIpo.score.gmp_score * 10}%` }} className="bg-black h-full rounded-none" />
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-zinc-400 text-xs py-4 text-center">Scorecard details pending calculation...</p>
              )}

              {/* Category Subscriptions Progress Card */}
              {selectedIpo.status !== "upcoming" && (
                <div className="space-y-3 bg-zinc-50 p-4 border border-zinc-200 rounded-none text-xs">
                  <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5 border-b border-zinc-200 pb-1">
                    <Users className="w-3.5 h-3.5 text-black" />
                    <span>Category Subscriptions</span>
                  </h4>
                  
                  {(() => {
                    const overall = selectedIpo.subscription_overall ?? 0;
                    const qib = selectedIpo.subscription_qib ?? 0;
                    const hni = selectedIpo.subscription_hni ?? 0;
                    const retail = selectedIpo.subscription_retail ?? 0;
                    
                    const maxVal = Math.max(1, overall, qib, hni, retail);
                    
                    return (
                      <div className="space-y-3 pt-1">
                        {/* QIB */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-[11px]">
                            <span className="text-zinc-500">Institutional (QIB)</span>
                            <span className="font-mono font-bold text-zinc-800">{qib.toFixed(2)}x</span>
                          </div>
                          <div className="w-full bg-zinc-100 h-1.5 rounded-none overflow-hidden border border-zinc-200">
                            <div 
                              style={{ width: `${(qib / maxVal) * 100}%` }} 
                              className="bg-black h-full rounded-none transition-all duration-500" 
                            />
                          </div>
                        </div>

                        {/* HNI */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-[11px]">
                            <span className="text-zinc-500">Non-Institutional (HNI/NII)</span>
                            <span className="font-mono font-bold text-zinc-800">{hni.toFixed(2)}x</span>
                          </div>
                          <div className="w-full bg-zinc-100 h-1.5 rounded-none overflow-hidden border border-zinc-200">
                            <div 
                              style={{ width: `${(hni / maxVal) * 100}%` }} 
                              className="bg-black h-full rounded-none transition-all duration-500" 
                            />
                          </div>
                        </div>

                        {/* Retail */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-[11px]">
                            <span className="text-zinc-500">Retail Investors</span>
                            <span className="font-mono font-bold text-zinc-800">{retail.toFixed(2)}x</span>
                          </div>
                          <div className="w-full bg-zinc-100 h-1.5 rounded-none overflow-hidden border border-zinc-200">
                            <div 
                              style={{ width: `${(retail / maxVal) * 100}%` }} 
                              className="bg-black h-full rounded-none transition-all duration-500" 
                            />
                          </div>
                        </div>

                        {/* Overall */}
                        <div className="flex justify-between items-center bg-zinc-200 p-2.5 rounded-none border border-zinc-300 mt-2 font-bold text-zinc-950">
                          <span className="text-[11px] uppercase tracking-wider">Overall Subscription</span>
                          <span className="text-sm font-mono">
                            {overall.toFixed(2)}x
                          </span>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* Financial fundamentals */}
              <div className="space-y-3 bg-zinc-50 p-4 border border-zinc-200 rounded-none text-xs">
                <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5 border-b border-zinc-200 pb-1">
                  <BarChart2 className="w-3.5 h-3.5 text-black" />
                  <span>Reported Financial Metrics</span>
                </h4>
                <div className="grid grid-cols-2 gap-y-2.5 gap-x-4 pt-1 font-mono text-zinc-850">
                  <div className="flex justify-between border-b border-zinc-200 pb-1">
                    <span className="text-zinc-500 font-sans">Revenue</span>
                    <span>₹{selectedIpo.financials.revenue} Cr</span>
                  </div>
                  <div className="flex justify-between border-b border-zinc-200 pb-1">
                    <span className="text-zinc-500 font-sans">Growth YoY</span>
                    <span>{((selectedIpo.financials?.revenue_growth_yoy ?? 0) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex justify-between border-b border-zinc-200 pb-1">
                    <span className="text-zinc-500 font-sans">Net Profit</span>
                    <span>₹{selectedIpo.financials.net_profit} Cr</span>
                  </div>
                  <div className="flex justify-between border-b border-zinc-200 pb-1">
                    <span className="text-zinc-500 font-sans">D/E Ratio</span>
                    <span>{selectedIpo.financials.debt_to_equity}</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-zinc-400 text-sm">
              Select an IPO to view scorecard & metrics details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
