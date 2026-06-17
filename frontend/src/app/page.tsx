"use client";

import React, { useEffect, useState, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";
import DashboardView from "@/components/DashboardView";
import PortfolioView from "@/components/PortfolioView";
import EventsView from "@/components/EventsView";
import StakeholdersView from "@/components/StakeholdersView";
import OpportunitiesView from "@/components/OpportunitiesView";
import IposView from "@/components/IposView";
import SimulatorView from "@/components/SimulatorView";
import SmartMoneyView from "@/components/SmartMoneyView";
import AuthView from "@/components/AuthView";

import { api } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [events, setEvents] = useState<any[]>([]);
  const [leads, setLeads] = useState<any[]>([]);
  const [activeAlertCount, setActiveAlertCount] = useState(0);
  const [prices, setPrices] = useState<Record<string, any>>({});

  // Load token from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem("helix_decidex_auth_token");
    setToken(savedToken);
    setAuthChecked(true);
  }, []);

  // Load initial feeds when token changes
  useEffect(() => {
    if (!token) return;
    async function loadData() {
      try {
        const evs = await api.getEvents();
        setEvents(evs);
        const alerts = await api.getRiskAlerts();
        setActiveAlertCount(alerts.length);
        
        // Load initial index prices
        const indicesData = await api.getIndices();
        setPrices((prev) => ({ ...prev, ...indicesData }));

        // Load initial alpha leads
        try {
          const initialLeads = await api.getLeads();
          setLeads(initialLeads);
        } catch (e) {
          console.warn("Leads API not available yet", e);
        }
      } catch (e) {
        console.error("Failed to load initial feeds", e);
      }
    }
    loadData();
  }, [token]);

  // WebSocket message callback
  const handleWSMessage = useCallback((msg: any) => {
    if (msg.type === "new_event") {
      setEvents((prev) => [msg.data, ...prev].slice(0, 50)); // cap to 50
    } else if (msg.type === "new_prediction") {
      console.log("WS Prediction Update:", msg.data);
    } else if (msg.type === "price_update") {
      setPrices((prev) => ({ ...prev, ...msg.data }));
    } else if (msg.type === "new_lead") {
      setLeads((prev) => [msg.data, ...prev].slice(0, 20)); // cap to 20
    }
  }, []);

  const connected = useWebSocket(handleWSMessage);

  const handleSearch = async (query: string) => {
    if (!query) return;
    try {
      const results = await api.search(query);
      if (results.length > 0) {
        setEvents(results);
        setActiveTab("events");
      }
    } catch (e) {
      console.error("Search failed", e);
    }
  };

  if (!authChecked) {
    return (
      <div className="min-h-screen bg-black text-white font-mono flex items-center justify-center">
        INITIALIZING SECURITY CONTEXT...
      </div>
    );
  }

  if (!token) {
    return <AuthView onSuccess={(newToken) => setToken(newToken)} />;
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-white font-sans">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        connected={connected}
      />

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header Ticker and Search */}
        <Header
          onSearch={handleSearch}
          activeAlertCount={activeAlertCount}
          prices={prices}
          onLogout={() => {
            localStorage.removeItem("helix_decidex_auth_token");
            setToken(null);
          }}
        />

        {/* Dynamic Tab Render Area */}
        <main className="flex-1 overflow-y-auto p-8 bg-zinc-50">
          {activeTab === "dashboard" && (
            <DashboardView
              events={events}
              leads={leads}
              onSelectEvent={(ev) => {
                setActiveTab("events");
              }}
              prices={prices}
            />
          )}
          {activeTab === "portfolio" && <PortfolioView prices={prices} />}
          {activeTab === "events" && <EventsView />}
          {activeTab === "simulator" && <SimulatorView prices={prices} />}
          {activeTab === "smart_money" && <SmartMoneyView />}
          {activeTab === "stakeholders" && <StakeholdersView />}
          {activeTab === "opportunities" && <OpportunitiesView />}
          {activeTab === "ipos" && <IposView />}
        </main>
      </div>
    </div>
  );
}

