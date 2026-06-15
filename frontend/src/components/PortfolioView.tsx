"use client";

import React, { useEffect, useState, useRef } from "react";
import { Plus, Trash2, ArrowUpRight, ArrowDownRight, Briefcase, PieChart, Search, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

export default function PortfolioView({ prices = {} }: { prices?: Record<string, any> }) {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [exposures, setExposures] = useState<any[]>([]);
  const [predictions, setPredictions] = useState<any>({});
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  // Movement Attribution States
  const [subTab, setSubTab] = useState<"forecast" | "attribution">("forecast");
  const [attribution, setAttribution] = useState<any>(null);
  const [attribLoading, setAttribLoading] = useState(false);
  const [attribMovePct, setAttribMovePct] = useState<number>(0.0);
  const [attribVolRatio, setAttribVolRatio] = useState<number>(1.0);

  const [prevPrices, setPrevPrices] = useState<Record<string, number>>({});
  const [flashStates, setFlashStates] = useState<Record<string, "up" | "down" | null>>({});

  useEffect(() => {
    const newFlash: Record<string, "up" | "down" | null> = {};
    let hasChanges = false;
    
    Object.keys(prices).forEach((key) => {
      const currentPrice = prices[key]?.price;
      const prevPrice = prevPrices[key];
      if (prevPrice !== undefined && currentPrice !== prevPrice) {
        newFlash[key] = currentPrice > prevPrice ? "up" : "down";
        hasChanges = true;
      }
    });

    if (hasChanges) {
      setFlashStates((prev) => ({ ...prev, ...newFlash }));
      setPrevPrices(Object.keys(prices).reduce((acc, key) => {
        acc[key] = prices[key]?.price;
        return acc;
      }, {} as Record<string, number>));

      const timer = setTimeout(() => {
        setFlashStates({});
      }, 1000);
      return () => clearTimeout(timer);
    } else {
      if (Object.keys(prevPrices).length === 0 && Object.keys(prices).length > 0) {
        setPrevPrices(Object.keys(prices).reduce((acc, key) => {
          acc[key] = prices[key]?.price;
          return acc;
        }, {} as Record<string, number>));
      }
    }
  }, [prices, prevPrices]);

  const holdings = portfolio?.holdings?.map((h: any) => {
    const liveData = prices[h.ticker];
    const currentPrice = liveData ? (liveData.price ?? h.current_price) : h.current_price;
    const pnl = (currentPrice - h.avg_buy_price) * h.quantity;
    const pnlPct = h.avg_buy_price !== 0 ? ((currentPrice - h.avg_buy_price) / h.avg_buy_price) * 100 : 0;
    return {
      ...h,
      current_price: currentPrice,
      pnl,
      pnl_pct: pnlPct,
    };
  }) || [];

  // Form states
  const [ticker, setTicker] = useState("");
  const [qty, setQty] = useState("");
  const [price, setPrice] = useState("");
  const [thesis, setThesis] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  // Autocomplete states
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
    if (ticker === lastSelected) {
      setSuggestions([]);
      return;
    }
    if (ticker.trim().length < 2) {
      setSuggestions([]);
      return;
    }

    const delayDebounceFn = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await api.searchTickers(ticker);
        setSuggestions(results || []);
      } catch (err) {
        console.error("Error fetching autocomplete suggestions:", err);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [ticker, lastSelected]);

  const handleSelectSuggestion = async (item: any) => {
    setTicker(item.symbol);
    setLastSelected(item.symbol);
    setSuggestions([]);
    setShowDropdown(false);
    
    // Auto-populate price
    try {
      const priceRes = await api.getPrices([item.symbol]);
      if (priceRes && priceRes[item.symbol]) {
        const livePrice = priceRes[item.symbol].price;
        if (livePrice && livePrice > 0) {
          setPrice(livePrice.toString());
        } else if (priceRes[item.symbol].close && priceRes[item.symbol].close > 0) {
          setPrice(priceRes[item.symbol].close.toString());
        } else {
          setPrice("100.00");
        }
      }
    } catch (e) {
      console.error("Failed to fetch price for selected ticker:", e);
    }
  };

  async function loadPortfolioData() {
    try {
      const port = await api.getPortfolio();
      setPortfolio(port);
      const expo = await api.getExposure();
      setExposures(expo);
      const preds = await api.getPortfolioPredictions();
      setPredictions(preds);
    } catch (e) {
      console.error("Failed to load portfolio details", e);
    }
  }

  useEffect(() => {
    loadPortfolioData();
  }, []);

  // Sync selected ticker live daily change to attribution state
  useEffect(() => {
    if (selectedTicker) {
      const dailyChange = prices[selectedTicker]?.change_pct ?? 0.0;
      setAttribMovePct(dailyChange);
      setAttribVolRatio(1.0);
      setAttribution(null);
    }
  }, [selectedTicker, prices]);

  // Fetch attribution when tab changes or sandbox inputs change
  useEffect(() => {
    const selectedHolding = holdings.find((h: any) => h.ticker === selectedTicker);
    if (selectedTicker && subTab === "attribution") {
      async function fetchAttribution() {
        setAttribLoading(true);
        try {
          const res = await api.getHoldingAttribution(
            selectedTicker!,
            attribMovePct,
            undefined,
            selectedHolding?.sector ?? undefined,
            attribVolRatio
          );
          setAttribution(res);
        } catch (e) {
          console.error("Failed to fetch attribution", e);
        } finally {
          setAttribLoading(false);
        }
      }
      fetchAttribution();
    }
  }, [selectedTicker, subTab, attribMovePct, attribVolRatio]);

  const handleAddStock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker || !qty || !price) return;
    setLoading(true);
    setErrorMessage("");

    try {
      // yfinance ticker format validation for India
      let resolvedTicker = ticker.trim().toUpperCase();
      if (!resolvedTicker.includes(".") && !resolvedTicker.startsWith("^")) {
        resolvedTicker += ".NS"; // default to NSE
      }
      await api.addHolding(resolvedTicker, parseFloat(qty), parseFloat(price), thesis.trim());
      
      // Reset form
      setTicker("");
      setQty("");
      setPrice("");
      setThesis("");
      
      // Reload
      await loadPortfolioData();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to add position");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteStock = async (t: string) => {
    if (!confirm(`Are you sure you want to remove ${t} position?`)) return;
    try {
      await api.removeHolding(t);
      if (selectedTicker === t) setSelectedTicker(null);
      await loadPortfolioData();
    } catch (e) {
      console.error("Failed to delete position", e);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in text-zinc-900 bg-white">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Holdings and Forms */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Add holding form */}
          <div className="glass-panel p-6 rounded-none border-zinc-200 bg-white">
            <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider mb-4 border-b border-zinc-200 pb-2">
              Add Position to Vault
            </h3>
            <form onSubmit={handleAddStock} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="relative" ref={dropdownRef}>
                  <label className="text-[10px] text-zinc-500 font-bold block mb-1">TICKER (e.g. RELIANCE, TCS)</label>
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="RELIANCE"
                      value={ticker}
                      onChange={(e) => {
                        setTicker(e.target.value);
                        if (lastSelected) setLastSelected(null);
                        setShowDropdown(true);
                      }}
                      onFocus={() => setShowDropdown(true)}
                      className="w-full bg-zinc-50 border border-zinc-200 rounded-none py-2 pl-9 pr-3 text-sm text-zinc-900 focus:outline-none focus:border-black transition-all duration-300"
                      required
                      autoComplete="off"
                    />
                    <Search className="absolute left-3 top-2.5 w-4 h-4 text-zinc-400" />
                  </div>

                  {/* Autocomplete Suggestions Dropdown */}
                  {showDropdown && (ticker.trim().length >= 2 || isSearching) && (
                    <div className="absolute top-full left-0 w-full mt-2 z-50 rounded-none border border-zinc-200 bg-white shadow-lg overflow-hidden max-h-60 overflow-y-auto">
                      {isSearching ? (
                        <div className="p-4 flex items-center justify-center gap-2 text-xs text-zinc-500">
                          <Loader2 className="w-4 h-4 animate-spin text-black" />
                          <span>Searching markets...</span>
                        </div>
                      ) : suggestions.length > 0 ? (
                        <ul className="divide-y divide-zinc-100">
                          {suggestions.map((item) => (
                            <li key={item.symbol}>
                              <button
                                type="button"
                                onClick={() => handleSelectSuggestion(item)}
                                className="w-full text-left px-4 py-3 hover:bg-zinc-50 active:bg-zinc-100 transition-all duration-150 flex items-center justify-between group"
                              >
                                <div className="flex flex-col min-w-0 pr-2">
                                  <span className="font-bold text-sm text-zinc-950 group-hover:underline transition-colors duration-155 truncate">
                                    {item.symbol}
                                  </span>
                                  <span className="text-[11px] text-zinc-500 truncate">
                                    {item.name}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                  <span className="text-[9px] font-bold px-2 py-0.5 rounded-none bg-zinc-100 text-zinc-650 border border-zinc-200 uppercase">
                                    {item.exchange}
                                  </span>
                                  <span className="text-[9px] font-bold px-2 py-0.5 rounded-none bg-zinc-200 text-zinc-900 border border-zinc-300">
                                    {item.type}
                                  </span>
                                </div>
                              </button>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <div className="p-4 text-center text-xs text-zinc-400">
                          No tickers found matching "{ticker}"
                        </div>
                      )}
                    </div>
                  )}
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 font-bold block mb-1">QUANTITY</label>
                  <input
                    type="number"
                    step="any"
                    placeholder="10"
                    value={qty}
                    onChange={(e) => setQty(e.target.value)}
                    className="w-full bg-zinc-50 border border-zinc-200 rounded-none py-2 px-3 text-sm text-zinc-900 focus:outline-none focus:border-black"
                    required
                  />
                </div>
                <div>
                  <label className="text-[10px] text-zinc-500 font-bold block mb-1">AVG BUY PRICE (INR)</label>
                  <input
                    type="number"
                    step="any"
                    placeholder="2450"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    className="w-full bg-zinc-50 border border-zinc-200 rounded-none py-2 px-3 text-sm text-zinc-900 focus:outline-none focus:border-black"
                    required
                  />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-zinc-500 font-bold block mb-1">
                  INVESTMENT THESIS <span className="text-zinc-400 font-normal normal-case">(your reason for holding — used by Thesis Drift Radar)</span>
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. Expecting coal demand to rise with infrastructure boom, strong revenue growth expected over next 2 years..."
                  value={thesis}
                  onChange={(e) => setThesis(e.target.value)}
                  className="w-full bg-zinc-50 border border-zinc-200 rounded-none py-2 px-3 text-sm text-zinc-900 focus:outline-none focus:border-black resize-none"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-black hover:bg-zinc-800 text-white font-bold py-2 px-4 rounded-none flex items-center justify-center gap-2 transition-all duration-300 disabled:opacity-50"
              >
                <Plus className="w-4 h-4" />
                <span>{loading ? "Adding..." : "Add Position"}</span>
              </button>
            </form>
            {errorMessage && <p className="text-xs text-rose-600 mt-2">{errorMessage}</p>}
          </div>

          {/* Holdings table */}
          <div className="glass-panel p-6 rounded-none border-zinc-200 bg-white">
            <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider mb-4 border-b border-zinc-200 pb-2">
              Asset Allocation & Vault Positions
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-zinc-200 text-[10px] font-bold text-zinc-500 tracking-wider">
                    <th className="pb-3 text-left">TICKER</th>
                    <th className="pb-3 text-right">QUANTITY</th>
                    <th className="pb-3 text-right">AVG PRICE</th>
                    <th className="pb-3 text-right">CURRENT PRICE</th>
                    <th className="pb-3 text-right">P&L</th>
                    <th className="pb-3 text-right">THESIS HEALTH</th>
                    <th className="pb-3 text-right">ACTIONS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                  {holdings.map((h: any) => {
                    const pnl = h.pnl ?? 0;
                    const pnlPct = h.pnl_pct ?? 0;
                    const isProfit = pnl >= 0;
                    const flash = flashStates[h.ticker];
                    const flashClass = flash === "up"
                      ? "bg-emerald-50 text-emerald-700 transition-all duration-300"
                      : flash === "down"
                      ? "bg-rose-50 text-rose-700 transition-all duration-300"
                      : "";

                    return (
                      <tr
                        key={h.ticker}
                        onClick={() => setSelectedTicker(h.ticker)}
                        className={`text-sm cursor-pointer hover:bg-zinc-50 transition-colors duration-200 ${selectedTicker === h.ticker ? "bg-zinc-100" : ""}`}
                      >
                        <td className="py-4">
                          <div>
                            <span className="font-bold text-zinc-950 block">{h.ticker}</span>
                            <span className="text-[10px] text-zinc-500">{h.company_name}</span>
                          </div>
                        </td>
                        <td className="py-4 text-right font-mono text-zinc-800">{h.quantity ?? 0}</td>
                        <td className="py-4 text-right font-mono text-zinc-800">
                          ₹{(h.avg_buy_price ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                        </td>
                        <td className={`py-4 text-right font-mono text-zinc-800 transition-all duration-300 ${flashClass}`}>
                          ₹{(h.current_price ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                        </td>
                        <td className={`py-4 text-right font-mono font-bold ${isProfit ? "text-emerald-700" : "text-rose-700"}`}>
                          <div className="flex flex-col items-end">
                            <span>₹{pnl.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
                            <span className="text-[10px] font-bold">
                              {isProfit ? "+" : ""}{pnlPct.toFixed(2)}%
                            </span>
                          </div>
                        </td>
                        <td className="py-4 text-right">
                          {h.thesis ? (
                            <div className="flex flex-col items-end gap-1">
                              <span className={`text-xs font-bold ${
                                (h.thesis_health ?? 100) >= 75 ? "text-zinc-800" :
                                (h.thesis_health ?? 100) >= 45 ? "text-zinc-600" :
                                "text-zinc-400"
                              }`}>{(h.thesis_health ?? 100).toFixed(0)}%</span>
                              <div className="w-16 bg-zinc-100 h-1 border border-zinc-200">
                                <div
                                  style={{ width: `${h.thesis_health ?? 100}%` }}
                                  className={`h-full ${
                                    (h.thesis_health ?? 100) >= 75 ? "bg-black" :
                                    (h.thesis_health ?? 100) >= 45 ? "bg-zinc-500" :
                                    "bg-zinc-300"
                                  }`}
                                />
                              </div>
                              <span className={`text-[9px] font-bold uppercase tracking-wide ${
                                (h.thesis_health ?? 100) >= 75 ? "text-zinc-800" :
                                (h.thesis_health ?? 100) >= 45 ? "text-zinc-500" :
                                "text-zinc-400"
                              }`}>
                                {(h.thesis_health ?? 100) >= 75 ? "ON TRACK" :
                                 (h.thesis_health ?? 100) >= 45 ? "DRIFTING" : "AT RISK"}
                              </span>
                            </div>
                          ) : (
                            <span className="text-[10px] text-zinc-300 italic">No thesis</span>
                          )}
                        </td>
                        <td className="py-4 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteStock(h.ticker);
                            }}
                            className="p-1.5 rounded-none border border-zinc-200 hover:border-rose-600 text-zinc-400 hover:text-rose-600 transition-colors duration-200"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                  {!holdings.length && (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-zinc-400">
                        No positions added. Get started by typing a stock above!
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Sidebar Info Panels */}
        <div className="space-y-8">
          {/* Sector Exposures */}
          <div className="glass-panel p-6 flex flex-col justify-between rounded-none border-zinc-200 bg-white">
            <div className="flex items-center gap-2 mb-6">
              <PieChart className="w-4 h-4 text-black" />
              <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider">
                Sector Diversification
              </h3>
            </div>
            
            <div className="space-y-4 flex-grow">
              {exposures.map((expo) => (
                <div key={expo.sector} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-semibold text-zinc-850">{expo.sector}</span>
                    <span className="font-mono text-zinc-500">{expo.weight_pct}%</span>
                  </div>
                  <div className="w-full bg-zinc-100 h-1.5 rounded-none overflow-hidden border border-zinc-200">
                    <div
                      style={{ width: `${expo.weight_pct}%` }}
                      className="bg-black h-full rounded-none"
                    />
                  </div>
                </div>
              ))}
              {!exposures.length && (
                <p className="text-xs text-zinc-400 text-center py-8">
                  No allocations found. Add stocks to view exposures.
                </p>
              )}
            </div>
          </div>

          {/* Forecasting Panel for selected stock */}
          {selectedTicker && (() => {
            const selectedHolding = holdings.find((h: any) => h.ticker === selectedTicker);
            return (
              <div className="glass-panel p-6 border-zinc-300 rounded-none bg-white">
                <h3 className="text-sm font-bold text-zinc-950 uppercase tracking-wider mb-4 flex justify-between items-center border-b border-zinc-200 pb-2">
                  <span>{selectedTicker} Intelligence</span>
                  <span className="text-[10px] bg-zinc-100 text-zinc-650 px-1.5 py-0.5 rounded-none font-mono">INSIGHTS</span>
                </h3>

                {/* Sub Tab selection */}
                <div className="flex border-b border-zinc-200 mb-6 text-xs font-bold uppercase tracking-wider">
                  <button
                    onClick={() => setSubTab("forecast")}
                    className={`pb-2 pr-4 transition-colors ${
                      subTab === "forecast" ? "border-b-2 border-black text-black" : "text-zinc-400 hover:text-zinc-600"
                    }`}
                  >
                    Forecasting
                  </button>
                  <button
                    onClick={() => setSubTab("attribution")}
                    className={`pb-2 px-4 transition-colors ${
                      subTab === "attribution" ? "border-b-2 border-black text-black" : "text-zinc-400 hover:text-zinc-600"
                    }`}
                  >
                    Move Attribution
                  </button>
                </div>
                
                {subTab === "forecast" ? (
                  predictions[selectedTicker] ? (
                    <div className="space-y-6">
                      {/* Expected move */}
                      <div className="flex justify-between items-center bg-zinc-50 p-4 border border-zinc-200 rounded-none">
                        <span className="text-xs text-zinc-500 font-bold uppercase">Expected Move</span>
                        <span className={`text-lg font-mono font-bold ${(predictions[selectedTicker].expected_move ?? 0) >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                          {(predictions[selectedTicker].expected_move ?? 0) >= 0 ? "+" : ""}{predictions[selectedTicker].expected_move ?? 0}%
                        </span>
                      </div>

                      {/* Distribution probabilities */}
                      <div className="space-y-3">
                        <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Probability Distribution</h4>
                        <div className="space-y-2">
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-emerald-700 font-bold">Bullish</span>
                              <span className="text-zinc-600 font-mono">{((predictions[selectedTicker].bullish ?? 0) * 100).toFixed(0)}%</span>
                            </div>
                            <div className="w-full bg-zinc-100 h-1.5 rounded-none overflow-hidden">
                              <div style={{ width: `${(predictions[selectedTicker].bullish ?? 0) * 100}%` }} className="bg-emerald-600 h-full rounded-none" />
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-zinc-550 font-semibold">Neutral</span>
                              <span className="text-zinc-600 font-mono">{((predictions[selectedTicker].neutral ?? 0) * 100).toFixed(0)}%</span>
                            </div>
                            <div className="w-full bg-zinc-100 h-1.5 rounded-none overflow-hidden">
                              <div style={{ width: `${(predictions[selectedTicker].neutral ?? 0) * 100}%` }} className="bg-zinc-400 h-full rounded-none" />
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-rose-700 font-bold">Bearish</span>
                              <span className="text-zinc-600 font-mono">{((predictions[selectedTicker].bearish ?? 0) * 100).toFixed(0)}%</span>
                            </div>
                            <div className="w-full bg-zinc-100 h-1.5 rounded-none overflow-hidden">
                              <div style={{ width: `${(predictions[selectedTicker].bearish ?? 0) * 100}%` }} className="bg-rose-600 h-full rounded-none" />
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="flex justify-between items-center text-xs">
                        <span className="text-zinc-500 font-medium">Model Confidence</span>
                        <span className="font-mono text-zinc-950 font-bold">{((predictions[selectedTicker].confidence ?? 0) * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-zinc-400 py-6 text-center">
                      No active predictions on this holding. Events trigger predictions.
                    </p>
                  )
                ) : (
                  <div className="space-y-4">
                    {/* Sandbox Controls */}
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-[10px] text-zinc-500 font-bold block mb-1">DAILY CHANGE (%)</label>
                        <input
                          type="number"
                          step="0.1"
                          value={attribMovePct}
                          onChange={(e) => setAttribMovePct(parseFloat(e.target.value) || 0.0)}
                          className="w-full bg-zinc-50 border border-zinc-200 rounded-none py-1.5 px-2 text-xs text-zinc-900 focus:outline-none focus:border-black font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] text-zinc-500 font-bold block mb-1">VOLUME RATIO</label>
                        <input
                          type="number"
                          step="0.1"
                          min="0.1"
                          value={attribVolRatio}
                          onChange={(e) => setAttribVolRatio(parseFloat(e.target.value) || 1.0)}
                          className="w-full bg-zinc-50 border border-zinc-200 rounded-none py-1.5 px-2 text-xs text-zinc-900 focus:outline-none focus:border-black font-mono"
                        />
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[9px] text-zinc-500 font-bold uppercase font-mono">Volume Sandbox:</span>
                      <div className="flex gap-1.5">
                        {[0.5, 1.0, 2.5, 5.0].map((v) => (
                          <button
                            key={v}
                            onClick={() => setAttribVolRatio(v)}
                            className={`text-[9px] px-2 py-0.5 border font-mono transition-colors duration-150 ${
                              attribVolRatio === v
                                ? "bg-black text-white border-black"
                                : "bg-white text-zinc-650 border-zinc-200 hover:border-zinc-300"
                            }`}
                          >
                            {v}x
                          </button>
                        ))}
                      </div>
                    </div>

                    {attribLoading ? (
                      <div className="py-12 flex flex-col justify-center items-center gap-2 text-xs text-zinc-400">
                        <Loader2 className="w-5 h-5 animate-spin text-black" />
                        <span>Running Bayesian Solver...</span>
                      </div>
                    ) : attribution ? (
                      <div className="space-y-4">
                        <div className="text-xs text-zinc-800 bg-zinc-50 border border-zinc-200 p-3 rounded-none font-sans leading-relaxed">
                          {attribution.explanation_summary}
                        </div>

                        <div className="space-y-3">
                          <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Attribution Factors</h4>
                          <div className="space-y-3">
                            {attribution.factors.map((f: any, idx: number) => {
                              const pct = (f.probability * 100).toFixed(0);
                              return (
                                <div key={idx} className="space-y-1">
                                  <div className="flex justify-between text-xs font-semibold">
                                    <span className="text-zinc-900">{f.name}</span>
                                    <span className="font-mono text-zinc-500">{pct}%</span>
                                  </div>
                                  <div className="w-full bg-zinc-100 h-1.5 border border-zinc-200 rounded-none overflow-hidden">
                                    <div
                                      style={{ width: `${pct}%` }}
                                      className={`h-full ${idx === 0 ? "bg-black" : "bg-zinc-400"}`}
                                    />
                                  </div>
                                  {f.evidence && (
                                    <span className="text-[9px] text-zinc-500 block leading-normal font-mono">
                                      → {f.evidence}
                                    </span>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-zinc-400 py-6 text-center">
                        Failed to compute factor attribution.
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
