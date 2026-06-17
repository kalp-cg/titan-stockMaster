"use client";

import React from "react";
import {
  TrendingUp,
  LayoutDashboard,
  Briefcase,
  Globe,
  Users,
  Compass,
  FileText,
  ShieldAlert,
  Coins,
} from "lucide-react";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  connected: boolean;
}

export default function Sidebar({ activeTab, setActiveTab, connected }: SidebarProps) {
  const menuItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "portfolio", label: "Portfolio Vault", icon: Briefcase },
    { id: "events", label: "Global Events", icon: Globe },
    { id: "simulator", label: "Scenario Simulator", icon: ShieldAlert },
    { id: "smart_money", label: "Smart Money", icon: Coins },
    { id: "stakeholders", label: "Stakeholders", icon: Users },
    { id: "opportunities", label: "Opportunities", icon: Compass },
    { id: "ipos", label: "IPO Tracker", icon: FileText },
  ];

  return (
    <aside className="w-64 h-screen glass-panel rounded-none border-y-0 border-l-0 flex flex-col justify-between p-6">
      <div>
        {/* Brand logo */}
        <div className="flex items-center gap-3 mb-10 px-2">
          <TrendingUp className="w-8 h-8 text-black" />
          <div>
            <h1 className="font-bold text-lg text-black leading-none">HELIX DECIDEX</h1>
            <span className="text-[10px] text-zinc-500 tracking-wider">MARKET INTELLIGENCE</span>
          </div>
        </div>

        {/* Navigation menu */}
        <nav className="space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-4 px-4 py-3 rounded-none transition-all duration-300 ${
                  isActive
                    ? "bg-black text-white border border-black"
                    : "text-zinc-600 hover:text-black hover:bg-zinc-100 border border-transparent"
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive ? "text-white" : "text-zinc-500"}`} />
                <span className="text-sm font-medium">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Network connection status */}
      <div className="px-2 py-3 border border-zinc-200 rounded-none bg-zinc-50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className={`w-2.5 h-2.5 rounded-none ${
              connected ? "bg-emerald-600" : "bg-rose-600 animate-pulse"
            }`}
          />
          <span className="text-xs text-zinc-600">
            {connected ? "Feed Connected" : "Connecting..."}
          </span>
        </div>
        <span className="text-[10px] bg-zinc-200 text-zinc-800 px-2 py-0.5 rounded-none font-mono">
          V0.1.0
        </span>
      </div>
    </aside>
  );
}
