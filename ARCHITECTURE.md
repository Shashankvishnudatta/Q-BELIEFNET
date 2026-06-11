# Architecture

## Frontend Architecture

- `src/App.tsx`: app shell, navigation, assistant surface, runtime status indicator.
- `src/store.ts`: Zustand state for API envelopes, provenance metadata, API errors, WebSocket state, and watchlist persistence.
- `src/components/DataSourceBadges.tsx`: reusable product-trust components for runtime mode, source, fallback, and API status.
- `src/components/BeliefIntelligencePanels.tsx`: belief score, metric breakdown, narrative clusters, evidence, explanation, history, and delta panels.
- `src/components/`: dashboard views for trending, stock details, signals, alerts, watchlist, reports, portfolio, and settings.
- `src/services/llm.ts`: backend LLM client plus local fallback/routing behavior.

## Backend Architecture

- `backend/main.py`: FastAPI app, CORS, middleware, route registration, status routes, structured error handlers, background task lifecycle.
- `backend/app/core/config.py`: typed runtime settings with `APP_MODE` and `DATA_MODE`.
- `backend/app/core/contracts.py`: provenance metadata, API response envelopes, structured application errors, live-mode guards.
- `backend/app/api/routes/`: REST API routes for market views, alerts, belief intelligence, and LLM.
- `backend/app/api/websockets.py`: typed WebSocket stream with provenance metadata, heartbeat, latency probes, ack/resume, and subscription errors.
- `backend/app/services/belief_engine.py`: deterministic prototype belief scoring, narrative grouping, deltas, history, and explainability.
- `backend/app/services/evidence_pipeline.py`: provider orchestration, fallback rules, source mix, freshness, and evidence bundles.
- `backend/app/services/providers/`: demo provider, live-capable market provider, TTL cache, and registry.
- `backend/app/services/`: market data, generated mock data, processing, embeddings, metrics, clustering, and ingestion scaffolding.

## Runtime Mode Model

`demo`: returns generated/mock market intelligence and labels it as generated.  
`hybrid`: attempts live-capable provider paths and labels fallback when used.  
`live`: requires provider credentials; missing config returns a structured error instead of pretending data is live.

## Data Provenance Model

Market responses use:

```json
{
  "data": {},
  "meta": {
    "source": "live | mock | generated | cached | fallback | unavailable",
    "mode": "demo | hybrid | live",
    "generated_at": "ISO timestamp",
    "is_fallback": false,
    "provider": "provider-or-generator-name",
    "confidence": "prototype | low | medium | high",
    "notes": "human-readable explanation"
  }
}
```

## Error Model

Expected failures use:

```json
{
  "error": {
    "code": "LLM_NOT_CONFIGURED",
    "message": "AI assistant is unavailable because the backend LLM key is not configured.",
    "details": {},
    "request_id": "uuid"
  }
}
```

Request IDs are also returned as `X-Request-ID`.

## Belief Intelligence Engine

The Phase 2 engine returns a full belief snapshot:

```text
BeliefAsset
BeliefScore
SignalBreakdown
BeliefSignal[]
NarrativeCluster[]
EvidenceItem[]
BeliefExplanation
BeliefDelta
Data provenance
```

The engine is deterministic for a symbol and time window. Demo evidence is synthetic and labeled with `internal-demo-generator`.

## Evidence Provider Layer

Phase 3 introduces `EvidenceProvider`, `ProviderResult`, `EvidenceCache`, `ProviderRegistry`, and `EvidencePipeline`.

```text
Providers -> Evidence Pipeline -> Belief Engine -> API/WebSocket -> Frontend Panels/LLM Context
```

Mode behavior:

- `demo`: deterministic generated evidence.
- `hybrid`: live-capable providers first, then visible demo fallback.
- `live`: live providers only unless `ALLOW_LIVE_MODE_DEMO_FALLBACK=true`.

Evidence bundles include `source_mix`, `freshness_summary`, `provider_results`, per-item provenance, and warnings.

## Provider Observability

Phase 4 adds provider runtime metrics:

- success/failure counts,
- consecutive failures,
- average and last latency,
- last success/failure timestamps,
- redacted last error,
- circuit state,
- last result source/count,
- last fallback flag.

## Provider Reliability Controls

Provider calls run through a lightweight reliability wrapper:

```text
Provider Registry
 -> Reliability Wrapper
 -> Evidence Pipeline
 -> Cache
 -> Belief Engine
 -> API/WebSocket
 -> Frontend Observability Panels
```

Controls:

- timeout,
- retry,
- circuit breaker,
- structured failure result.

Demo provider should remain healthy. Live-capable provider failures are visible and do not crash hybrid/demo flows.

## Evidence Cache Lifecycle

The in-memory cache tracks fresh hits, misses, stale entries, stale reasons, age, TTL, `cached_at`, and `expires_at`. Hybrid/live paths may serve stale cache after provider failure only when configured, and stale use is visible in the response.

## Background Refresh Pipeline

`background_refresh.py` provides optional scheduled refresh and in-memory run history. It calls the same evidence pipeline used by APIs, records success/failure by symbol, provider result summaries, cache updates, fallback counts, duration, and errors.

### Belief Score Formula

`belief_score` combines attention, sentiment, momentum, source agreement, and inverse fragility into a 0-100 interpretive signal. The implementation uses transparent weighted arithmetic instead of opaque ML so the score can be inspected and tested.

### Narrative Clustering

Narratives are grouped with keyword rules across earnings, product/news, analyst ratings, macro/rates, valuation, regulation, social hype, risk/fear, and technical momentum. This is intentionally lightweight and explainable.

## WebSocket Message Flow

1. Client connects to `/ws`.
2. Client optionally sends `subscribe`, `ack`, and `resume`.
3. Server sends typed messages with `type`, `payload`, `meta`, and `id`.
4. Client updates Zustand state after basic type discrimination.
5. Belief stream messages include `belief_snapshot`, `belief_delta`, `narrative_shift`, and `system_status`.
6. Belief snapshot/delta messages include source mix, freshness, provider summaries, and fallback flags.
7. Pipeline events include `provider_health_update`, `ingestion_run_started`, `ingestion_run_completed`, `cache_refreshed`, `cache_stale_served`, and `pipeline_warning`.
8. Heartbeats and latency probes keep status visible without implying live market truth.

## LLM Request Flow

1. Frontend sends question and prompt metadata to `/api/llm`.
2. Backend reads `HF_API_KEY` and `HF_MODEL_ID`.
3. Backend builds belief snapshot context when a ticker is detected.
4. If configured, backend calls Hugging Face chat completions with a no-financial-advice prompt.
5. If not configured, backend returns a local belief-aware fallback answer with source mix and freshness context.
6. Phase 4 context includes provider health and cache summary when available.

## Deployment Flow

- Local dev: `npm run dev` starts the TypeScript Express/Vite proxy and backend can run on port `8000`.
- Docker: Nginx frontend serves static assets and proxies `/api` and `/ws`.
- Vercel: frontend build only.
- Render: backend service using `cd backend && uvicorn main:app`.

## Known Architectural Limits

- Background tasks should move to FastAPI lifespan.
- Provider handling is not yet a clean plugin/provider abstraction.
- Belief evidence is synthetic until live evidence providers are connected.
- Provenance is endpoint-level for older market routes; belief evidence has per-item provenance.
- Redis/FAISS/spaCy paths are partial and optional.
