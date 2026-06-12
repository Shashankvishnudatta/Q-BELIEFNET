# Audit Report

## Phase 1 Changes Completed

Phase 1 upgraded Q-Belief Net from a polished demo toward a trustworthy product prototype foundation. The core changes are security guardrails, explicit runtime modes, API provenance envelopes, structured error handling, WebSocket metadata, frontend provenance badges, stronger env contracts, deployment alignment, and acceptance tests.

## Phase 2 Changes Completed

Phase 2 adds an explainable Belief Intelligence Engine. The project now has deterministic prototype belief snapshots, metric breakdowns, narrative clusters, synthetic evidence objects, score explanations, history, deltas, belief-specific WebSocket messages, belief-aware frontend panels, and backend tests for the new intelligence layer.

## Phase 3 Changes Completed

Phase 3 adds a live-capable evidence provider layer. Belief snapshots now flow through provider registry, evidence pipeline, in-memory TTL cache, source mix, freshness summaries, provider results, and fallback warnings before reaching the belief engine, WebSocket stream, frontend panels, and LLM context.

## Phase 4 Changes Completed

Phase 4 adds pipeline observability and reliability maturity: provider runtime metrics, timeout/retry/circuit-breaker behavior, stale-cache lifecycle metadata, optional background refresh, ingestion run history, ingestion status/manual refresh endpoints, WebSocket pipeline events, Settings view observability panels, and LLM pipeline-health context.

## Phase 4 Pipeline and Observability Audit

- Evidence fetching before Phase 4: request-time only through `build_evidence_bundle`.
- Cache before Phase 4: simple in-memory TTL with cached result flag.
- Provider health before Phase 4: configured/enabled/status only.
- Provider failures before Phase 4: structured result errors, but no counters or circuit state.
- Provider latency before Phase 4: per-result latency only.
- Background jobs before Phase 4: no evidence refresh scheduler.
- Ingestion run history before Phase 4: none.
- Frontend visibility before Phase 4: stock detail source/freshness/provider panels, but no operational pipeline panel.
- What remains request-time: API belief snapshots still compute on demand unless background refresh is enabled.
- What remains demo/prototype: demo evidence, basic market-derived live-capable provider, unauthenticated manual refresh, in-memory-only metrics/cache/run history.

Phase 4 improvements:

- provider runtime metrics: success/failure counts, consecutive failures, latency averages, circuit state, redacted errors,
- reliability wrapper: timeout, retry, circuit breaker,
- cache lifecycle: hit/miss, age, TTL, stale status, stale reason, served stale,
- optional background refresh service,
- ingestion status and manual refresh endpoints,
- WebSocket pipeline observability events,
- Settings view pipeline observability panel.

## Phase 3 Data Provider Audit

- Existing data sources: `market_data.py` contains live-capable Yahoo/RapidAPI and social-provider paths; `mock_data.py` contains generated dashboard data; `belief_engine.py` previously generated synthetic evidence internally.
- Demo/generated sources: `internal-demo-generator` now lives in `providers/demo_provider.py` and returns deterministic synthetic evidence with per-item provenance.
- Live-capable sources: `providers/market_provider.py` wraps the existing market data path and only emits live market-derived evidence when configured.
- Fallback behavior: `evidence_pipeline.py` uses demo evidence in demo mode, tries live-capable providers in hybrid mode, and adds visible demo fallback if live evidence is unavailable.
- Live mode behavior: live mode does not silently use demo evidence unless `ALLOW_LIVE_MODE_DEMO_FALLBACK=true`.
- Cache: `providers/cache.py` implements in-memory TTL caching with cache-hit metadata; no secrets or user data are stored.
- Freshness: evidence bundles include latest/oldest timestamps, fresh/stale counts, cache hit count, live item count, and synthetic item count.
- Provider errors: unconfigured providers return structured `ProviderResult.errors` instead of pretending data exists.
- Belief engine input: `/api/belief/{symbol}` now builds an evidence bundle and computes the belief snapshot from that bundle.
- Frontend visibility: stock detail now shows source mix, freshness, provider status, and evidence trust/fallback state.

