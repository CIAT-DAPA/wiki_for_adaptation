"""
Thin client for Google's Gemini (Generative Language) REST API.

Only two operations are needed: embedding text and generating an answer.
We use plain `requests` (already available via mozilla-django-oidc) to avoid
adding an SDK dependency.

Docs: https://ai.google.dev/api/rest
"""
from __future__ import annotations

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


def embed_text(text: str, *, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """Return the embedding vector for a piece of text.

    task_type should be RETRIEVAL_DOCUMENT when indexing and RETRIEVAL_QUERY
    when embedding a user question (improves retrieval quality).
    """
    model = getattr(settings, "GEMINI_EMBED_MODEL", "text-embedding-004")
    url = f"{BASE_URL}/models/{model}:embedContent?key={_api_key()}"
    payload = {
        "model": f"models/{model}",
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
    }
    try:
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise GeminiError(f"Embedding request failed: {exc}") from exc
    if resp.status_code != 200:
        raise GeminiError(f"Embedding error {resp.status_code}: {resp.text[:300]}")
    return resp.json()["embedding"]["values"]


def generate_answer(system_instruction: str, prompt: str) -> str:
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
    try:
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise GeminiError(f"Generation request failed: {exc}") from exc
    if resp.status_code != 200:
        raise GeminiError(f"Generation error {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    try:
        candidate = data["candidates"][0]
        parts = candidate["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError):
        # Model may have returned no candidate (e.g. safety block)
        raise GeminiError(f"Unexpected Gemini response: {str(data)[:300]}")
