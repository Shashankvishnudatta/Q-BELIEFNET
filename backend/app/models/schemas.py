from pydantic import BaseModel, Field
from typing import Generic, List, Literal, TypeVar

from app.core.contracts import ProvenanceMeta

class SparklinePoint(BaseModel):
    time: int
    value: float

class TrendingStock(BaseModel):
    id: str
    ticker: str
    name: str
    beliefScore: int = Field(..., ge=0, le=100)
    sentiment: str
    velocity: float
    sector: str
    marketCap: str
    sparkline: List[SparklinePoint]

class Metrics(BaseModel):
    coherence: str
    velocity: str
    fragility: str

class ChartDataPoint(BaseModel):
    date: str
    price: str
    belief: str

class Cluster(BaseModel):
    label: str
    dominance: int
    color: str

class Node(BaseModel):
    id: str
    label: str
    x: int
    y: int
    size: int

class Edge(BaseModel):
    source: str
    target: str

class Network(BaseModel):
    nodes: List[Node]
    edges: List[Edge]

class TimelineEvent(BaseModel):
    time: str
    event: str
    sentiment: str

class StockDetail(BaseModel):
    ticker: str
    name: str
    beliefScore: int
    signal: str
    metrics: Metrics
    chartData: List[ChartDataPoint]
    clusters: List[Cluster]
    network: Network
    timeline: List[TimelineEvent]

class Signal(BaseModel):
    id: str
    type: str
    title: str
    description: str
    impact: str
    timestamp: str

class Alert(BaseModel):
    id: str
    ticker: str
    message: str
    severity: str
    time: str


SentimentLabel = Literal["positive", "negative", "neutral", "mixed"]
AssetType = Literal["equity", "crypto", "index", "unknown"]
TrendDirection = Literal["up", "down", "flat", "mixed"]
SourceType = Literal["social", "news", "market", "analyst", "technical", "demo"]
ProviderStatusValue = Literal["ok", "healthy", "partial", "unavailable", "error", "disabled", "cached", "timeout", "circuit_open"]
CircuitState = Literal["closed", "open", "half_open"]


class BeliefAsset(BaseModel):
    symbol: str
    name: str
    asset_type: AssetType = "equity"


class BeliefSignal(BaseModel):
    name: str
    score: float = Field(..., ge=0, le=100)
    direction: TrendDirection
    description: str


class BeliefMetric(BaseModel):
    value: float = Field(..., ge=0, le=100)
    label: str
    description: str


class BeliefScore(BaseModel):
    score: int = Field(..., ge=0, le=100)
    label: str
    velocity: float = Field(..., ge=-100, le=100)
    coherence: float = Field(..., ge=0, le=1)
    fragility: float = Field(..., ge=0, le=1)
    confidence: str = "prototype"


class SignalBreakdown(BaseModel):
    attention: float = Field(..., ge=0, le=100)
    sentiment: float = Field(..., ge=0, le=100)
    momentum: float = Field(..., ge=0, le=100)
    source_agreement: float = Field(..., ge=0, le=100)
    volatility: float = Field(..., ge=0, le=100)
    evidence_depth: float = Field(..., ge=0, le=100)


class EvidenceItem(BaseModel):
    id: str
    symbol: str
    source_type: SourceType
    source_name: str
    text: str
    timestamp: str
    sentiment: float = Field(..., ge=-1, le=1)
    attention_weight: float = Field(..., ge=0, le=1)
    reliability_weight: float = Field(..., ge=0, le=1)
    matched_keywords: List[str]
    provenance: ProvenanceMeta
    note: str
    provider: str | None = None
    url: str | None = None
    is_synthetic: bool = False
    is_live: bool = False
    is_cached: bool = False


class EvidenceRequest(BaseModel):
    symbol: str
    mode: str = "demo"
    window: str = "latest"
    allow_fallback: bool = True


class SourceReliability(BaseModel):
    provider: str
    reliability_weight: float = Field(..., ge=0, le=1)
    rationale: str