## Phase 2 Intelligence Flow Audit

- Trending data: existing `/api/trending` can use generated demo data or live-capable Yahoo/RapidAPI paths outside demo mode. New `/api/belief/trending` ranks assets by belief score and velocity from the Phase 2 engine.
- Stock details: existing `/api/stock/{ticker}` returns chart-oriented stock detail cards. The new `/api/belief/{symbol}` returns belief-specific analytics with evidence and explanations.
- Signals: `/api/signals` remains demo in demo mode and live-capable through market/social provider scaffolding outside demo mode.
- Belief score, velocity, coherence, fragility: now calculated in `backend/app/services/belief_engine.py` from attention, sentiment, momentum, source agreement, volatility, evidence depth, and inverse fragility.
- Narrative clusters: lightweight keyword grouping in `belief_engine.py`; not heavy ML.
- Evidence: generated deterministic synthetic evidence labeled `internal-demo-generator` with per-item provenance and synthetic-demo notes.
- Embeddings/clustering services: FAISS, spaCy, and clustering code remain partial/scaffolded and are not used by the Phase 2 belief engine.
- Frontend consumers: `src/store.ts` fetches `/api/belief/{symbol}` and `/history`; `src/components/StockDetail.tsx` renders the belief panels from `BeliefIntelligencePanels.tsx`.
- WebSocket stream: now includes `belief_snapshot`, `belief_delta`, `narrative_shift`, and `system_status` messages with provenance metadata.
- Mock/live status: Phase 2 belief engine is demo/prototype-generated. It is live-provider-ready in architecture but does not yet aggregate real evidence.

## Security Status

Current source no longer contains the previously hardcoded Hugging Face-style token. The frontend no longer uses `VITE_HF_API_KEY`. Backend LLM calls use backend `HF_API_KEY`.

Git history still contains the old token pattern. Rotate the exposed key immediately and purge history before publishing or sharing the repo publicly.

## Runtime Mode Changes

Backend settings now include:

- `APP_MODE`: `demo | hybrid | live`
- `DATA_MODE`: `demo | hybrid | live`
- `APP_ENV`
- `API_HOST`
- `API_PORT`
- `HF_MODEL_ID`

Behavior:

- `demo`: generated/mock data only.
- `hybrid`: live-capable provider attempts with declared fallback.
- `live`: structured failure when required provider credentials are missing.

## Provenance Changes

Market endpoints now return:

- `data`
- `meta.source`
- `meta.mode`
- `meta.generated_at`
- `meta.is_fallback`
- `meta.provider`
- `meta.confidence`
- `meta.notes`

Applied to:

- `/api/trending`
- `/api/stock/{ticker}`
- `/api/signals`
- `/api/alerts`
- WebSocket messages

## WebSocket Contract Changes

WebSocket messages now include `type`, `payload`, `meta`, and message `id`. Legacy `data` fields remain on market update messages for compatibility.

Handled message types:

- `heartbeat`
- `latency_test`
- `trending_update`
- `stock_update`
- `belief_snapshot`
- `belief_delta`
- `narrative_shift`
- `system_status`
- `error`

## Belief Engine Formula

The 0-100 belief score is a weighted combination of attention, sentiment, momentum, source agreement, and inverse fragility. Supporting metrics:

- attention: evidence volume and intensity,
- sentiment: weighted tone,
- velocity: momentum relative to prior generated window,
- coherence: source agreement and low volatility,
- fragility: instability from sparse, volatile, concentrated, or fallback evidence,
- source agreement: alignment across source categories.

This is interpretive analytics, not financial advice or price prediction.

## Error Model Changes

