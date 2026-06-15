"use client";

import React, { useEffect, useState } from "react";
import { Search, Bell, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";

interface HeaderProps {
  onSearch: (query: string) => void;
  activeAlertCount: number;
  prices?: Record<string, any>;
  onLogout?: () => void;
}

export default function Header({ onSearch, activeAlertCount, prices = {}, onLogout }: HeaderProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [marketView, setMarketView] = useState<"india" | "global">("india");
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

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(searchQuery);
  };

  const indexList = marketView === "india" ? [
    { key: "^NSEI", label: "NIFTY 50" },
    { key: "^BSESN", label: "SENSEX" },
    { key: "^NSEBANK", label: "BANK NIFTY" },
    { key: "GC=F", label: "Gold" },
    { key: "CL=F", label: "Crude Oil" },
  ] : [
    { key: "^GSPC", label: "S&P 500" },
    { key: "^IXIC", label: "NASDAQ" },
    { key: "^FTSE", label: "FTSE 100" },
    { key: "^N225", label: "Nikkei 225" },
    { key: "^GDAXI", label: "DAX" },
    { key: "^HSI", label: "Hang Seng" },
  ];

  return (
    <header className="h-20 border-b border-zinc-200 bg-white flex items-center justify-between px-8 z-10 w-full">
      {/* Ticker marquee with toggle */}
      <div className="flex items-center gap-4 max-w-3xl overflow-hidden flex-1 mr-4">
        <div className="flex bg-zinc-100 p-0.5 rounded-none border border-zinc-200 text-[10px] font-bold text-zinc-500 shrink-0">
          <button
            onClick={() => setMarketView("india")}
            className={`px-2.5 py-1 rounded-none transition-all duration-200 ${marketView === "india" ? "bg-black text-white font-bold" : "text-zinc-650 hover:text-black"}`}
          >
            INDIA
          </button>
          <button
            onClick={() => setMarketView("global")}
            className={`px-2.5 py-1 rounded-none transition-all duration-200 ${marketView === "global" ? "bg-black text-white font-bold" : "text-zinc-655 hover:text-black"}`}
          >
            GLOBAL
          </button>
        </div>

        <div className="flex items-center gap-3 overflow-x-auto py-2 scrollbar-none">
          {indexList.map((idx) => {
            const data = prices[idx.key];
            if (!data) return null;
            const isPos = (data.change_pct ?? 0) >= 0;
            const flash = flashStates[idx.key];
            const flashClass = flash === "up"
              ? "bg-emerald-50 border-emerald-600"
              : flash === "down"
              ? "bg-rose-50 border-rose-600"
              : "bg-zinc-50 border-zinc-200";

            return (
              <div
                key={idx.key}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-none border whitespace-nowrap transition-all duration-300 ${flashClass}`}
              >
                <span className="text-xs font-semibold text-zinc-600">{idx.label}</span>
                <span className="text-sm font-mono text-zinc-900">
                  {(data.price ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                </span>
                <span
                  className={`text-[10px] font-mono ${isPos ? "text-emerald-600" : "text-rose-600"}`}
                >
                  {isPos ? "+" : ""}
                  {(data.change_pct ?? 0).toFixed(2)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Search and alerts */}
      <div className="flex items-center gap-6 shrink-0">
        <form onSubmit={handleSearchSubmit} className="relative w-64">
          <input
            type="text"
            placeholder="Search events, stocks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-zinc-50 border border-zinc-200 rounded-none py-2 pl-10 pr-4 text-sm text-zinc-900 placeholder-zinc-400 focus:outline-none focus:border-black transition-all duration-300"
          />
          <Search className="w-4 h-4 text-zinc-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
        </form>

        <div className="flex items-center gap-4">
          <div className="relative">
            <button className="p-2 rounded-none bg-zinc-50 border border-zinc-200 text-zinc-600 hover:text-black transition-all duration-200">
              <Bell className="w-5 h-5" />
            </button>
          </div>

          <div className="flex items-center gap-2 bg-rose-50 border border-rose-300 px-3 py-1.5 rounded-none">
            <ShieldAlert className="w-4 h-4 text-rose-600" />
            <span className="text-xs font-semibold text-rose-700">
              {activeAlertCount} Risk Alerts
            </span>
          </div>

          {onLogout && (
            <button
              onClick={onLogout}
              className="px-3 py-1.5 rounded-none bg-black text-white hover:bg-zinc-800 border border-black font-mono text-xs font-bold transition-all duration-200 cursor-pointer"
            >
              LOGOUT
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
