"""
Incremental indexing: keep a single page's chunks up to date.

Used by the Wagtail signal receivers so editors don't have to run
``build_chat_index`` by hand after every content change.
"""
from __future__ import annotations

import logging

from .gemini import embed_text
from .indexer import chunks_from_document, document_for_page
from .models import ChatChunk

logger = logging.getLogger(__name__)


def remove_page_chunks(page_id: int) -> int:
    """Drop every indexed chunk belonging to a page."""
    deleted, _ = ChatChunk.objects.filter(page_id=page_id).delete()
    return deleted


def reindex_page(page) -> int:
    """Re-embed and replace the chunks for a single page.

    Returns the number of chunks stored. Embedding happens before the old
    rows are deleted, so a failed API call never leaves the page unindexed.
    """
    doc = document_for_page(page)
    if doc is None:
        # Not indexable (unsupported type, draft, or no content) -> drop it.
        remove_page_chunks(page.id)
        return 0

    rows: list[ChatChunk] = []
    for chunk in chunks_from_document(doc):
        row = ChatChunk(
            page_id=chunk["page_id"],
            page_type=chunk["page_type"],
            title=chunk["title"],
            url=chunk["url"],
            heading=chunk["heading"],
            text=chunk["text"],
        )
        row.embedding = embed_text(chunk["text"], task_type="RETRIEVAL_DOCUMENT")
        rows.append(row)

    remove_page_chunks(doc.page_id)
    ChatChunk.objects.bulk_create(rows)
    logger.info("Chatbot: reindexed page %s (%s chunks)", doc.page_id, len(rows))
    return len(rows)
