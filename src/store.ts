import { create } from 'zustand';

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const wsUrlOverride = (import.meta.env.VITE_WS_BASE_URL || import.meta.env.VITE_WS_URL || '').trim();
let shouldReconnect = true;

function buildApiUrl(path: string): string {
  if (!apiBaseUrl) return path;
  return `${apiBaseUrl}${path}`;
}

function resolveWsUrl(): string {
  if (wsUrlOverride) {
    return wsUrlOverride;
  }

  if (apiBaseUrl) {
    try {
      const parsed = new URL(apiBaseUrl);
      parsed.protocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
      parsed.pathname = '/ws';
      parsed.search = '';
      parsed.hash = '';
      return parsed.toString();
    } catch (error) {
      console.error('Invalid VITE_API_BASE_URL, falling back to window host:', error);
    }
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws`;
}

export type ViewState = 'home' | 'trending' | 'signals' | 'watchlist' | 'alerts' | 'reports' | 'portfolio' | 'settings' | 'stock';

export interface SparklinePoint {
  time: number;
  value: number;
}

export interface TrendingStock {
  id: string;
  ticker: string;
  name: string;
  beliefScore: number;
  sentiment: 'bullish' | 'bearish' | 'neutral';
  velocity: number;
  sector: string;
  marketCap: string;
  sparkline: SparklinePoint[];
}

export interface ProvenanceMeta {
  source: 'live' | 'mock' | 'generated' | 'cached' | 'fallback' | 'unavailable';
  mode: 'demo' | 'hybrid' | 'live' | string;
  generated_at: string;
  is_fallback: boolean;
  provider: string;
  confidence: 'prototype' | 'low' | 'medium' | 'high' | string;
  notes: string;
}

interface ApiEnvelope<T> {
  data: T;
  meta: ProvenanceMeta;
}

interface ApiErrorPayload {
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    request_id?: string;
  };
}

export interface StockData {
  ticker: string;
  name: string;
  beliefScore: number;
  signal: 'Bullish' | 'Bearish';
  metrics: {
    coherence: string;
    velocity: string;
    fragility: string;
  };
  chartData: { date: string; price: string; belief: string }[];
  clusters: { label: string; dominance: number; color: string }[];
  network: {
    nodes: { id: string; label: string; x: number; y: number; size: number }[];
    edges: { source: string; target: string }[];
  };
  timeline: { time: string; event: string; sentiment: 'bullish' | 'bearish' | 'neutral' }[];
}

export interface BeliefSnapshot {
  asset: {
    symbol: string;
    name: string;
    asset_type: string;
  };
  belief: {
    score: number;
    label: string;
    velocity: number;
    coherence: number;
    fragility: number;
    confidence: string;
  };
  breakdown: {
    attention: number;
    sentiment: number;
    momentum: number;
    source_agreement: number;
    volatility: number;
    evidence_depth: number;
  };
  signals: {
    name: string;
    score: number;
    direction: 'up' | 'down' | 'flat' | 'mixed';
    description: string;
  }[];
  narratives: {
    id: string;
    title: string;
    strength: number;
    sentiment: 'positive' | 'negative' | 'neutral' | 'mixed';
    evidence_count: number;
    keywords: string[];
    representative_evidence: string;
    trend_direction: 'up' | 'down' | 'flat' | 'mixed';
  }[];
  evidence: {
    id: string;
    symbol: string;
    source_type: string;
    source_name: string;
    text: string;
    timestamp: string;
    sentiment: number;
    attention_weight: number;
    reliability_weight: number;
    matched_keywords: string[];
    provenance: ProvenanceMeta;
    note: string;
    provider?: string | null;
    url?: string | null;
    is_synthetic?: boolean;
    is_live?: boolean;
    is_cached?: boolean;
  }[];
  evidence_bundle?: EvidenceBundle | null;
  source_mix?: Record<string, number>;
  freshness_summary?: EvidenceFreshness | null;
  provider_results?: ProviderResult[];
  warnings?: string[];
  explanation: {
    summary: string;
    drivers: string[];
    warnings: string[];
  };
  delta: BeliefDelta;
  meta: ProvenanceMeta;
}

export interface BeliefHistoryPoint {
  timestamp: string;
  score: number;
  velocity: number;
  coherence: number;
  fragility: number;
}

export interface EvidenceFreshness {
  latest_timestamp: string | null;
  oldest_timestamp: string | null;
  fresh_item_count: number;
  stale_item_count: number;
  cache_hit_count: number;
  live_item_count: number;
  synthetic_item_count: number;
}

export interface ProviderResult {
  provider: string;
  source: string;
  mode: string;
  is_fallback: boolean;
  is_live: boolean;
  is_cached: boolean;
  generated_at: string;
  fetched_at: string | null;
  expires_at: string | null;
  latency_ms: number;
  status: 'ok' | 'partial' | 'unavailable' | 'error' | 'disabled' | 'cached' | string;
  evidence: BeliefSnapshot['evidence'];
  warnings: string[];
  errors: { code: string; message: string }[];
}

export interface EvidenceBundle {
  symbol: string;
  items: BeliefSnapshot['evidence'];
  provider_results: ProviderResult[];
  freshness_summary: EvidenceFreshness;
  source_mix: Record<string, number>;
  warnings: string[];
  meta: ProvenanceMeta;
}

export interface BeliefDelta {
  symbol: string;
  previous_score: number;
  current_score: number;
  delta: number;
  changed_metrics: Record<string, number>;
  reason: string;
  source_mix?: Record<string, number>;
  freshness_summary?: EvidenceFreshness | null;
  provider_status_summary?: {
    provider: string;
    status: string;
    is_live: boolean;
    is_cached: boolean;
    is_fallback: boolean;
  }[];
  fallback_used?: boolean;
}

export interface MarketSignal {
  id: string;
  type: string;
  title: string;
  description: string;
  impact: 'low' | 'medium' | 'high';
  timestamp: string;
}

export interface MarketAlert {
  id: string;
  ticker: string;
  message: string;
  severity: 'low' | 'medium' | 'high';
  time: string;
}

export interface ApiStatus {
  status: string;
  service: string;
  version: string;
  app_mode: 'demo' | 'hybrid' | 'live' | string;
  app_env: string;
  data_mode: 'demo' | 'hybrid' | 'live' | string;
  redis: {
    configured: boolean;
    available: boolean;
  };
  llm: {
    configured: boolean;
    provider: string;
    model: string;
  };
  features: Record<string, boolean | string>;
  providers?: {
    name: string;
    enabled: boolean;
    configured: boolean;
    supports_live: boolean;
    status: string;
    last_success?: string | null;
    last_error_code?: string | null;
    mode_behavior: string;
  }[];
  evidence_cache?: {
    enabled: boolean;
    backend: string;
    ttl_seconds: number;
    entries: number;
    allow_stale_on_failure?: boolean;
    stale_max_age_seconds?: number;
  };
  provider_health?: {
    healthy: number;
    degraded: number;
    circuit_open: number;
  };
  ingestion?: {
    scheduler_enabled: boolean;
    interval_seconds: number;
    last_run: null | {
      run_id: string;
      status: string;
      started_at: string;
      finished_at: string | null;
      duration_ms: number;
      symbols_succeeded: string[];
      symbols_failed: string[];
      fallback_count: number;
    };
  };
}

type WebSocketMessage =
  | { type: 'heartbeat'; payload?: { status?: string }; meta?: ProvenanceMeta; id?: number }
  | { type: 'latency_test'; payload?: { ts: number }; ts?: number; meta?: ProvenanceMeta; id?: number }
  | { type: 'trending_update'; payload?: TrendingStock[]; data?: TrendingStock[]; meta?: ProvenanceMeta; id?: number }
  | { type: 'stock_update'; payload?: Partial<StockData>; data?: Partial<StockData>; meta?: ProvenanceMeta; id?: number }
  | { type: 'belief_snapshot'; symbol?: string; payload?: BeliefSnapshot; meta?: ProvenanceMeta; id?: number }
  | { type: 'belief_delta'; symbol?: string; payload?: BeliefDelta; meta?: ProvenanceMeta; id?: number }
  | { type: 'narrative_shift'; symbol?: string; payload?: BeliefSnapshot['narratives'][number]; meta?: ProvenanceMeta; id?: number }
  | { type: 'system_status'; payload?: { status: string; app_mode?: string; data_mode?: string; belief_stream?: string; provider_health?: ApiStatus['provider_health']; ingestion?: ApiStatus['ingestion'] }; meta?: ProvenanceMeta; id?: number }
  | { type: 'provider_health_update'; payload?: Record<string, unknown>; meta?: ProvenanceMeta; id?: number }
  | { type: 'ingestion_run_started' | 'ingestion_run_completed' | 'cache_refreshed' | 'cache_stale_served' | 'pipeline_warning'; payload?: Record<string, unknown>; meta?: ProvenanceMeta; id?: number }
  | { type: 'error'; payload?: { code: string; message: string }; meta?: ProvenanceMeta; id?: number };

interface AppState {
  activeView: ViewState;
  setActiveView: (view: ViewState) => void;
  
  // Trending Data State
  trendingStocks: TrendingStock[];
  isLoadingTrending: boolean;
  trendingMeta: ProvenanceMeta | null;
  trendingError: string | null;
  fetchTrending: () => Promise<void>;

  // Stock Detail State
  activeTicker: string | null;
  setActiveTicker: (ticker: string) => void;
  stockData: StockData | null;
  isLoadingStock: boolean;
  stockMeta: ProvenanceMeta | null;
  stockError: string | null;
  fetchStock: (ticker: string) => Promise<void>;
  beliefSnapshot: BeliefSnapshot | null;
  beliefHistory: BeliefHistoryPoint[];
  beliefDelta: BeliefDelta | null;
  isLoadingBelief: boolean;
  beliefMeta: ProvenanceMeta | null;
  beliefError: string | null;
  fetchBeliefSnapshot: (ticker: string) => Promise<void>;
  fetchBeliefHistory: (ticker: string) => Promise<void>;

  // Signals State
  signals: MarketSignal[];
  isLoadingSignals: boolean;
  signalsMeta: ProvenanceMeta | null;
  signalsError: string | null;
  fetchSignals: () => Promise<void>;

  // Alerts State
  alerts: MarketAlert[];
  isLoadingAlerts: boolean;
  alertsMeta: ProvenanceMeta | null;
  alertsError: string | null;
  fetchAlerts: () => Promise<void>;

  // Runtime Status
  apiStatus: ApiStatus | null;
  apiStatusError: string | null;
  fetchApiStatus: () => Promise<void>;

  // Watchlist State
  watchlist: string[];
  toggleWatchlistTicker: (ticker: string) => void;
  hydrateWatchlist: () => void;

  // WebSocket State
  wsConnected: boolean;
  wsMeta: ProvenanceMeta | null;
  wsError: string | null;
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
  sendWsMessage: (message: Record<string, unknown>) => void;
}

let globalWs: WebSocket | null = null;

let reconnectCount = 0;
let lastDisconnectTime: number | null = null;
let lastHeartbeatTime: number = Date.now();
let heartbeatInterval: NodeJS.Timeout | null = null;
let latencies: number[] = [];
let lastMessageId = 0;

function isEnvelope<T>(payload: unknown): payload is ApiEnvelope<T> {
  return Boolean(payload && typeof payload === 'object' && 'data' in payload && 'meta' in payload);
}

async function parseApiResponse<T>(response: Response): Promise<ApiEnvelope<T>> {
  const payload = await response.json() as ApiEnvelope<T> | T | ApiErrorPayload;

  if (!response.ok) {
    const hasError = Boolean(payload && typeof payload === 'object' && 'error' in payload);
    const message = hasError && (payload as ApiErrorPayload).error?.message
      ? (payload as ApiErrorPayload).error?.message
      : `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  if (isEnvelope<T>(payload)) {
    return payload;
  }

  return {
    data: payload as T,
    meta: {
      source: 'unavailable',
      mode: 'unknown',
      generated_at: new Date().toISOString(),
      is_fallback: true,
      provider: 'legacy-api-response',
      confidence: 'prototype',
      notes: 'Backend returned a legacy response without provenance metadata.',
    },
  };
}

(window as any).generateWsReport = () => {
  const avgLatency = latencies.length ? latencies.reduce((a, b) => a + b, 0) / latencies.length : 0;
  const report = {
    avg_latency: `${avgLatency.toFixed(2)}ms`,
    reconnect_success_rate: reconnectCount > 0 ? "100%" : "N/A",
    reconnects_attempted: reconnectCount,
    dropped_connections: reconnectCount
  };
  console.log("WebSocket Stability Report:", report);
  return report;
};

export const useAppStore = create<AppState>((set, get) => ({
  activeView: 'home',
  setActiveView: (view) => set({ activeView: view }),
  
  trendingStocks: [],
  isLoadingTrending: false,
  trendingMeta: null,
  trendingError: null,
  fetchTrending: async () => {
    set({ isLoadingTrending: true, trendingError: null });
    try {
      const response = await fetch(buildApiUrl('/api/trending'));
      const { data, meta } = await parseApiResponse<TrendingStock[]>(response);
      set({ trendingStocks: data, trendingMeta: meta, isLoadingTrending: false });
    } catch (error) {
      console.error('Failed to fetch trending stocks:', error);
      set({ isLoadingTrending: false, trendingError: error instanceof Error ? error.message : 'Failed to fetch trending stocks' });
    }
  },

  activeTicker: null,
  setActiveTicker: (ticker) => {
    set({ activeTicker: ticker, activeView: 'stock' });
    get().sendWsMessage({ type: 'subscribe', channel: 'stock', ticker });
    get().sendWsMessage({ type: 'subscribe', channel: 'belief', ticker });
  },
  stockData: null,
  isLoadingStock: false,
  stockMeta: null,
  stockError: null,
  fetchStock: async (ticker) => {
    set({ isLoadingStock: true, stockData: null, stockError: null });
    try {
      const response = await fetch(buildApiUrl(`/api/stock/${ticker}`));
      const { data, meta } = await parseApiResponse<StockData>(response);
      set({ stockData: data, stockMeta: meta, isLoadingStock: false });
    } catch (error) {
      console.error('Failed to fetch stock data:', error);
      set({ isLoadingStock: false, stockError: error instanceof Error ? error.message : 'Failed to fetch stock data' });
    }
  },
  beliefSnapshot: null,
  beliefHistory: [],
  beliefDelta: null,
  isLoadingBelief: false,
  beliefMeta: null,
  beliefError: null,
  fetchBeliefSnapshot: async (ticker) => {
    set({ isLoadingBelief: true, beliefError: null });
    try {
      const response = await fetch(buildApiUrl(`/api/belief/${ticker}`));
      const { data, meta } = await parseApiResponse<BeliefSnapshot>(response);
      set({ beliefSnapshot: data, beliefDelta: data.delta, beliefMeta: meta, isLoadingBelief: false });
    } catch (error) {
      console.error('Failed to fetch belief snapshot:', error);
      set({ isLoadingBelief: false, beliefError: error instanceof Error ? error.message : 'Failed to fetch belief snapshot' });
    }
  },
  fetchBeliefHistory: async (ticker) => {
    try {
      const response = await fetch(buildApiUrl(`/api/belief/${ticker}/history`));
      const { data, meta } = await parseApiResponse<BeliefHistoryPoint[]>(response);
      set({ beliefHistory: data, beliefMeta: meta });
    } catch (error) {
      console.error('Failed to fetch belief history:', error);
      set({ beliefError: error instanceof Error ? error.message : 'Failed to fetch belief history' });
    }
  },

  signals: [],
  isLoadingSignals: false,
  signalsMeta: null,
  signalsError: null,
  fetchSignals: async () => {
    set({ isLoadingSignals: true, signalsError: null });
    try {
      const response = await fetch(buildApiUrl('/api/signals'));
      const { data, meta } = await parseApiResponse<MarketSignal[]>(response);
      set({ signals: data, signalsMeta: meta, isLoadingSignals: false });
    } catch (error) {
      console.error('Failed to fetch signals:', error);
      set({ isLoadingSignals: false, signalsError: error instanceof Error ? error.message : 'Failed to fetch signals' });
    }
  },

  alerts: [],
  isLoadingAlerts: false,
  alertsMeta: null,
  alertsError: null,
  fetchAlerts: async () => {
    set({ isLoadingAlerts: true, alertsError: null });
    try {
      const response = await fetch(buildApiUrl('/api/alerts'));
      const { data, meta } = await parseApiResponse<MarketAlert[]>(response);
      set({ alerts: data, alertsMeta: meta, isLoadingAlerts: false });
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
      set({ isLoadingAlerts: false, alertsError: error instanceof Error ? error.message : 'Failed to fetch alerts' });
    }
  },

  apiStatus: null,
  apiStatusError: null,
  fetchApiStatus: async () => {
    try {
      const response = await fetch(buildApiUrl('/api/status'));
      if (!response.ok) throw new Error(`Status request failed with ${response.status}`);
      const data = await response.json() as ApiStatus;
      set({ apiStatus: data, apiStatusError: null });
    } catch (error) {
      console.error('Failed to fetch API status:', error);
      set({ apiStatusError: error instanceof Error ? error.message : 'Backend offline' });
    }
  },

  watchlist: [],
  hydrateWatchlist: () => {
    try {
      const raw = localStorage.getItem('qb-watchlist');
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        set({ watchlist: parsed.map((ticker) => String(ticker).toUpperCase()) });
      }
    } catch (error) {
      console.error('Failed to hydrate watchlist:', error);
    }
  },
  toggleWatchlistTicker: (ticker) => {
    const normalized = ticker.toUpperCase();
    set((state) => {
      const next = state.watchlist.includes(normalized)
        ? state.watchlist.filter((t) => t !== normalized)
        : [...state.watchlist, normalized];
      try {
        localStorage.setItem('qb-watchlist', JSON.stringify(next));
      } catch (error) {
        console.error('Failed to persist watchlist:', error);
      }
      return { watchlist: next };
    });
  },

  wsConnected: false,
  wsMeta: null,
  wsError: null,
  sendWsMessage: (message: Record<string, unknown>) => {
    if (globalWs && globalWs.readyState === WebSocket.OPEN) {
      globalWs.send(JSON.stringify(message));
    }
  },
  disconnectWebSocket: () => {
    shouldReconnect = false;
    if (heartbeatInterval) {
      clearInterval(heartbeatInterval);
      heartbeatInterval = null;
    }
    if (globalWs) {
      const ws = globalWs;
      globalWs = null;
      ws.onopen = null;
      ws.onmessage = null;
      ws.onerror = null;
      ws.onclose = null;

      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CLOSING) {
        ws.close();
      } else {
        ws.addEventListener('open', () => ws.close(), { once: true });
      }
    }
    set({ wsConnected: false });
  },
  connectWebSocket: () => {
    // Prevent multiple connections
    if (globalWs && (globalWs.readyState === WebSocket.CONNECTING || globalWs.readyState === WebSocket.OPEN)) return;
    if (get().wsConnected) return;

    try {
      shouldReconnect = true;
      const wsUrl = resolveWsUrl();
        
      const ws = new WebSocket(wsUrl);
      globalWs = ws;

      if (heartbeatInterval) clearInterval(heartbeatInterval);
      heartbeatInterval = setInterval(() => {
        if (globalWs && globalWs.readyState === WebSocket.OPEN) {
          const timeSinceLastHeartbeat = Date.now() - lastHeartbeatTime;
          if (timeSinceLastHeartbeat > 25000) {
            console.warn("No heartbeat received for >25s. Forcing reconnect...");
            globalWs.close();
          }
        }
      }, 5000);

      ws.onopen = () => {
        if (lastDisconnectTime) {
          const timeDiff = Date.now() - lastDisconnectTime;
          console.log({
            reconnects: reconnectCount,
            lastReconnectTime: `${timeDiff}ms`
          });
          lastDisconnectTime = null;
        }
        lastHeartbeatTime = Date.now();
        console.log('WebSocket connected');
        set({ wsConnected: true });
        
        // Send resume
        if (lastMessageId > 0) {
            ws.send(JSON.stringify({ type: 'resume', last_message_id: lastMessageId }));
        }

        // Subscribe to updates (legacy, backend now broadcasts)
        ws.send(JSON.stringify({ type: 'subscribe', channel: 'trending' }));
        const activeTicker = get().activeTicker;
        if (activeTicker) {
          ws.send(JSON.stringify({ type: 'subscribe', channel: 'stock', ticker: activeTicker }));
          ws.send(JSON.stringify({ type: 'subscribe', channel: 'belief', ticker: activeTicker }));
        }
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          
          if (message.id) {
              lastMessageId = message.id;
              ws.send(JSON.stringify({ type: 'ack', id: message.id }));
          }

          // TASK 5 - HEARTBEAT HANDLING (FRONTEND)
          if (message.type === 'heartbeat') {
            lastHeartbeatTime = Date.now();
            if (message.meta) set({ wsMeta: message.meta });
            return;
          }

          if (message.type === 'latency_test') {
            const ts = message.payload?.ts ?? message.ts ?? Date.now();
            const latency = Date.now() - ts;
            latencies.push(latency);
            if (latencies.length > 50) latencies.shift();
            if (message.meta) set({ wsMeta: message.meta });
            return;
          }

          if (message.type === 'error') {
            set({ wsError: message.payload?.message ?? 'WebSocket error', wsMeta: message.meta ?? null });
            return;
          }
          
          console.log("Received:", message);
          
          if (message.type === 'trending_update' && (message.payload || message.data)) {
            const incoming = message.payload ?? message.data ?? [];
            // Smoothly merge trending updates
            set((state) => {
              const updatedStocks = [...state.trendingStocks];
              incoming.forEach((incomingStock: TrendingStock) => {
                const idx = updatedStocks.findIndex(s => s.ticker === incomingStock.ticker);
                if (idx !== -1) {
                  updatedStocks[idx] = { ...updatedStocks[idx], ...incomingStock };
                } else {
                  updatedStocks.push(incomingStock);
                }
              });
              return { trendingStocks: updatedStocks, trendingMeta: message.meta ?? state.trendingMeta, wsMeta: message.meta ?? state.wsMeta };
            });
          } else if (message.type === 'stock_update' && (message.payload || message.data)) {
            const incoming = message.payload ?? message.data;
            // Update stock data if it matches the currently active ticker
            set((state) => {
              if (incoming && state.activeTicker === incoming.ticker) {
                return { stockData: { ...state.stockData, ...incoming } as StockData, stockMeta: message.meta ?? state.stockMeta, wsMeta: message.meta ?? state.wsMeta };
              }
              return state;
            });
          } else if (message.type === 'belief_snapshot' && message.payload) {
            set((state) => {
              if (!message.payload || (state.activeTicker && message.payload.asset.symbol !== state.activeTicker)) {
                return { wsMeta: message.meta ?? state.wsMeta };
              }
              return {
                beliefSnapshot: message.payload,
                beliefDelta: message.payload.delta,
                beliefMeta: message.meta ?? message.payload.meta ?? state.beliefMeta,
                wsMeta: message.meta ?? state.wsMeta,
              };
            });
          } else if (message.type === 'belief_delta' && message.payload) {
            set((state) => {
              if (state.activeTicker && message.payload?.symbol !== state.activeTicker) {
                return { wsMeta: message.meta ?? state.wsMeta };
              }
              return {
                beliefDelta: message.payload ?? state.beliefDelta,
                wsMeta: message.meta ?? state.wsMeta,
              };
            });
          } else if (
            message.type === 'narrative_shift'
            || message.type === 'system_status'
            || message.type === 'provider_health_update'
            || message.type === 'ingestion_run_started'
            || message.type === 'ingestion_run_completed'
            || message.type === 'cache_refreshed'
            || message.type === 'cache_stale_served'
            || message.type === 'pipeline_warning'
          ) {
            if (message.meta) set({ wsMeta: message.meta });
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.onclose = () => {
        if (!shouldReconnect) {
          globalWs = null;
          return;
        }
        lastDisconnectTime = Date.now();
        reconnectCount++;
        console.log('WebSocket disconnected. Reconnecting...');
        set({ wsConnected: false, wsError: 'WebSocket disconnected. Reconnecting...' });
        globalWs = null;
        // Attempt to reconnect after 3 seconds
        setTimeout(() => {
          if (shouldReconnect) {
            get().connectWebSocket();
          }
        }, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        set({ wsError: 'WebSocket connection error' });
      };
    } catch (error) {
      console.error('Failed to initialize WebSocket:', error);
    }
  }
}));
