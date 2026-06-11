from __future__ import annotations

import hashlib
import random
import re
from datetime import datetime, timedelta, timezone

from app.core.contracts import make_provenance, utc_now_iso
from app.models.schemas import EvidenceItem, EvidenceRequest, ProviderResult
from app.services.providers.base import EvidenceProvider, provider_timer

PROTOTYPE_NOTE = "Synthetic demo evidence for product exploration."

NARRATIVE_RULES = {
    "earnings": ["earnings", "guidance", "margin", "revenue", "profit"],
    "product-news": ["product", "launch", "demand", "orders", "customers", "adoption"],
    "analyst-ratings": ["analyst", "rating", "upgrade", "downgrade", "target"],
    "macro-rates": ["rates", "macro", "inflation", "dollar", "yield"],
    "valuation": ["valuation", "multiple", "expensive", "cheap", "priced"],
    "regulation": ["regulation", "policy", "antitrust", "compliance", "probe"],
    "social-hype": ["viral", "retail", "social", "mentions", "hype"],
    "risk-fear": ["risk", "fear", "selloff", "concern", "fragile", "uncertainty"],
    "technical-momentum": ["breakout", "momentum", "volume", "trend", "support"],
}

POSITIVE_WORDS = {"growth", "beat", "upgrade", "demand", "strong", "improving", "breakout", "momentum", "adoption", "resilient"}
NEGATIVE_WORDS = {"risk", "downgrade", "weak", "selloff", "concern", "uncertainty", "fragile", "expensive", "pressure", "probe"}


def _seed_for(symbol: str, window: str) -> int:
    digest = hashlib.sha256(f"{symbol}:{window}:q-belief-provider-v1".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _rng(symbol: str, window: str) -> random.Random:
    return random.Random(_seed_for(symbol, window))


def _window_start(window: str) -> datetime:
    if window == "latest":
        return datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    try:
        return datetime.fromisoformat(window.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)


def _score_text_sentiment(text: str) -> float:
    tokens = re.findall(r"[a-z]+", text.lower())
    positives = sum(1 for token in tokens if token in POSITIVE_WORDS)
    negatives = sum(1 for token in tokens if token in NEGATIVE_WORDS)
    return max(-1.0, min(1.0, (positives - negatives) / max(positives + negatives, 1)))


class DemoEvidenceProvider(EvidenceProvider):
    name = "internal-demo-generator"
    source_type = "demo"
    supports_live = False

    async def fetch_evidence(self, symbol: str, context: EvidenceRequest) -> ProviderResult:
        with provider_timer() as timer:
            evidence = generate_demo_evidence(symbol, context.window, is_fallback=context.mode != "demo")
        self.last_success = utc_now_iso()
        return ProviderResult(
            provider=self.name,
            source="generated" if context.mode == "demo" else "fallback",
            mode=context.mode,
            is_fallback=context.mode != "demo",
            is_live=False,
            is_cached=False,
            generated_at=utc_now_iso(),
            fetched_at=utc_now_iso(),
            latency_ms=timer.latency_ms,
            status="ok",
            evidence=evidence,
            warnings=[] if context.mode == "demo" else ["Live evidence unavailable; using synthetic demo fallback."],
        )


def generate_demo_evidence(symbol: str, window: str = "latest", *, is_fallback: bool = False) -> list[EvidenceItem]:
    rng = _rng(symbol, window)
    now = _window_start(window)
    selected = rng.sample(list(NARRATIVE_RULES), k=6)
    count = 9 + rng.randint(0, 3)
    source = "fallback" if is_fallback else "generated"
    provenance = make_provenance(
        source=source,
        provider="internal-demo-generator",
        is_fallback=is_fallback,
        notes="Demo-generated evidence for belief-signal analytics; not live market truth.",
        confidence="prototype",
    )

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

    evidence: list[EvidenceItem] = []
    for index in range(count):
        narrative_id = selected[index % len(selected)]
        keywords = rng.sample(NARRATIVE_RULES[narrative_id], k=min(3, len(NARRATIVE_RULES[narrative_id])))
        positive_bias = rng.random() > 0.36
        phrase = rng.choice(positive_phrases if positive_bias else negative_phrases)
        text = (
            f"Synthetic demo signal for {symbol}: {narrative_id.replace('-', ' ')} is associated with "
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
                provider="internal-demo-generator",
                text=text,
                timestamp=(now - timedelta(minutes=17 * index)).isoformat().replace("+00:00", "Z"),
                sentiment=round(sentiment, 3),
                attention_weight=round(rng.uniform(0.42, 0.96), 3),
                reliability_weight=round(rng.uniform(0.34, 0.82), 3),
                matched_keywords=keywords,
                provenance=provenance,
                note=PROTOTYPE_NOTE,
                is_synthetic=True,
                is_live=False,
                is_cached=False,
            )
        )
    return evidence
