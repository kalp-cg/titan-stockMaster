/**
 * API client library for Project Titan.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (typeof window !== "undefined") {
    const token = localStorage.getItem("titan_auth_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      ...headers,
      ...options.headers,
    },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP error ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    fetchAPI("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  signup: (email: string, password: string) =>
    fetchAPI("/api/v1/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  getMe: () => fetchAPI("/api/v1/auth/me"),

  // Events
  getEvents: (category?: string) =>
    fetchAPI(`/api/v1/events${category ? `?category=${category}` : ""}`),
  getEvent: (id: string) => fetchAPI(`/api/v1/events/${id}`),
  getEventImpact: (id: string) => fetchAPI(`/api/v1/events/${id}/impact`),

  // Market
  getPrices: (tickers: string[]) =>
    fetchAPI(`/api/v1/market/prices?tickers=${tickers.join(",")}`),
  getIndices: () => fetchAPI("/api/v1/market/indices"),
  getHistory: (ticker: string, period = "1y") =>
    fetchAPI(`/api/v1/market/history/${ticker}?period=${period}`),
  searchTickers: (q: string) =>
    fetchAPI(`/api/v1/market/search?q=${encodeURIComponent(q)}`),

  // Portfolio
  getPortfolio: () => fetchAPI("/api/v1/portfolio"),
  addHolding: (ticker: string, qty: number, price: number, thesis: string = "") =>
    fetchAPI("/api/v1/portfolio/holdings", {
      method: "POST",
      body: JSON.stringify({ ticker, quantity: qty, avg_buy_price: price, thesis }),
    }),
  removeHolding: (ticker: string) =>
    fetchAPI(`/api/v1/portfolio/holdings/${ticker}`, {
      method: "DELETE",
    }),
  getExposure: () => fetchAPI("/api/v1/portfolio/exposure"),

  // Predictions
  getPrediction: (ticker: string) => fetchAPI(`/api/v1/predictions/${ticker}`),
  getPortfolioPredictions: () => fetchAPI("/api/v1/predictions/portfolio"),

  // Opportunities
  getOpportunities: () => fetchAPI("/api/v1/opportunities"),

  // IPOs
  getIPOs: () => fetchAPI("/api/v1/ipos"),

  // Risk Alerts
  getRiskAlerts: () => fetchAPI("/api/v1/risk/alerts"),

  // Stakeholder Intelligence
  getShareholding: (ticker: string) =>
    fetchAPI(`/api/v1/stakeholders/${ticker}/shareholding`),
  getShareholdingHistory: (ticker: string, quarters = 8) =>
    fetchAPI(
      `/api/v1/stakeholders/${ticker}/shareholding/history?quarters=${quarters}`
    ),
  getBulkDeals: (ticker?: string) =>
    fetchAPI(`/api/v1/stakeholders/bulk-deals${ticker ? `?ticker=${ticker}` : ""}`),
  getInsiderTrades: (ticker?: string) =>
    fetchAPI(
      `/api/v1/stakeholders/insider-trades${ticker ? `?ticker=${ticker}` : ""}`
    ),
  getInstitutionalFlows: () => fetchAPI("/api/v1/stakeholders/institutional-flows"),
  getSmartMoney: (ticker: string) =>
    fetchAPI(`/api/v1/stakeholders/${ticker}/smart-money`),

  // Explain
  explainPrediction: (predId: string) => fetchAPI(`/api/v1/explain/${predId}`),

  // Search
  search: (q: string) => fetchAPI(`/api/v1/search?q=${encodeURIComponent(q)}`),

  // Alpha Leads
  getLeads: () => fetchAPI("/api/v1/leads"),

  // Smart Money (New)
  getSmartMoneyPortfolio: () => fetchAPI("/api/v1/smart-money/portfolio"),
  getSmartMoneyTicker: (ticker: string) => fetchAPI(`/api/v1/smart-money/ticker/${ticker}`),
  refreshSmartMoney: () => fetchAPI("/api/v1/smart-money/refresh", { method: "POST" }),

  // Historical Analogy (New)
  getHistoricalAnalogy: (eventId: string) => fetchAPI(`/api/v1/events/${eventId}/historical-analogy`),

  // Causal Chain Economic Propagation (New)
  getEventCausalChain: (eventId: string) => fetchAPI(`/api/v1/events/${eventId}/causal-chain`),

  // Movement Attribution (New)
  getHoldingAttribution: (ticker: string, movePct = 0.0, moveDate?: string, sector?: string, volumeRatio = 1.0) => {
    let url = `/api/v1/portfolio/holdings/${ticker}/attribution?move_pct=${movePct}&volume_ratio=${volumeRatio}`;
    if (moveDate) url += `&move_date=${encodeURIComponent(moveDate)}`;
    if (sector) url += `&sector=${encodeURIComponent(sector)}`;
    return fetchAPI(url);
  },
};

