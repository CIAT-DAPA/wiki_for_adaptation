"""
Chatbot API: answer questions grounded in the wiki content.

Flow: embed the question -> retrieve the most similar content chunks ->
ask Gemini to answer using ONLY those chunks -> return the answer plus the
source pages so the widget can render citation links.

To protect the (free-tier) Gemini quota, requests are rate-limited per session
and successful answers are cached, so repeated questions cost no API calls.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import date

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .gemini import GeminiError, generate_answer
from .retrieval import search_chunks


SYSTEM_INSTRUCTION = (
    "You are the assistant for the TrackAdapt Wiki, a knowledge base about "
    "climate change adaptation indicators, metrics, methods and standard "
    "operating procedures (SOPs). Answer the user's question using ONLY the "
    "context provided below, which is extracted from the wiki. "
    "If the answer is not contained in the context, say clearly that you "
    "could not find it in the wiki and suggest browsing or searching the site. "
    "Never invent facts, methods, numbers, or references. Be concise and "
    "practical. Always answer in the same language as the user's question."
)

MAX_QUESTION_LEN = 500


# ---------------------------------------------------------------------------
# Quota protection: rate limiting + answer cache
# ---------------------------------------------------------------------------

def _client_id(request) -> str:
    """Stable identifier for rate limiting: session key, else client IP."""
    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key
    if session_key:
        return f"s:{session_key}"
    return "ip:" + request.META.get("REMOTE_ADDR", "unknown")


def _hit(bucket_key: str, ttl: int) -> int:
    """Atomically increment a counter bucket, creating it with the given TTL."""
    cache.add(bucket_key, 0, ttl)
    try:
        return cache.incr(bucket_key)
    except ValueError:
        # Key expired between add and incr; start a fresh window.
        cache.set(bucket_key, 1, ttl)
        return 1


def _rate_limit_message(request):
    """Return a message if the client is over a limit, else None."""
    ident = _client_id(request)
    per_min = getattr(settings, "CHATBOT_RATE_LIMIT_PER_MIN", 10)
    per_day = getattr(settings, "CHATBOT_RATE_LIMIT_PER_DAY", 100)

    minute = int(time.time() // 60)
    if _hit(f"chat_rl_min:{ident}:{minute}", 60) > per_min:
        return "You're sending questions too quickly. Please wait a minute and try again."

    today = date.today().isoformat()
    if _hit(f"chat_rl_day:{ident}:{today}", 86400) > per_day:
        return "You've reached today's question limit. Please try again tomorrow."

    return None


def _answer_cache_key(question: str) -> str:
    normalized = " ".join(question.lower().split())
    return "chat_ans:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Retrieval context
# ---------------------------------------------------------------------------

def _build_context(scored_chunks):
    """Return (context_text, sources) from retrieved chunks."""
    context_parts = []
    sources = []
    seen_urls = set()
    for i, (chunk, _score) in enumerate(scored_chunks, start=1):
        context_parts.append(f"[Source {i}: {chunk.title}]\n{chunk.text}")
        key = chunk.url or chunk.title
        if key not in seen_urls:
            seen_urls.add(key)
            sources.append({"title": chunk.title, "url": chunk.url})
    return "\n\n".join(context_parts), sources


@require_POST
def ask(request):
    if not getattr(settings, "GEMINI_API_KEY", ""):
        return JsonResponse(
            {"error": "The chatbot is not configured (missing GEMINI_API_KEY)."},
            status=503,
        )

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request body."}, status=400)

    question = (payload.get("question") or "").strip()
    if not question:
        return JsonResponse({"error": "Please enter a question."}, status=400)
    question = question[:MAX_QUESTION_LEN]

    # Rate limit before doing any work (protects the API quota).
    limit_msg = _rate_limit_message(request)
    if limit_msg:
        return JsonResponse({"error": limit_msg}, status=429)

    # Serve a cached answer for repeated questions (no API calls).
    cache_key = _answer_cache_key(question)
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse(cached)

    try:
        scored = search_chunks(question, k=getattr(settings, "CHATBOT_TOP_K", 6))
    except GeminiError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    if not scored:
        return JsonResponse({
            "answer": "I couldn't find anything in the wiki yet. The content "
                      "index may be empty — try browsing or searching the site.",
            "sources": [],
        })

    context, sources = _build_context(scored)
    prompt = f"Context from the wiki:\n\n{context}\n\nQuestion: {question}"

    try:
        answer = generate_answer(SYSTEM_INSTRUCTION, prompt)
    except GeminiError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    result = {"answer": answer, "sources": sources}
    cache.set(cache_key, result, getattr(settings, "CHATBOT_CACHE_SECONDS", 3600))
    return JsonResponse(result)
