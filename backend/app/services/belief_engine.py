from __future__ import annotations

import hashlib
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Iterable

from app.core.config import settings
from app.core.contracts import AppHTTPException, ProvenanceMeta, make_provenance
from app.models.schemas import (
    BeliefAsset,
    BeliefDelta,
    BeliefExplanation,
    BeliefHistoryPoint,
    BeliefMetric,
    BeliefScore,
    BeliefSignal,
    BeliefSnapshot,
    EvidenceBundle,
    EvidenceItem,
    NarrativeCluster,
    SignalBreakdown,
)

PROTOTYPE_NOTE = "Synthetic demo evidence for product exploration."

ASSET_NAMES = {
    "AAPL": "Apple Inc.",
    "AMD": "Advanced Micro Devices",
    "AMZN": "Amazon.com Inc.",
    "COIN": "Coinbase Global Inc.",
    "GOOGL": "Alphabet Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "MARA": "MARA Holdings Inc.",
    "META": "Meta Platforms Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "PLTR": "Palantir Technologies Inc.",
    "SMCI": "Super Micro Computer Inc.",
    "TSLA": "Tesla Inc.",
    "UNH": "UnitedHealth Group Inc.",
    "XOM": "Exxon Mobil Corporation",
}

DEFAULT_BELIEF_UNIVERSE = ["NVDA", "TSLA", "AAPL", "AMD", "MSFT", "META", "AMZN", "GOOGL", "PLTR", "COIN"]

NARRATIVE_RULES = {
    "earnings": {
        "title": "Earnings and Guidance",
        "keywords": ["earnings", "guidance", "margin", "revenue", "profit"],
    },
    "product-news": {
        "title": "Product and Business News",
        "keywords": ["product", "launch", "demand", "orders", "customers", "adoption"],
    },
    "analyst-ratings": {
        "title": "Analyst and Ratings Pressure",
        "keywords": ["analyst", "rating", "upgrade", "downgrade", "target"],
    },
    "macro-rates": {
        "title": "Macro and Rates",
        "keywords": ["rates", "macro", "inflation", "dollar", "yield"],
    },
    "valuation": {
        "title": "Valuation Debate",
        "keywords": ["valuation", "multiple", "expensive", "cheap", "priced"],
    },
    "regulation": {
        "title": "Regulation and Policy Risk",
        "keywords": ["regulation", "policy", "antitrust", "compliance", "probe"],
    },
    "social-hype": {
        "title": "Social Attention",
        "keywords": ["viral", "retail", "social", "mentions", "hype"],
    },
    "risk-fear": {
        "title": "Risk and Fear",
        "keywords": ["risk", "fear", "selloff", "concern", "fragile", "uncertainty"],
    },
    "technical-momentum": {
        "title": "Technical Momentum",
        "keywords": ["breakout", "momentum", "volume", "trend", "support"],
    },
}

POSITIVE_WORDS = {
    "growth",
    "beat",
    "upgrade",
    "demand",
    "strong",
    "improving",
    "breakout",
    "momentum",
    "adoption",
    "resilient",
}

NEGATIVE_WORDS = {
    "risk",
    "downgrade",
    "weak",
    "selloff",
    "concern",
    "uncertainty",
    "fragile",
    "expensive",
    "pressure",
    "probe",
}


def validate_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized or len(normalized) > 8 or not re.fullmatch(r"[A-Z0-9.]+", normalized):
        raise AppHTTPException(
            status_code=400,
            code="INVALID_TICKER",
            message="Ticker must be a short alphanumeric symbol.",
            details={"ticker": symbol},
        )
    return normalized


