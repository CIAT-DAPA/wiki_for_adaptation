"""
Keep the chatbot index in sync with Wagtail content changes.

Publishing a page re-embeds just that page; unpublishing or deleting it drops
its chunks. Indexing failures are logged and swallowed so a Gemini outage or a
missing API key can never block an editor from saving content.

Set CHATBOT_AUTO_INDEX = False to disable (e.g. during bulk imports).
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver
from wagtail.models import Page
from wagtail.signals import page_published, page_unpublished

from .indexing import reindex_page, remove_page_chunks

logger = logging.getLogger(__name__)


def _auto_index_enabled() -> bool:
    return bool(getattr(settings, "CHATBOT_AUTO_INDEX", True))


@receiver(page_published)
def chatbot_index_on_publish(sender, instance, **kwargs):
    if not _auto_index_enabled():
        return
    try:
        reindex_page(instance)
    except Exception:
        # Never let indexing break publishing.
        logger.exception("Chatbot: failed to reindex page %s on publish", instance.pk)


@receiver(page_unpublished)
def chatbot_deindex_on_unpublish(sender, instance, **kwargs):
    if not _auto_index_enabled():
        return
    try:
        remove_page_chunks(instance.pk)
    except Exception:
        logger.exception("Chatbot: failed to de-index page %s on unpublish", instance.pk)


@receiver(post_delete)
def chatbot_deindex_on_delete(sender, instance, **kwargs):
    # post_delete fires for every model, so filter to pages cheaply.
    if not isinstance(instance, Page):
        return
    if not _auto_index_enabled():
        return
    try:
        remove_page_chunks(instance.pk)
    except Exception:
        logger.exception("Chatbot: failed to de-index page %s on delete", instance.pk)
