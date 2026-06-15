"use client";

import React, { useState, useEffect } from "react";
import { 
  Search, 
  Zap, 
  TrendingUp, 
  TrendingDown, 
  ShieldAlert, 
  Play, 
  Loader2, 
  ArrowRight, 
  AlertTriangle,
  Layers,
  Activity,
  Briefcase
} from "lucide-react";
import { api } from "@/lib/api";

const PREDEFINED_SCENARIOS = [
  {
    title: "Crude Oil Shock (+30%)",
    query: "Crude Oil rises 30%",
    desc: "Simulates geopolitical oil supply shocks affecting utilities, aviation, and paint industries.",
    category: "Geopolitical / Commodity"
  },
  {
    title: "US Fed Rate Cut (-50bps)",
    query: "Jerome Powell Federal Reserve cuts interest rates 50bps",
    desc: "Simulates monetary policy easing that benefits banking, finance, and global tech capital flows.",
    category: "Monetary Policy"
  },
  {
    title: "Semiconductor Supply Freeze",
    query: "Semiconductor supply chain freeze",
    desc: "Simulates hardware/chip production bottlenecks hurting automakers and technology exporters.",
    category: "Supply Chain"
  },
  {
    title: "Govt Infrastructure Capex Push",
    query: "Narendra Modi infrastructure capex budget expansion",
    desc: "Simulates heavy domestic capex spending targeting infrastructure and green power grids.",
    category: "Fiscal Budget"
  },
  {
    title: "Trade War Tariff Hike (+20%)",
    query: "Donald Trump trade tariff hike on imports",
    desc: "Simulates high import tariffs disrupting global exports, IT services, and metal supply chains.",
    category: "Macro Trade"
  }
];