def _seed_for(symbol: str, window: str) -> int:
    digest = hashlib.sha256(f"{symbol}:{window}:q-belief-v2".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _rng(symbol: str, window: str) -> random.Random:
    return random.Random(_seed_for(symbol, window))


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _bounded_ratio(value: float) -> float:
    return round(_clamp(value, 0.0, 1.0), 3)


def _sentiment_label(score: float) -> str:
    if score > 0.18:
        return "positive"
    if score < -0.18:
        return "negative"
    if abs(score) <= 0.08:
        return "neutral"
    return "mixed"


def _score_text_sentiment(text: str) -> float:
    tokens = re.findall(r"[a-z]+", text.lower())
    if not tokens:
        return 0.0
    positives = sum(1 for token in tokens if token in POSITIVE_WORDS)
    negatives = sum(1 for token in tokens if token in NEGATIVE_WORDS)
    raw = (positives - negatives) / max(positives + negatives, 1)
    return max(-1.0, min(1.0, raw))


def _evidence_provenance() -> ProvenanceMeta:
    source = "generated"
    is_fallback = False
    notes = "Demo-generated evidence for belief-signal analytics; not live market truth."
    if settings.DATA_MODE in {"hybrid", "live"}:
        source = "fallback"
        is_fallback = True
        notes = "Prototype belief evidence is generated because live evidence aggregation is not connected."
    return make_provenance(
        source=source,
        provider="internal-demo-generator",
        is_fallback=is_fallback,
        notes=notes,
        confidence="prototype",
    )


def _snapshot_provenance() -> ProvenanceMeta:
    source = "generated"
    is_fallback = False
    notes = "Belief scores are deterministic prototype analytics derived from synthetic demo evidence."
    if settings.DATA_MODE in {"hybrid", "live"}:
        source = "fallback"
        is_fallback = True
        notes = "Belief engine returned generated prototype analytics because live evidence providers are not connected."
    return make_provenance(
        source=source,
        provider="belief-engine-v1",
        is_fallback=is_fallback,
        notes=notes,
        confidence="prototype",
    )


def _window_start(window: str) -> datetime:
    if window == "latest":
        return datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    try:
        return datetime.fromisoformat(window.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)


def generate_demo_evidence(symbol: str, window: str = "latest") -> list[EvidenceItem]:
    rng = _rng(symbol, window)
    now = _window_start(window)
    narrative_ids = list(NARRATIVE_RULES)
    selected = rng.sample(narrative_ids, k=6)
    count = 9 + rng.randint(0, 3)
    evidence: list[EvidenceItem] = []
    provenance = _evidence_provenance()

    positive_phrases = [
        "strong demand and improving margin discussion",
        "growth momentum supported by resilient customer adoption",
        "analyst upgrade chatter and higher target debate",
        "breakout volume reinforcing technical momentum",
    ]
    negative_phrases = [
        "valuation concern and expensive multiple debate",
        "macro uncertainty creating pressure around guidance",
        "regulation risk and compliance questions",
        "fragile social hype with weak source agreement",
    ]

    for index in range(count):
        narrative_id = selected[index % len(selected)]
        rule = NARRATIVE_RULES[narrative_id]
        keywords = rng.sample(rule["keywords"], k=min(3, len(rule["keywords"])))
        positive_bias = rng.random() > 0.36
        phrase = rng.choice(positive_phrases if positive_bias else negative_phrases)
        text = (
            f"Synthetic demo signal for {symbol}: {rule['title'].lower()} is associated with "
            f"{phrase}; matched keywords include {', '.join(keywords)}."
        )
        sentiment = _score_text_sentiment(text)
        if positive_bias and sentiment <= 0:
            sentiment = round(rng.uniform(0.15, 0.72), 2)
        if not positive_bias and sentiment >= 0:
            sentiment = round(rng.uniform(-0.65, -0.12), 2)

        evidence.append(
            EvidenceItem(
                id=f"{symbol.lower()}-{window.replace(':', '').replace('-', '')}-{index}",
                symbol=symbol,
                source_type=rng.choice(["demo", "social", "market", "analyst", "technical"]),
                source_name="internal-demo-generator",
                text=text,
                timestamp=(now - timedelta(minutes=17 * index)).isoformat().replace("+00:00", "Z"),
                sentiment=round(sentiment, 3),
                attention_weight=round(rng.uniform(0.42, 0.96), 3),
                reliability_weight=round(rng.uniform(0.34, 0.82), 3),
                matched_keywords=keywords,
                provenance=provenance,
                note=PROTOTYPE_NOTE,
            )
        )
    return evidence


def _cluster_evidence(evidence: Iterable[EvidenceItem]) -> list[NarrativeCluster]:
    buckets: dict[str, list[EvidenceItem]] = defaultdict(list)
    for item in evidence:
        text = f"{item.text} {' '.join(item.matched_keywords)}".lower()
        matches = [
            narrative_id
            for narrative_id, rule in NARRATIVE_RULES.items()
            if any(keyword in text for keyword in rule["keywords"])
        ]
        buckets[(matches[0] if matches else "social-hype")].append(item)

    clusters: list[NarrativeCluster] = []
    total_weight = sum(item.attention_weight for items in buckets.values() for item in items) or 1.0
    for narrative_id, items in buckets.items():
        rule = NARRATIVE_RULES[narrative_id]
        weight = sum(item.attention_weight for item in items)
        avg_sentiment = sum(item.sentiment for item in items) / max(len(items), 1)
        keyword_counts = Counter(keyword for item in items for keyword in item.matched_keywords)
        keywords = [keyword for keyword, _ in keyword_counts.most_common(5)] or rule["keywords"][:3]
        direction = "up" if avg_sentiment > 0.15 else "down" if avg_sentiment < -0.15 else "flat"
        clusters.append(
            NarrativeCluster(
                id=narrative_id,
                title=rule["title"],
                strength=_bounded_ratio(weight / total_weight),
                sentiment=_sentiment_label(avg_sentiment),
                evidence_count=len(items),
                keywords=keywords,
                representative_evidence=items[0].text,
                trend_direction=direction,
            )
        )

    return sorted(clusters, key=lambda cluster: cluster.strength, reverse=True)


def _metric_direction(current: float, previous: float) -> str:
    delta = current - previous
    if delta > 2:
        return "up"
    if delta < -2:
        return "down"
    return "flat"


def _compute_metrics(symbol: str, window: str, evidence: list[EvidenceItem]) -> tuple[SignalBreakdown, dict[str, float]]:
    rng = _rng(symbol, f"{window}:metrics")
    evidence_count = len(evidence)
    attention = _clamp(30 + evidence_count * 5 + sum(item.attention_weight for item in evidence) * 3.2)
    avg_sentiment = sum(item.sentiment * item.reliability_weight for item in evidence) / max(sum(item.reliability_weight for item in evidence), 1)
    sentiment = _clamp(50 + avg_sentiment * 45)
    source_count = len({item.source_type for item in evidence})
    source_agreement = _clamp(48 + (source_count * 7) - (sum(abs(item.sentiment - avg_sentiment) for item in evidence) / max(evidence_count, 1)) * 32)
    volatility = _clamp(sum(abs(item.sentiment - avg_sentiment) for item in evidence) / max(evidence_count, 1) * 95 + rng.uniform(4, 14))
    evidence_depth = _clamp(evidence_count * 8 + source_count * 6)
    previous_attention = _clamp(attention + rng.uniform(-18, 12))
    momentum = _clamp(50 + (attention - previous_attention) * 1.4 + avg_sentiment * 18)
    fragility = _clamp(
        18
        + volatility * 0.42
        + max(0, 9 - evidence_count) * 5
        + max(0, 3 - source_count) * 8
        + (100 - source_agreement) * 0.18
        + (22 if settings.DATA_MODE != "demo" else 0)
    )

    breakdown = SignalBreakdown(
        attention=round(attention, 2),
        sentiment=round(sentiment, 2),
        momentum=round(momentum, 2),
        source_agreement=round(source_agreement, 2),
        volatility=round(volatility, 2),
        evidence_depth=round(evidence_depth, 2),
    )
    derived = {
        "avg_sentiment": round(avg_sentiment, 3),
        "fragility": round(fragility, 2),
        "previous_attention": round(previous_attention, 2),
    }
    return breakdown, derived


def _belief_label(score: int, sentiment_score: float) -> str:
    tone = "Positive" if sentiment_score >= 58 else "Negative" if sentiment_score <= 42 else "Mixed"
    if score >= 75:
        return f"Strong {tone} Attention"
    if score >= 60:
        return f"Moderate {tone} Attention"
    if score >= 45:
        return f"Emerging {tone} Attention"
    return f"Weak {tone} Attention"


def _build_explanation(
    symbol: str,
    score: int,
    breakdown: SignalBreakdown,
    belief: BeliefScore,
    narratives: list[NarrativeCluster],
    evidence: list[EvidenceItem],
) -> BeliefExplanation:
    strongest = narratives[0] if narratives else None
    summary = (
        f"{symbol} shows {belief.label.lower()} with velocity {belief.velocity:+.1f}, "
        f"coherence {belief.coherence:.2f}, and fragility {belief.fragility:.2f}."
    )
    drivers: list[str] = []
    if breakdown.attention >= 70:
        drivers.append(f"Attention is high at {breakdown.attention:.0f}/100 because the demo evidence set has broad signal volume.")
    else:
        drivers.append(f"Attention is moderate at {breakdown.attention:.0f}/100, so the score is not purely volume-driven.")

    if breakdown.sentiment >= 58:
        drivers.append(f"Sentiment contributes positively at {breakdown.sentiment:.0f}/100 across weighted evidence.")
    elif breakdown.sentiment <= 42:
        drivers.append(f"Sentiment is a drag at {breakdown.sentiment:.0f}/100 because negative evidence carries meaningful weight.")
    else:
        drivers.append(f"Sentiment is mixed at {breakdown.sentiment:.0f}/100, which limits conviction.")

    if strongest:
        drivers.append(
            f"The strongest narrative cluster is '{strongest.title}' with {strongest.evidence_count} evidence item(s)."
        )

    if belief.coherence >= 0.7:
        drivers.append("Narrative coherence is relatively high because signals point in similar directions.")
    elif belief.coherence < 0.45:
        drivers.append("Narrative coherence is low because evidence is fragmented across competing themes.")

    warnings = [
        "This is not financial advice; scores are interpretive belief signals, not buy/sell recommendations.",
    ]
    if any(item.source_name == "internal-demo-generator" for item in evidence):
        warnings.append("Demo-mode evidence is synthetic and should not be treated as live market truth.")
    if belief.fragility >= 0.55:
        warnings.append("Fragility is elevated, so the belief signal may be sensitive to new evidence.")
    if breakdown.source_agreement < 55:
        warnings.append("Source agreement is limited, indicating a less stable narrative base.")

    return BeliefExplanation(summary=summary, drivers=drivers, warnings=warnings)


def build_belief_snapshot(symbol: str, window: str = "latest", evidence_bundle: EvidenceBundle | None = None) -> BeliefSnapshot:
    normalized = validate_symbol(symbol)
    evidence = evidence_bundle.items if evidence_bundle else generate_demo_evidence(normalized, window)
    narratives = _cluster_evidence(evidence)
    breakdown, derived = _compute_metrics(normalized, window, evidence)
    fragility_score = derived["fragility"]
    coherence = _bounded_ratio((breakdown.source_agreement * 0.65 + (100 - breakdown.volatility) * 0.35) / 100)
    fragility = _bounded_ratio(fragility_score / 100)
    velocity = round(breakdown.momentum - 50, 2)
    score = int(
        round(
            _clamp(
                breakdown.attention * 0.24
                + breakdown.sentiment * 0.24
                + breakdown.momentum * 0.18
                + breakdown.source_agreement * 0.18
                + (100 - fragility_score) * 0.16
            )
        )
    )
    previous_score = int(round(_clamp(score - velocity * 0.35 + (_rng(normalized, f"{window}:delta").uniform(-4, 4)))))
    delta_value = score - previous_score
    belief = BeliefScore(
        score=score,
        label=_belief_label(score, breakdown.sentiment),
        velocity=velocity,
        coherence=coherence,
        fragility=fragility,
        confidence="prototype",
    )
    signals = [
        BeliefSignal(
            name="Attention",
            score=breakdown.attention,
            direction=_metric_direction(breakdown.attention, derived["previous_attention"]),
            description="Volume and intensity of available belief evidence.",
        ),
        BeliefSignal(
            name="Sentiment",
            score=breakdown.sentiment,
            direction="up" if breakdown.sentiment > 55 else "down" if breakdown.sentiment < 45 else "flat",
            description="Weighted tone of the evidence set.",
        ),
        BeliefSignal(
            name="Narrative Coherence",
            score=round(coherence * 100, 2),
            direction="up" if coherence >= 0.6 else "down" if coherence < 0.45 else "flat",
            description="How consistently the evidence points to the same market belief.",
        ),
        BeliefSignal(
            name="Fragility",
            score=round(fragility * 100, 2),
            direction="down" if fragility < 0.45 else "up" if fragility > 0.55 else "flat",
            description="Instability risk from sparse, volatile, or concentrated evidence.",
        ),
    ]
    delta = BeliefDelta(
        symbol=normalized,
        previous_score=previous_score,
        current_score=score,
        delta=delta_value,
        changed_metrics={
            "attention": round(breakdown.attention - derived["previous_attention"], 2),
            "sentiment": round(breakdown.sentiment - 50, 2),
            "fragility": round(fragility * 100 - 50, 2),
        },
        reason=(
            "Attention increased while fragility remained controlled."
            if delta_value >= 0
            else "Belief intensity softened as fragility and mixed sentiment weighed on the score."
        ),
    )
    explanation = _build_explanation(normalized, score, breakdown, belief, narratives, evidence)
    if evidence_bundle and evidence_bundle.warnings:
        explanation.warnings = [*explanation.warnings, *evidence_bundle.warnings]
    snapshot_meta = evidence_bundle.meta if evidence_bundle else _snapshot_provenance()
    return BeliefSnapshot(
        asset=BeliefAsset(symbol=normalized, name=ASSET_NAMES.get(normalized, f"{normalized} Corporation")),
        belief=belief,
        breakdown=breakdown,
        signals=signals,
        narratives=narratives,
        evidence=evidence,
        evidence_bundle=evidence_bundle,
        source_mix=evidence_bundle.source_mix if evidence_bundle else {},
        freshness_summary=evidence_bundle.freshness_summary if evidence_bundle else None,
        provider_results=evidence_bundle.provider_results if evidence_bundle else [],
        warnings=evidence_bundle.warnings if evidence_bundle else [],
        explanation=explanation,
        delta=delta,
        meta=snapshot_meta,
    )


async def build_belief_snapshot_async(symbol: str, window: str = "latest") -> BeliefSnapshot:
    from app.services.evidence_pipeline import build_evidence_bundle

    bundle = await build_evidence_bundle(symbol, window=window)
    return build_belief_snapshot(symbol, window=window, evidence_bundle=bundle)


def build_belief_history(symbol: str, days: int = 14) -> list[BeliefHistoryPoint]:
    normalized = validate_symbol(symbol)
    days = int(_clamp(days, 3, 30))
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(days=days - 1)
    points: list[BeliefHistoryPoint] = []
    for offset in range(days):
        stamp = start + timedelta(days=offset)
        snapshot = build_belief_snapshot(normalized, stamp.isoformat().replace("+00:00", "Z"))
        points.append(
            BeliefHistoryPoint(
                timestamp=stamp.isoformat().replace("+00:00", "Z"),
                score=snapshot.belief.score,
                velocity=snapshot.belief.velocity,
                coherence=snapshot.belief.coherence,
                fragility=snapshot.belief.fragility,
            )
        )
    return points


def build_trending_beliefs(limit: int = 8) -> list[BeliefSnapshot]:
    configured = [ticker.strip().upper() for ticker in settings.MARKET_DATA_TICKERS.split(",") if ticker.strip()]
    universe = configured or DEFAULT_BELIEF_UNIVERSE
    snapshots = [build_belief_snapshot(symbol) for symbol in universe[: max(limit * 2, limit)]]
    ranked = sorted(snapshots, key=lambda item: (item.belief.score, abs(item.belief.velocity)), reverse=True)
    return ranked[:limit]
