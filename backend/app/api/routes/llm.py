from __future__ import annotations

import re
from typing import Any

import aiohttp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import logger
from app.db.repository import get_latest_belief_snapshot, get_watchlist_items, recent_ingestion_runs
from app.db.session import persistence_status
from app.services.belief_engine import build_belief_snapshot_async
from app.services.evidence_pipeline import provider_status_payload

router = APIRouter()

DEFAULT_MODEL = "meta-llama/Meta-Llama-3-8B"
CHAT_MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"
HF_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"


class LLMRequest(BaseModel):
    question: str = Field(min_length=1)
    model: str = DEFAULT_MODEL
    system_prompt: str | None = None


class LLMResponse(BaseModel):
    response: str


KNOWN_TICKERS = {
    "NVDA", "TSLA", "AAPL", "AMD", "MSFT", "META", "AMZN", "GOOGL", "PLTR", "SMCI",
    "COIN", "MARA", "JPM", "UNH", "XOM", "V", "JNJ", "WMT", "PG", "MA",
}


def _find_ticker(question: str) -> str | None:
    matches = re.findall(r"\b[A-Z]{1,5}\b", question.upper())
    return next((token for token in matches if token in KNOWN_TICKERS), None)


async def _belief_context(question: str) -> tuple[str | None, str]:
    ticker = _find_ticker(question)
    if not ticker:
        return None, (
            "No specific ticker was detected. Explain Q-Belief Net as a belief-signal analytics prototype, "
            "and invite the user to ask about a supported ticker."
        )

    snapshot = await build_belief_snapshot_async(ticker)
    top_narratives = ", ".join(cluster.title for cluster in snapshot.narratives[:3]) or "no dominant narrative"
    source_mix = snapshot.source_mix or {}
    freshness = snapshot.freshness_summary
    provider_status = provider_status_payload()
    persisted = get_latest_belief_snapshot(ticker)
    watchlist_symbols = {item.get("symbol") for item in get_watchlist_items()}
    ingestion_runs = recent_ingestion_runs(limit=1)
    persistence = persistence_status()
    context = (
        f"Ticker: {snapshot.asset.symbol} ({snapshot.asset.name})\n"
        f"In local watchlist: {'yes' if ticker in watchlist_symbols else 'no'}\n"
        f"Latest persisted snapshot: {persisted.get('created_at') if persisted else 'none'}\n"
        f"Latest ingestion run: {ingestion_runs[0].get('status') if ingestion_runs else 'none'}\n"
        f"Persistence available: {persistence.get('available')}\n"
        f"Belief score: {snapshot.belief.score}/100 ({snapshot.belief.label})\n"
        f"Velocity: {snapshot.belief.velocity:+.1f}\n"
        f"Coherence: {snapshot.belief.coherence:.2f}\n"
        f"Fragility: {snapshot.belief.fragility:.2f}\n"
        f"Attention: {snapshot.breakdown.attention:.0f}/100\n"
        f"Sentiment: {snapshot.breakdown.sentiment:.0f}/100\n"
        f"Source agreement: {snapshot.breakdown.source_agreement:.0f}/100\n"
        f"Evidence count: {len(snapshot.evidence)}\n"
        f"Source mix: live={source_mix.get('live', 0)}, cached={source_mix.get('cached', 0)}, synthetic={source_mix.get('synthetic', 0)}, fallback={source_mix.get('fallback', 0)}\n"
        f"Freshness: latest={freshness.latest_timestamp if freshness else 'unknown'}, fresh_items={freshness.fresh_item_count if freshness else 0}\n"
        f"Provider health: {provider_status.get('health_summary', {})}\n"
        f"Cache: {provider_status.get('evidence_cache', {})}\n"
        f"Top narrative clusters: {top_narratives}\n"
        f"Provenance: {snapshot.meta.source}, mode={snapshot.meta.mode}, provider={snapshot.meta.provider}\n"
        "The evidence is synthetic demo evidence unless a future live provider is connected."
    )
    return ticker, context