export default function SimulatorView({ prices = {} }: { prices?: Record<string, any> }) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [event, setEvent] = useState<any>(null);
  const [impacts, setImpacts] = useState<any[]>([]);
  const [portfolio, setPortfolio] = useState<any>(null);
  const [predictions, setPredictions] = useState<Record<string, any>>({});
  const [selectedImpact, setSelectedImpact] = useState<any>(null);

  // Load portfolio for stress testing
  useEffect(() => {
    async function loadPortfolio() {
      try {
        const port = await api.getPortfolio();
        setPortfolio(port);
      } catch (e) {
        console.error("Failed to load portfolio for simulator", e);
      }
    }
    loadPortfolio();
  }, []);

  const runSimulation = async (simulationQuery: string) => {
    if (!simulationQuery.trim()) return;
    setLoading(true);
    setEvent(null);
    setImpacts([]);
    setSelectedImpact(null);

    try {
      // 1. Search (triggers hypothetical event generation & impact propagation on the backend)
      const results = await api.search(simulationQuery);
      if (results && results.length > 0) {
        const simEvent = results[0]; // Get the generated simulated event
        setEvent(simEvent);

        // 2. Fetch the specific event impacts from the knowledge graph
        const eventImpacts = await api.getEventImpact(simEvent.id);
        setImpacts(eventImpacts || []);

        // 3. Fetch latest predictions for portfolio stress test comparison
        const portPreds = await api.getPortfolioPredictions();
        setPredictions(portPreds || {});

        if (eventImpacts && eventImpacts.length > 0) {
          setSelectedImpact(eventImpacts[0]);
        }
      }
    } catch (e) {
      console.error("Simulation execution failed", e);
    } finally {
      setLoading(false);
    }
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runSimulation(query);
  };

  // Map simulated impacts to the user's active portfolio holdings
  const getPortfolioStressResults = () => {
    if (!portfolio || !portfolio.holdings || impacts.length === 0) return [];

    return portfolio.holdings.map((holding: any) => {
      // Find matching impact in the simulated impacts list
      const impact = impacts.find((imp) => imp.ticker === holding.ticker);
      
      const liveData = prices[holding.ticker];
      const currentPrice = liveData ? (liveData.price ?? holding.current_price) : holding.current_price;
      const currentVal = currentPrice * holding.quantity;

      if (!impact) {
        return {
          ticker: holding.ticker,
          companyName: holding.company_name,
          quantity: holding.quantity,
          currentPrice,
          currentVal,
          expectedMovePct: 0.0,
          simulatedPrice: currentPrice,
          simulatedVal: currentVal,
          deltaValue: 0.0,
          impactLevel: "Neutral"
        };
      }

      // Calculate expected move % based on direction and magnitude (severity scales it)
      const severityScale = event ? event.severity : 0.5;
      const expectedMovePct = impact.direction * impact.magnitude * severityScale * 10; // scaled up to %
      
      const simulatedPrice = currentPrice * (1 + expectedMovePct / 100);
      const simulatedVal = simulatedPrice * holding.quantity;
      const deltaValue = simulatedVal - currentVal;

      let impactLevel = "Neutral";
      if (expectedMovePct >= 2.0) impactLevel = "Strong Positive";
      else if (expectedMovePct > 0.3) impactLevel = "Positive";
      else if (expectedMovePct <= -2.0) impactLevel = "Severe Risk";
      else if (expectedMovePct < -0.3) impactLevel = "Risk";

      return {
        ticker: holding.ticker,
        companyName: holding.company_name,
        quantity: holding.quantity,
        currentPrice,
        currentVal,
        expectedMovePct,
        simulatedPrice,
        simulatedVal,
        deltaValue,
        impactLevel
      };
    });
  };

  const stressResults = getPortfolioStressResults();
  const totalPortfolioValue = stressResults.reduce((acc: number, curr: any) => acc + curr.currentVal, 0);
  const totalSimulatedValue = stressResults.reduce((acc: number, curr: any) => acc + curr.simulatedVal, 0);
  const totalDeltaValue = totalSimulatedValue - totalPortfolioValue;
  const portfolioDeltaPct = totalPortfolioValue > 0 ? (totalDeltaValue / totalPortfolioValue) * 100 : 0;

  return (
    <div className="space-y-8 animate-fade-in text-zinc-900 bg-white">
      {/* Top Header */}
      <div className="flex justify-between items-start border-b border-zinc-200 pb-5">
        <div>
          <h2 className="text-xl font-bold text-zinc-950 uppercase tracking-wider">Geopolitical & Macro Scenario Simulator</h2>
          <p className="text-xs text-zinc-500 mt-1">Stress test global shifts and traverse causal graph propagation chains across your portfolio.</p>
        </div>
        <span className="text-[10px] border border-black bg-black text-white px-2.5 py-1 font-mono uppercase tracking-wider">
          Titan Engine Active
        </span>
      </div>

      {/* Simulator Search & Predefined Scenarios Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Side: Input Form & Predefined Lists */}
        <div className="space-y-6 lg:col-span-1">
          <div className="glass-panel p-6 border-zinc-200 bg-white rounded-none">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 mb-4">Simulate Custom Shift</h3>
            <form onSubmit={handleCustomSubmit} className="space-y-3">
              <div className="relative">
                <input
                  type="text"
                  placeholder="e.g. US raises tariffs on Chinese steel..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full bg-zinc-50 border border-zinc-300 rounded-none px-4 py-2.5 text-sm font-mono text-zinc-950 focus:outline-none focus:border-black placeholder-zinc-400"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="w-full bg-black text-white hover:bg-zinc-800 disabled:bg-zinc-200 disabled:text-zinc-400 rounded-none py-2.5 font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 border border-black transition-all duration-200"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Propagating Shock...
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-current" />
                    Run Stress Test
                  </>
                )}
              </button>
            </form>
          </div>

          <div className="glass-panel p-6 border-zinc-200 bg-white rounded-none">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-500 mb-4">Macro Stress Templates</h3>
            <div className="space-y-3">
              {PREDEFINED_SCENARIOS.map((scen: any, idx: number) => (
                <button
                  key={idx}
                  onClick={() => {
                    setQuery(scen.query);
                    runSimulation(scen.query);
                  }}
                  disabled={loading}
                  className="w-full text-left p-3 border border-zinc-200 hover:border-black bg-zinc-50 hover:bg-zinc-100/50 rounded-none transition-all duration-300 flex flex-col justify-between"
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[10px] font-bold text-zinc-950 uppercase font-mono">{scen.title}</span>
                    <span className="text-[8px] bg-zinc-200 text-zinc-700 px-1.5 py-0.5 rounded-none font-bold uppercase tracking-wider">
                      {scen.category}
                    </span>
                  </div>
                  <p className="text-[10px] text-zinc-500 leading-normal">{scen.desc}</p>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Side: Simulation Summary Output */}
        <div className="lg:col-span-2">
          {loading ? (
            <div className="h-full min-h-[350px] border border-dashed border-zinc-300 flex flex-col items-center justify-center text-zinc-400 gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-black" />
              <div className="text-center">
                <p className="text-xs font-mono font-bold text-zinc-700 uppercase">Traversing Economic Graph Paths...</p>
                <p className="text-[10px] text-zinc-400 mt-1">Running BFS propagation vectors and updating risk scores</p>
              </div>
            </div>
          ) : event ? (
            <div className="glass-panel p-6 border-zinc-200 bg-white rounded-none space-y-6">
              {/* Event Metadata Header */}
              <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-4 border-b border-zinc-200 pb-5">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-bold tracking-wider bg-zinc-100 text-zinc-800 border border-zinc-300 px-2 py-0.5 rounded-none uppercase font-mono">
                      {event.category || "General"}
                    </span>
                    <span className={`text-[9px] font-bold tracking-wider px-2 py-0.5 border rounded-none uppercase font-mono ${
                      event.sentiment === "positive" 
                        ? "bg-emerald-50 border-emerald-200 text-emerald-700" 
                        : event.sentiment === "negative"
                          ? "bg-rose-50 border-rose-200 text-rose-700"
                          : "bg-zinc-100 border-zinc-300 text-zinc-700"
                    }`}>
                      {event.sentiment} Sentiment
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-zinc-950 font-mono">{event.title}</h3>
                </div>
                <div className="flex gap-6">
                  <div className="text-left md:text-right">
                    <span className="text-[9px] text-zinc-400 uppercase font-mono block">Severity</span>
                    <span className="text-xl font-bold font-mono text-zinc-950">{(event.severity * 10).toFixed(1)}/10</span>
                  </div>
                  <div className="text-left md:text-right">
                    <span className="text-[9px] text-zinc-400 uppercase font-mono block">Confidence</span>
                    <span className="text-xl font-bold font-mono text-zinc-950">{Math.round(event.confidence * 100)}%</span>
                  </div>
                </div>
              </div>

              {/* Event Summary */}
              <div className="bg-zinc-50 border border-zinc-200 p-4 rounded-none">
                <p className="text-xs text-zinc-600 leading-relaxed font-mono">
                  {event.summary || "No summary details available for this simulated trigger event."}
                </p>
              </div>

              {/* Dynamic Impact Traversal Chains & Portfolio Stress Row */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                {/* Traversal List */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 border-b border-zinc-100 pb-2">
                    <Layers className="w-4 h-4 text-black" />
                    <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-800">Causal Impact Chains</h4>
                  </div>
                  
                  <div className="space-y-2.5 max-h-[220px] overflow-y-auto pr-2">
                    {impacts.length === 0 ? (
                      <p className="text-[10px] text-zinc-450 italic">No direct stock connections found for this event in knowledge graph.</p>
                    ) : (
                      impacts.map((imp: any, idx: number) => {
                        const isSelected = selectedImpact?.ticker === imp.ticker;
                        return (
                          <div
                            key={idx}
                            onClick={() => setSelectedImpact(imp)}
                            className={`p-2.5 border rounded-none cursor-pointer transition-all duration-200 ${
                              isSelected 
                                ? "bg-black border-black text-white" 
                                : "bg-zinc-50 border-zinc-200 hover:border-zinc-400 text-zinc-900"
                            }`}
                          >
                            <div className="flex justify-between items-center mb-1">
                              <span className="text-[10px] font-bold font-mono">{imp.ticker.replace(".NS", "")}</span>
                              <span className={`text-[9px] font-bold font-mono ${
                                isSelected 
                                  ? "text-white" 
                                  : imp.direction > 0 ? "text-emerald-600" : "text-rose-600"
                              }`}>
                                {imp.direction > 0 ? "+" : "-"}{Math.round(imp.magnitude * 100)}%
                              </span>
                            </div>
                            <p className={`text-[9px] truncate ${isSelected ? "text-zinc-300" : "text-zinc-550"}`}>
                              {imp.company_name}
                            </p>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* Pathway Breakdown */}
                <div className="space-y-4">
                  <div className="flex items-center gap-2 border-b border-zinc-100 pb-2">
                    <Activity className="w-4 h-4 text-black" />
                    <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-800">Shock Propagation Detail</h4>
                  </div>

                  {selectedImpact ? (
                    <div className="p-4 border border-zinc-200 bg-white rounded-none space-y-3 h-[220px] overflow-y-auto">
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs font-bold text-zinc-950 font-mono">{selectedImpact.ticker.replace(".NS", "")}</span>
                        <span className="text-[10px] bg-zinc-100 text-zinc-700 px-1.5 py-0.5 rounded-none font-mono">
                          Confidence: {Math.round(selectedImpact.confidence * 100)}%
                        </span>
                      </div>

                      <div className="space-y-2 font-mono">
                        <span className="text-[8px] text-zinc-400 uppercase tracking-widest block mb-1.5">Propagation Path</span>
                        {selectedImpact.reasoning_path?.map((step: string, sIdx: number) => {
                          const parts = step.split(" --[");
                          const nodeName = parts[0];
                          const relation = parts[1] ? parts[1].split("]-->")[0] : null;
                          const nextNode = parts[1] ? parts[1].split("]-->")[1] : null;

                          return (
                            <div key={sIdx} className="text-[10px] space-y-1">
                              <div className="flex items-center gap-1.5 text-zinc-950 font-bold">
                                <span className="w-1.5 h-1.5 bg-black rounded-none"></span>
                                {nodeName}
                              </div>
                              {relation && (
                                <div className="pl-3 py-0.5 border-l border-zinc-300 text-[9px] text-zinc-550 flex items-center gap-1">
                                  <ArrowRight className="w-2.5 h-2.5 text-zinc-400" />
                                  <span>{relation.replace(" (w=", " [weight=")}</span>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="h-[220px] border border-dashed border-zinc-200 flex items-center justify-center text-zinc-400 text-[10px] font-mono">
                      Select a stock on the left to trace causal path
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[350px] border border-dashed border-zinc-200 flex flex-col items-center justify-center text-zinc-400 gap-4">
              <div className="w-12 h-12 border border-zinc-300 flex items-center justify-center">
                <ShieldAlert className="w-6 h-6 text-zinc-400" />
              </div>
              <div className="text-center">
                <p className="text-xs font-mono font-bold text-zinc-650 uppercase">Simulator Standby</p>
                <p className="text-[10px] text-zinc-400 mt-1">Select a macro scenario or enter a custom event on the left</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Portfolio Stress Testing Table */}
      {event && stressResults.length > 0 && (
        <div className="glass-panel p-6 border-zinc-200 bg-white rounded-none space-y-5">
          <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 border-b border-zinc-100 pb-4">
            <div className="flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-black" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-900">Portfolio Stress Test Matrix</h3>
            </div>
            
            {/* Total impact metrics */}
            <div className="flex gap-6 font-mono">
              <div className="text-left">
                <span className="text-[9px] text-zinc-400 uppercase">Portfolio Base</span>
                <span className="text-sm font-bold text-zinc-950 block">₹{totalPortfolioValue.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
              </div>
              <div className="text-left">
                <span className="text-[9px] text-zinc-400 uppercase">Simulated Stress Result</span>
                <span className="text-sm font-bold text-zinc-950 block">₹{totalSimulatedValue.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
              </div>
              <div className="text-left">
                <span className="text-[9px] text-zinc-400 uppercase">Net Value Impact</span>
                <span className={`text-sm font-bold block ${totalDeltaValue >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                  ₹{totalDeltaValue.toLocaleString("en-IN", { maximumFractionDigits: 2 })} ({totalDeltaValue >= 0 ? "+" : ""}{portfolioDeltaPct.toFixed(2)}%)
                </span>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs font-mono">
              <thead>
                <tr className="border-b border-zinc-300 text-zinc-400 uppercase text-[9px] tracking-wider">
                  <th className="pb-3 font-semibold">Ticker</th>
                  <th className="pb-3 font-semibold text-right">Holdings</th>
                  <th className="pb-3 font-semibold text-right">Base Price</th>
                  <th className="pb-3 font-semibold text-right">Base Value</th>
                  <th className="pb-3 font-semibold text-right">Expected Move</th>
                  <th className="pb-3 font-semibold text-right">Simulated Price</th>
                  <th className="pb-3 font-semibold text-right">Simulated Value</th>
                  <th className="pb-3 font-semibold text-right">Net Delta</th>
                  <th className="pb-3 font-semibold text-right">Risk Tag</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200">
                {stressResults.map((row: any, idx: number) => {
                  const isNeg = row.deltaValue < 0;
                  const isZero = row.deltaValue === 0;
                  
                  let badgeClass = "bg-zinc-100 text-zinc-700 border-zinc-300";
                  if (row.impactLevel === "Strong Positive") badgeClass = "bg-emerald-100 text-emerald-800 border-emerald-300";
                  else if (row.impactLevel === "Positive") badgeClass = "bg-emerald-50 text-emerald-700 border-emerald-200";
                  else if (row.impactLevel === "Severe Risk") badgeClass = "bg-rose-100 text-rose-800 border-rose-300";
                  else if (row.impactLevel === "Risk") badgeClass = "bg-rose-50 text-rose-700 border-rose-200";

                  return (
                    <tr key={idx} className="hover:bg-zinc-50/50">
                      <td className="py-3 font-bold text-zinc-950">
                        {row.ticker.replace(".NS", "")}
                        <span className="text-[10px] text-zinc-400 font-normal block">{row.companyName}</span>
                      </td>
                      <td className="py-3 text-right text-zinc-700">{row.quantity.toLocaleString()}</td>
                      <td className="py-3 text-right text-zinc-700">₹{row.currentPrice.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</td>
                      <td className="py-3 text-right text-zinc-700">₹{row.currentVal.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</td>
                      <td className={`py-3 text-right font-bold ${isZero ? "text-zinc-400" : isNeg ? "text-rose-600" : "text-emerald-600"}`}>
                        {isZero ? "0.00%" : `${isNeg ? "" : "+"}${row.expectedMovePct.toFixed(2)}%`}
                      </td>
                      <td className="py-3 text-right text-zinc-700">₹{row.simulatedPrice.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</td>
                      <td className="py-3 text-right text-zinc-700 font-bold">₹{row.simulatedVal.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</td>
                      <td className={`py-3 text-right font-bold ${isZero ? "text-zinc-400" : isNeg ? "text-rose-700" : "text-emerald-700"}`}>
                        {isZero ? "—" : `${isNeg ? "" : "+"}${row.deltaValue.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`}
                      </td>
                      <td className="py-3 text-right">
                        <span className={`border px-2 py-0.5 rounded-none font-bold text-[9px] uppercase tracking-wider ${badgeClass}`}>
                          {row.impactLevel}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
