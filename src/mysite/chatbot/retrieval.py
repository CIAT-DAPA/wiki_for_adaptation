"""
Retrieval over the stored ChatChunk embeddings.

The corpus is small, so we load all chunk vectors and rank them by cosine
similarity in pure Python. No numpy or vector-DB extension required.
"""
from __future__ import annotations

import math

from .gemini import embed_text
from .models import ChatChunk


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def search_chunks(question: str, k: int = 6) -> list[tuple[ChatChunk, float]]:
    """Return the top-k (chunk, score) most similar to the question."""
    query_vec = embed_text(question, task_type="RETRIEVAL_QUERY")
    scored: list[tuple[ChatChunk, float]] = []
    for chunk in ChatChunk.objects.all().iterator():
        try:
            score = _cosine(query_vec, chunk.embedding)
        except Exception:
            continue
        scored.append((chunk, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:k]
