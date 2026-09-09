"""
Thin client for Google's Gemini (Generative Language) REST API.

Only two operations are needed: embedding text and generating an answer.
We use plain `requests` (already available via mozilla-django-oidc) to avoid
adding an SDK dependency.

Docs: https://ai.google.dev/api/rest
"""
from __future__ import annotations

import re
import time

import requests
from django.conf import settings

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
TIMEOUT = 30


class GeminiError(RuntimeError):
    pass


def _api_key() -> str:
    key = getattr(settings, "GEMINI_API_KEY", "")
    if not key:
        raise GeminiError(
            "GEMINI_API_KEY is not set. Add it to your .env file to enable the chatbot."
        )
    return key


def _retry_delay_seconds(resp) -> float | None:
    """Parse Google's suggested retry delay (RetryInfo.retryDelay, e.g. "38s")
    from a 429 response body, if present."""
    try:
        details = resp.json().get("error", {}).get("details", [])
    except ValueError:
        return None
    for detail in details:
        delay = detail.get("retryDelay")
        if delay:
            match = re.match(r"([\d.]+)s?$", delay)
            if match:
                return float(match.group(1))
    return None


def _post_with_retries(url: str, payload: dict, *, max_retries: int, error_label: str) -> dict:
    """POST with retry-on-429 (rate limit / quota), honoring Google's suggested
    retry delay when given, else exponential backoff. Raises GeminiError once
    retries are exhausted or on any other failure."""
    delay = 5.0
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, json=payload, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise GeminiError(f"{error_label} request failed: {exc}") from exc

        if resp.status_code == 200:
            return resp.json()

        if resp.status_code == 429 and attempt < max_retries:
            wait = _retry_delay_seconds(resp) or delay
            time.sleep(wait)
            delay = min(delay * 2, 60.0)
            continue

        raise GeminiError(f"{error_label} error {resp.status_code}: {resp.text[:300]}")

    raise GeminiError(f"{error_label} error 429: quota exceeded after {max_retries} retries")


def embed_text(text: str, *, task_type: str = "RETRIEVAL_DOCUMENT", max_retries: int = 5) -> list[float]:
    """Return the embedding vector for a piece of text.

    task_type should be RETRIEVAL_DOCUMENT when indexing and RETRIEVAL_QUERY
    when embedding a user question (improves retrieval quality).

    Retries on 429 (rate limit/quota) since bulk indexing easily bursts past
    the free tier's per-minute limit; a single question from the chat widget
    just costs one extra retry, not a user-visible failure.
    """
    model = getattr(settings, "GEMINI_EMBED_MODEL", "text-embedding-004")
    url = f"{BASE_URL}/models/{model}:embedContent?key={_api_key()}"
    payload = {
        "model": f"models/{model}",
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
    }
    data = _post_with_retries(url, payload, max_retries=max_retries, error_label="Embedding")
    return data["embedding"]["values"]


def generate_answer(system_instruction: str, prompt: str, *, max_retries: int = 2) -> str:
    """Call a Gemini Flash model and return the generated text."""
    model = getattr(settings, "GEMINI_CHAT_MODEL", "gemini-2.0-flash")
    url = f"{BASE_URL}/models/{model}:generateContent?key={_api_key()}"
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 800,
        },
    }
    data = _post_with_retries(url, payload, max_retries=max_retries, error_label="Generation")
    try:
        candidate = data["candidates"][0]
        parts = candidate["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError):
        # Model may have returned no candidate (e.g. safety block)
        raise GeminiError(f"Unexpected Gemini response: {str(data)[:300]}")
