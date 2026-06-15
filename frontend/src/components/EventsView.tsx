"use client";

import React, { useEffect, useState } from "react";
import { Globe, Filter, AlertCircle, Target, Layers, Clock } from "lucide-react";
import { api } from "@/lib/api";

export default function EventsView() {
  const [events, setEvents] = useState<any[]>([]);
  const [category, setCategory] = useState<string>("");
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [selectedEventDetails, setSelectedEventDetails] = useState<any>(null);
  const [impactedCompanies, setImpactedCompanies] = useState<any[]>([]);
  const [analogies, setAnalogies] = useState<any>(null);
  const [causalChains, setCausalChains] = useState<any[]>([]);

  useEffect(() => {
    async function loadEvents() {
      try {
        const data = await api.getEvents(category || undefined);
        setEvents(data);
        if (data.length > 0 && !selectedEventId) {
          setSelectedEventId(data[0].id);
        }
      } catch (e) {
        console.error("Failed to load events", e);
      }
    }
    loadEvents();
  }, [category]);

  useEffect(() => {
    async function loadEventDetails() {
      if (!selectedEventId) return;
      try {
        const details = await api.getEvent(selectedEventId);
        setSelectedEventDetails(details);
        
        // Fetch impact, analogies, and causal chains in parallel
        const [impact, analogyData, causalData] = await Promise.all([
          api.getEventImpact(selectedEventId),
          api.getHistoricalAnalogy(selectedEventId).catch(() => null),
          api.getEventCausalChain(selectedEventId).catch(() => [])
        ]);
        setImpactedCompanies(impact || []);
        setAnalogies(analogyData);
        setCausalChains(causalData || []);
      } catch (e) {
        console.error("Failed to load event details or analogies", e);
      }
    }
    loadEventDetails();
  }, [selectedEventId]);

  const categories = [
    { value: "", label: "All Categories" },
    { value: "geopolitical", label: "Geopolitical" },
    { value: "economic", label: "Economic" },
    { value: "company", label: "Company" },
    { value: "regulatory", label: "Regulatory" },
    { value: "market", label: "Market" },
  ];

  return (
    <div className="space-y-8 animate-fade-in text-zinc-900 bg-white">
      {/* Category Filter */}
      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-none border-b border-zinc-200">
        {categories.map((cat) => (
          <button
            key={cat.value}
            onClick={() => {
              setCategory(cat.value);
              setSelectedEventId(null);
              setSelectedEventDetails(null);
              setImpactedCompanies([]);
            }}
            className={`px-4 py-2 text-xs font-semibold rounded-none border transition-all duration-300 whitespace-nowrap ${
              category === cat.value
                ? "bg-black text-white border-black"
                : "bg-zinc-50 text-zinc-650 border-zinc-200 hover:text-black hover:bg-zinc-100"
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left column: Event Timeline list */}
        <div className="lg:col-span-2 glass-panel p-6 h-[600px] flex flex-col rounded-none border-zinc-200 bg-white shadow-none">
          <div className="flex items-center gap-2 mb-6 border-b border-zinc-200 pb-2">
            <Globe className="w-5 h-5 text-black" />
            <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider">
              Market Intelligence Timeline
            </h3>
          </div>

          <div className="overflow-y-auto pr-2 flex-grow space-y-4">
            {events.map((ev) => {
              const isActive = selectedEventId === ev.id;
              const sentimentColors = {
                positive: "bg-emerald-50 text-emerald-700 border-emerald-300",
                negative: "bg-rose-50 text-rose-700 border-rose-300",
                neutral: "bg-zinc-100 text-zinc-650 border-zinc-300",
              };
              const sent = (ev.sentiment || "neutral").toLowerCase() as keyof typeof sentimentColors;
              
              return (
                <div
                  key={ev.id}
                  onClick={() => setSelectedEventId(ev.id)}
                  className={`p-4 rounded-none border cursor-pointer transition-all duration-300 flex justify-between gap-4 ${
                    isActive
                      ? "bg-zinc-50 border-zinc-400"
                      : "bg-white border-zinc-200 hover:bg-zinc-50"
                  }`}
                >
                  <div className="space-y-2 flex-grow">
                    <div className="flex items-center gap-3">
                      <span className="text-[9px] uppercase font-bold tracking-wider text-zinc-700 bg-zinc-200 px-2 py-0.5 rounded-none">
                        {ev.category}
                      </span>
                      <span className="text-[10px] text-zinc-400 font-mono">
                        {new Date(ev.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <h4 className="text-sm font-bold text-zinc-950 leading-snug">{ev.title}</h4>
                    <p className="text-xs text-zinc-650 line-clamp-2">{ev.summary}</p>
                  </div>
                  <div className="flex flex-col justify-between items-end shrink-0">
                    <span className={`text-[10px] px-2 py-0.5 rounded-none border font-bold uppercase ${sentimentColors[sent] || "bg-zinc-100 border-zinc-200"}`}>
                      {ev.sentiment}
                    </span>
                    <span className="text-xs font-mono text-zinc-800 font-bold">
                      Sev {((ev.severity ?? 0) * 10).toFixed(1)}
                    </span>
                  </div>
                </div>
              );
            })}
            {!events.length && (
              <p className="text-sm text-zinc-400 py-12 text-center">No events found in this category.</p>
            )}
          </div>
        </div>

        {/* Right column: Selected Event Details & Graph impact propagation */}
        <div className="glass-panel p-6 h-[600px] flex flex-col justify-between rounded-none border-zinc-200 bg-white shadow-none">
          {selectedEventDetails ? (
            <div className="space-y-6 overflow-y-auto pr-1 flex-grow">
              <div>
                <span className="text-[9px] bg-zinc-100 text-zinc-605 border border-zinc-200 px-2 py-0.5 rounded-none font-mono uppercase tracking-wider">
                  Details
                </span>
                <h3 className="text-base font-bold text-zinc-950 mt-3 leading-snug">
                  {selectedEventDetails.title}
                </h3>
                <span className="text-[10px] text-zinc-500 font-mono block mt-1">
                  Source: {selectedEventDetails.source} | {new Date(selectedEventDetails.timestamp).toLocaleDateString()}
                </span>
              </div>

              {/* NER entities */}
              {selectedEventDetails.entities?.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5 border-b border-zinc-100 pb-1">
                    <Target className="w-3.5 h-3.5 text-black" />
                    <span>Extracted NLP Entities</span>
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedEventDetails.entities.map((ent: any) => (
                      <span
                        key={ent.text}
                        className="text-[10px] bg-zinc-50 border border-zinc-200 text-zinc-800 px-2.5 py-1 rounded-none font-medium"
                      >
                        {ent.normalized_name}
                        <span className="text-[8px] text-zinc-450 ml-1 font-mono">
                          {ent.entity_type}
                        </span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Causal Chain Economy Propagation */}
              <div className="space-y-4">
                <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5 border-b border-zinc-100 pb-1">
                  <Globe className="w-3.5 h-3.5 text-black" />
                  <span>Market Causality Chain</span>
                </h4>
                
                {causalChains && causalChains.length > 0 ? (
                  <div className="space-y-6">
                    {causalChains.map((c: any, cIdx: number) => (
                      <div key={cIdx} className="space-y-4">
                        <div className="flex justify-between items-center text-xs font-bold font-mono bg-zinc-100 p-2.5 border border-zinc-200 rounded-none text-zinc-900">
                          <span>TRIGGER: {c.trigger_label}</span>
                          <span className={c.base_impact >= 0 ? "text-emerald-700" : "text-rose-700"}>
                            {c.base_impact >= 0 ? "+" : ""}{(c.base_impact * 10).toFixed(1)} severity
                          </span>
                        </div>

                        <div className="relative pl-6 border-l border-zinc-200 ml-3.5 space-y-5 py-1">
                          {c.chain.map((node: any, nIdx: number) => {
                            const isPositive = node.direction > 0;
                            const hopLabels = ["", "Primary", "Secondary", "Tertiary", "Quaternary"];
                            const label = hopLabels[node.depth] || `${node.depth}-order`;
                            
                            return (
                              <div key={nIdx} className="relative group">
                                {/* Bullet indicator on the timeline */}
                                <div className="absolute -left-[30.5px] top-1.5 w-2 h-2 rounded-none bg-black border border-black group-hover:bg-white transition-colors duration-150" />
                                
                                <div className="space-y-0.5">
                                  <div className="flex items-center gap-2">
                                    <span className="text-[9px] uppercase font-bold tracking-wider text-zinc-550 font-mono">
                                      {label} Impact
                                    </span>
                                    <span className={`text-[8px] px-1 py-0.2 border uppercase font-mono font-bold ${
                                      node.node_type === "company"
                                        ? "bg-zinc-250 text-zinc-800 border-zinc-350"
                                        : "bg-zinc-100 text-zinc-650 border-zinc-200"
                                    }`}>
                                      {node.node_type}
                                    </span>
                                  </div>
                                  
                                  <div className="flex justify-between items-center text-xs font-bold text-zinc-950">
                                    <span>{node.label}</span>
                                    <span className={`font-mono text-[10px] ${isPositive ? "text-emerald-700" : "text-rose-700"}`}>
                                      {isPositive ? "▲" : "▼"} {(node.impact * 10).toFixed(1)}
                                    </span>
                                  </div>

                                  <div className="text-[10px] text-zinc-500 leading-normal font-mono">
                                    {node.reason}
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-zinc-450 py-4 text-center italic border border-dashed border-zinc-200">
                    No causal dependencies propagated for this event type.
                  </p>
                )}
              </div>

              {/* Graph impact propagation */}
              <div className="space-y-4">
                <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5 border-b border-zinc-100 pb-1">
                  <Layers className="w-3.5 h-3.5 text-black" />
                  <span>Downstream Company Impacts</span>
                </h4>
                
                <div className="space-y-3">
                  {/* Downstream impacts list */}
                  {impactedCompanies.map((comp) => {
                    const isPos = comp.direction > 0;
                    return (
                      <div
                        key={comp.ticker}
                        className="p-3 bg-zinc-50 border border-zinc-200 rounded-none flex items-center justify-between"
                      >
                        <div>
                          <span className="text-xs font-bold text-zinc-900">{comp.ticker}</span>
                          <span className="text-[10px] text-zinc-500 block">{comp.company_name}</span>
                        </div>
                        <div className="text-right">
                          <span className={`text-xs font-mono font-bold ${isPos ? "text-emerald-700" : "text-rose-700"}`}>
                            {isPos ? "+" : ""}{((comp.direction ?? 0) * (comp.magnitude ?? 0) * 10).toFixed(1)}
                          </span>
                          <span className="text-[9px] text-zinc-550 block font-mono">
                            Conf {((comp.confidence ?? 0) * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    );
                  })}
                  {!impactedCompanies.length && (
                    <p className="text-xs text-zinc-400 py-4 text-center">
                      No matching economic graph relationships triggered.
                    </p>
                  )}
                </div>
              </div>

              {/* Historical Mirror Panel */}
              <div className="space-y-4 pt-4 border-t border-zinc-200">
                <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5 border-b border-zinc-100 pb-1">
                  <Clock className="w-3.5 h-3.5 text-black" />
                  <span>Historical Mirror (Analogies)</span>
                </h4>
                
                {analogies && analogies.analogies?.length > 0 ? (
                  <div className="space-y-4">
                    <p className="text-xs text-zinc-700 bg-zinc-50 border border-zinc-200 p-3 rounded-none italic font-sans leading-normal">
                      {analogies.summary}
                    </p>

                    <div className="grid grid-cols-2 gap-4 bg-zinc-50 border border-zinc-200 p-3 rounded-none font-mono text-xs text-zinc-800">
                      <div>
                        <span className="text-[9px] text-zinc-500 uppercase block font-sans font-bold">AVG 30D REACTION</span>
                        <span className={`font-bold ${(analogies.avg_expected_impact_30d ?? 0) >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                          {(analogies.avg_expected_impact_30d ?? 0) >= 0 ? "+" : ""}{analogies.avg_expected_impact_30d}%
                        </span>
                      </div>
                      <div>
                        <span className="text-[9px] text-zinc-500 uppercase block font-sans font-bold">AVG 60D REACTION</span>
                        <span className={`font-bold ${(analogies.avg_expected_impact_60d ?? 0) >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                          {(analogies.avg_expected_impact_60d ?? 0) >= 0 ? "+" : ""}{analogies.avg_expected_impact_60d}%
                        </span>
                      </div>
                    </div>

                    <div className="space-y-3">
                      {analogies.analogies.map((a: any) => (
                        <div key={a.event_id} className="p-3 border border-zinc-200 rounded-none bg-white space-y-1">
                          <div className="flex justify-between items-center text-xs">
                            <span className="font-bold text-zinc-950 leading-snug pr-2">
                              {a.year} — {a.title}
                            </span>
                            <span className="font-mono text-[9px] text-zinc-550 shrink-0 font-bold">
                              {(a.similarity_score * 100).toFixed(0)}% SIM
                            </span>
                          </div>
                          <p className="text-[11px] text-zinc-600 leading-normal font-sans pb-1.5 border-b border-zinc-100">
                            {a.description}
                          </p>
                          <div className="flex gap-4 pt-1.5 text-[9px] font-mono text-zinc-750">
                            <div>
                              <span>Nifty 30d: </span>
                              <span className={`font-bold ${a.nifty_impact_30d >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                                {a.nifty_impact_30d >= 0 ? "+" : ""}{a.nifty_impact_30d}%
                              </span>
                            </div>
                            <div>
                              <span>60d: </span>
                              <span className={`font-bold ${a.nifty_impact_60d >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                                {a.nifty_impact_60d >= 0 ? "+" : ""}{a.nifty_impact_60d}%
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-zinc-455 py-4 text-center italic border border-dashed border-zinc-200">
                    No historically similar events seeded for this scenario.
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-zinc-400 text-sm">
              Select an event to view details & impact analysis.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