async def _local_belief_answer(question: str) -> str:
    ticker, context = await _belief_context(question)
    if not ticker:
        return (
            "Q-Belief Net analyzes market belief signals such as attention, sentiment, narrative coherence, "
            "velocity, fragility, and evidence provenance. Ask about a ticker like NVDA or AAPL to inspect a "
            "belief snapshot. This is not financial advice."
        )

    snapshot = await build_belief_snapshot_async(ticker)
    narrative = snapshot.narratives[0].title if snapshot.narratives else "no dominant narrative"
    source_mix = snapshot.source_mix or {}
    freshness = snapshot.freshness_summary
    provider_status = provider_status_payload()
    persisted = get_latest_belief_snapshot(ticker)
    watchlist_symbols = {item.get("symbol") for item in get_watchlist_items()}
    ingestion_runs = recent_ingestion_runs(limit=1)
    persistence = persistence_status()
    return (
        f"{ticker} currently shows {snapshot.belief.label.lower()} in demo mode, with a belief score of "
        f"{snapshot.belief.score}/100, velocity {snapshot.belief.velocity:+.1f}, coherence "
        f"{snapshot.belief.coherence:.2f}, and fragility {snapshot.belief.fragility:.2f}. "
        f"The main narrative cluster is {narrative}. The score is driven by attention "
        f"({snapshot.breakdown.attention:.0f}/100), sentiment ({snapshot.breakdown.sentiment:.0f}/100), "
        f"and source agreement ({snapshot.breakdown.source_agreement:.0f}/100) across "
        f"{len(snapshot.evidence)} evidence items. Source mix: {source_mix.get('live', 0)} live, "
        f"{source_mix.get('cached', 0)} cached, {source_mix.get('synthetic', 0)} synthetic, "
        f"{source_mix.get('fallback', 0)} fallback. Latest evidence timestamp: "
        f"{freshness.latest_timestamp if freshness else 'unknown'}. "
        f"{ticker} is {'in' if ticker in watchlist_symbols else 'not in'} your local watchlist. "
        f"Latest persisted snapshot: {persisted.get('created_at') if persisted else 'none'}. "
        f"Latest ingestion run: {ingestion_runs[0].get('status') if ingestion_runs else 'none'}. "
        f"Persistence available: {persistence.get('available')}. {snapshot.explanation.warnings[0]} "
        f"Provider health summary: {provider_status.get('health_summary', {})}. "
        "Synthetic evidence is generated for product exploration and is not live market truth. "
        "This is not financial advice."
    )


@router.post("", response_model=LLMResponse)
async def generate_llm_response(payload: LLMRequest) -> LLMResponse:
    api_key = (settings.HF_API_KEY or "").strip()
    if not api_key:
        return LLMResponse(response=await _local_belief_answer(payload.question))

    _, context = await _belief_context(payload.question)
    system_prompt = payload.system_prompt or (
        "You are Q-Belief Net's market-belief assistant. Explain attention, sentiment, velocity, "
        "coherence, fragility, narrative clusters, evidence count, and provenance. Do not provide "
        "financial advice, price predictions, or buy/sell recommendations. Clearly say when data is "
        "demo-generated. Use the internal belief context below when relevant.\n\n"
        f"{context}"
    )
    model = (settings.HF_MODEL_ID or payload.model or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if model == DEFAULT_MODEL:
        model = CHAT_MODEL

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            HF_CHAT_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": payload.question},
                ],
                "max_tokens": 256,
                "temperature": 0.7,
                "top_p": 0.95,
                "stream": False,
            },
        ) as response:
            try:
                data: Any = await response.json()
            except Exception:
                data = {"error": await response.text()}

            if response.status >= 400:
                error_message = data.get("error") if isinstance(data, dict) else None
                logger.warning("Hugging Face chat completion failed: %s", error_message or response.status)
                raise HTTPException(status_code=response.status, detail=error_message or "Hugging Face chat completion failed")

            if isinstance(data, dict):
                choices = data.get("choices")
                if isinstance(choices, list) and choices:
                    choice = choices[0] or {}
                    message = choice.get("message") if isinstance(choice, dict) else None
                    if isinstance(message, dict):
                        content = (message.get("content") or "").strip()
                        if content:
                            return LLMResponse(response=content)

                generated_text = (data.get("generated_text") or "").strip()
                if generated_text:
                    return LLMResponse(response=generated_text)

            return LLMResponse(response="Unable to generate response. Please try again.")


@router.get("/status")
async def llm_status() -> dict[str, bool | str]:
    return {
        "configured": bool(settings.HF_API_KEY),
        "provider": "huggingface",
        "app_mode": settings.APP_MODE,
        "data_mode": settings.DATA_MODE,
        "model": settings.HF_MODEL_ID or "not-configured",
    }