class EvidenceFreshness(BaseModel):
    latest_timestamp: str | None = None
    oldest_timestamp: str | None = None
    fresh_item_count: int = 0
    stale_item_count: int = 0
    cache_hit_count: int = 0
    live_item_count: int = 0
    synthetic_item_count: int = 0
    cache_state: str = "miss"
    cache_hit: bool = False
    cache_miss: bool = True
    cache_key: str | None = None
    cached_at: str | None = None
    expires_at: str | None = None
    age_seconds: float | None = None
    ttl_seconds: int | None = None
    stale: bool = False
    stale_reason: str | None = None
    served_stale: bool = False


class ProviderResult(BaseModel):
    provider: str
    source: str
    mode: str
    is_fallback: bool = False
    is_live: bool = False
    is_cached: bool = False
    generated_at: str
    fetched_at: str | None = None
    expires_at: str | None = None
    latency_ms: float = 0
    status: ProviderStatusValue
    evidence: List[EvidenceItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[dict[str, str]] = Field(default_factory=list)
    cache_key: str | None = None
    cache_hit: bool = False
    cache_miss: bool = True
    cached_at: str | None = None
    age_seconds: float | None = None
    ttl_seconds: int | None = None
    stale: bool = False
    stale_reason: str | None = None
    served_stale: bool = False


class ProviderHealth(BaseModel):
    name: str
    enabled: bool
    configured: bool
    supports_live: bool
    status: ProviderStatusValue
    last_success: str | None = None
    last_error_code: str | None = None
    mode_behavior: str


class ProviderRuntimeMetrics(BaseModel):
    provider_name: str
    enabled: bool
    configured: bool
    supports_live: bool
    status: str
    last_success_at: str | None = None
    last_failure_at: str | None = None
    last_error_code: str | None = None
    last_error_message_redacted: str | None = None
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    average_latency_ms: float = 0
    last_latency_ms: float = 0
    circuit_state: CircuitState = "closed"
    circuit_opened_at: str | None = None
    last_result_source: str | None = None
    last_result_count: int = 0
    last_fallback_used: bool = False


class IngestionRun(BaseModel):
    run_id: str
    started_at: str
    finished_at: str | None = None
    duration_ms: float = 0
    symbols_requested: List[str]
    symbols_succeeded: List[str] = Field(default_factory=list)
    symbols_failed: List[str] = Field(default_factory=list)
    provider_results_summary: dict[str, int] = Field(default_factory=dict)
    cache_updates: int = 0
    fallback_count: int = 0
    status: str = "running"
    errors: List[dict[str, str]] = Field(default_factory=list)


class EvidenceBundle(BaseModel):
    symbol: str
    items: List[EvidenceItem]
    provider_results: List[ProviderResult]
    freshness_summary: EvidenceFreshness
    source_mix: dict[str, int]
    reliability: List[SourceReliability]
    warnings: List[str]
    meta: ProvenanceMeta


class NarrativeCluster(BaseModel):
    id: str
    title: str
    strength: float = Field(..., ge=0, le=1)
    sentiment: SentimentLabel
    evidence_count: int = Field(..., ge=0)
    keywords: List[str]
    representative_evidence: str
    trend_direction: TrendDirection


class BeliefExplanation(BaseModel):
    summary: str
    drivers: List[str]
    warnings: List[str]


class BeliefDelta(BaseModel):
    symbol: str
    previous_score: int = Field(..., ge=0, le=100)
    current_score: int = Field(..., ge=0, le=100)
    delta: int
    changed_metrics: dict[str, float]
    reason: str


class BeliefHistoryPoint(BaseModel):
    timestamp: str
    score: int = Field(..., ge=0, le=100)
    velocity: float = Field(..., ge=-100, le=100)
    coherence: float = Field(..., ge=0, le=1)
    fragility: float = Field(..., ge=0, le=1)


class BeliefSnapshot(BaseModel):
    asset: BeliefAsset
    belief: BeliefScore
    breakdown: SignalBreakdown
    signals: List[BeliefSignal]
    narratives: List[NarrativeCluster]
    evidence: List[EvidenceItem]
    evidence_bundle: EvidenceBundle | None = None
    source_mix: dict[str, int] = Field(default_factory=dict)
    freshness_summary: EvidenceFreshness | None = None
    provider_results: List[ProviderResult] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    explanation: BeliefExplanation
    delta: BeliefDelta
    meta: ProvenanceMeta


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    data: T
    meta: ProvenanceMeta
