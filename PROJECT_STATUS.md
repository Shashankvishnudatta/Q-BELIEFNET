# Project Status

## What Is Implemented

- React/TypeScript dashboard with Zustand state.
- FastAPI backend with health/status, structured error model, and provenance envelopes.
- Runtime modes: `demo`, `hybrid`, `live`.
- WebSocket stream with typed messages, heartbeat, latency probes, ack/resume, reconnect, and provenance metadata.
- Backend-only Hugging Face LLM key handling.
- Phase 2 belief intelligence engine with deterministic prototype scoring, signal breakdowns, narrative clusters, evidence, explanations, deltas, and history.
- Belief endpoints: `/api/belief/{symbol}`, `/api/belief/{symbol}/history`, and `/api/belief/trending`.
- Frontend belief panels for score explanation, metric breakdown, narratives, evidence, history, and stream deltas.
- Belief-aware local assistant fallback when hosted LLM credentials are not configured.
- Evidence provider layer with demo provider, live-capable market provider, registry, in-memory TTL cache, and evidence pipeline.
- Provider status endpoint at `/api/providers/status`.
- Frontend evidence transparency panels for source mix, freshness, provider status, and trust/fallback state.
- Provider runtime metrics, timeout/retry/circuit-breaker controls, stale-cache lifecycle metadata, ingestion run history, optional background refresh, and `/api/ingestion/status`.
- Settings view pipeline observability panel for provider health, cache, and ingestion state.
- SQLite local persistence for belief snapshots, ingestion runs, provider health events, cache metadata, workspace state, and operation audit logs.
- Workspace endpoints for watchlist, tracking portfolio, and belief alert rules.
- Manual refresh safety guard with optional `X-QBN-Admin-Token`.
- Settings view persistence/workspace/audit panels.
- Docker, Render, and Vercel deployment configs.
- Backend acceptance tests for health, status, provenance, routes, mock data, LLM safety, belief engine, belief routes, narrative clusters, and explanations.

## What Is Demo/Mock

- Alerts feed.
- Portfolio and reports views.
- WebSocket stream content.
- Belief graph visualization.
- Belief engine evidence, score, velocity, coherence, fragility, and narrative clusters in demo mode.
- Demo provider evidence in fallback paths when `DATA_MODE=hybrid` and live providers are unavailable.

## What Is Live-Capable

- Trending stocks and stock detail can use Yahoo/RapidAPI paths outside demo mode.
- Signals can use public/provider social data paths outside demo mode.
- LLM assistant can use Hugging Face when backend `HF_API_KEY` is configured.
- Belief engine is architected for live evidence providers but currently uses deterministic generated evidence.
- Market-derived evidence provider is live-capable when backend provider credentials are configured.

## What Is Not Implemented

- LangChain.
- Production trading/investment recommendations.
- Real authenticated user accounts.
- Real authenticated user accounts.
- Full CI pipeline.
- Frontend unit/integration tests.
- Rich live social/news evidence aggregation beyond the basic market provider.
- Production-authenticated manual ingestion refresh endpoint.
- Postgres or managed database persistence for multi-user production.

## What Is Planned

- FastAPI lifespan migration.
- Provider abstraction and per-record provenance.
- Frontend tests and CI.
- Production-grade auth/storage.
- Better observability and deployment hardening.

## How To Explain Product Honestly

Q-Belief Net is a serious full-stack market-belief intelligence prototype. It is designed around transparent runtime modes and provenance metadata, so the UI and APIs do not pretend generated demo analytics are live market truth. The current foundation supports demo mode by default, hybrid live-capable provider paths, backend-secured LLM calls, and WebSocket demo streams for product exploration.

The Phase 2 belief engine adds explainable analytics: every score has a formula, metric breakdown, synthetic evidence, narrative clusters, warnings, and provenance. It should be described as a belief-signal analytics prototype, not a stock-price prediction system.

Phase 3 adds a provider pipeline so belief scores are backed by explicit evidence bundles. The UI and APIs now show source mix, freshness, provider status, cache hits, and fallback warnings.

Phase 4 adds pipeline maturity: provider runtime metrics, reliability controls, visible cache lifecycle, optional background refresh, ingestion run history, WebSocket pipeline events, and frontend operational observability.

Phase 5 adds local durability and workspace continuity. Belief snapshots, ingestion runs, provider health events, cache metadata, watchlists, tracking portfolio rows, belief alert rules, and operation audit records can now survive backend restarts when SQLite persistence is enabled. This is still a local product prototype, not a multi-user SaaS deployment.

## Resume/Product-Safe Summary

Built Q-Belief Net, a full-stack market-belief intelligence prototype using React, TypeScript, Zustand, Recharts, FastAPI, WebSockets, Docker, and backend-secured LLM integration. Implemented product runtime modes, API provenance metadata, structured error handling, demo/live data boundaries, and an explainable belief engine with deterministic prototype scoring, narrative clusters, evidence, and non-financial-advice assistant context.