Expected failures return:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {},
    "request_id": "uuid"
  }
}
```

Request IDs are attached to HTTP responses.

## Frontend Product Clarity

Added reusable UI:

- `DataSourceBadge`
- `RuntimeModeBadge`
- `FallbackNotice`
- `ApiStatusCard`

The dashboard now surfaces backend status, LLM availability, runtime mode, source type, and fallback warnings without disrupting core flows.

## Build/Test Status

Validated during Phase 1:

- `npm run lint`
- `npm run build`
- `python -m pytest`

Validated during Phase 2:

- `npm run lint`
- `npm run build`
- `cd backend; $env:PYTHONDONTWRITEBYTECODE='1'; .venv\Scripts\python.exe -m pytest`

Backend acceptance tests now cover health, status, provenance, mock data, route shape, LLM safety, belief scoring, belief routes, narrative clusters, and explanations.

Phase 3 tests cover:

- demo provider provenance and stability,
- evidence pipeline source mix and hybrid fallback,
- live mode refusing silent demo fallback,
- provider status without secret leakage,
- cache hit metadata,
- belief endpoint evidence bundle integration,
- LLM fallback source-context awareness.

Phase 4 tests cover:

- provider runtime metrics updating on success,
- structured timeout errors,
- circuit opening after repeated failures,
- stale cache lifecycle metadata,
- ingestion status endpoint,
- manual refresh symbol validation and one-symbol refresh,
- background refresh one-cycle execution,
- WebSocket pipeline event publishing.

## Remaining Risks

- Secret still exists in Git history until purged.
- FastAPI still uses deprecated `on_event`; migrate to lifespan next.
- Frontend tests and CI are still missing.
- Docker full build should be run before deployment.
- Live providers need real credentials, retry policy, caching, and observability.
- Phase 2 belief evidence is synthetic until real evidence providers are connected.
- Phase 3 adds a provider abstraction, but real social/news aggregation is still future work.
- Provenance is endpoint-level for older market routes; belief evidence has per-item provenance.

## Next Phase Recommendations

1. Rotate and purge secret history.
2. Migrate FastAPI background tasks to lifespan.
3. Add GitHub Actions or equivalent CI.
4. Add frontend tests for status/provenance/belief panels.
5. Build live evidence provider abstraction with retries, caching, and per-record provenance.
6. Add richer live news/social providers and observability around provider failures.

## Phase 5 Persistence and Workspace Audit

State that was in memory before Phase 5:

- provider cache contents and cache lifecycle metadata,
- ingestion run history,
- provider runtime health history,
- recent belief snapshots,
- manual refresh operation history,
- user workspace state beyond frontend localStorage.

State moved to SQLite-backed local persistence:

- `belief_snapshots`: persisted score, metrics, provenance, evidence bundle, narratives, and explanation JSON,
- `ingestion_runs`: manual/background refresh outcomes and trigger metadata,
- `provider_health_events`: redacted provider status/latency/circuit snapshots,
- `evidence_cache_records`: durable cache metadata and hit/stale counts,
- `watchlist_items`, `portfolio_items`, `alert_rules`: local workspace continuity,
- `operation_audit_log`: auditable manual refreshes, workspace edits, and snapshot generation.

State that remains intentionally ephemeral:

- active WebSocket clients,
- in-flight background refresh task state,
- full in-memory evidence cache payloads,
- UI-only preferences such as temporary form state.

Local database status:

- Default database path is `backend/data/qbeliefnet.db`.
- Database files are ignored by Git.
- Existing local `backend/data/metrics.db` remains a local artifact and should not be tracked.
- Tests use ignored workspace-local database files under `backend/.test_tmp/`.

Manual refresh safety:

- `POST /api/ingestion/refresh` validates symbols, enforces `MAX_MANUAL_REFRESH_SYMBOLS`, and can require `X-QBN-Admin-Token`.
- Status reports whether manual refresh is enabled and whether a token is required, but never exposes token values.
- Manual refresh operations are persisted in the operation audit log.

Workspace continuity:

- New persistent workspace APIs expose watchlist, tracking portfolio, and belief alert rules.
- These are local tracking features only and do not place trades or represent brokerage data.

Remaining Phase 5 risks:

- SQLite is appropriate for a local prototype, but Postgres or managed storage is recommended before multi-user production.
- Manual refresh guard is not a full authentication system.
- FastAPI startup still uses deprecated `on_event`; lifespan migration remains recommended.
- Frontend tests and CI remain future work.
