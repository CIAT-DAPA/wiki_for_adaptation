"""Helpers to render list-style rich-text tidily.

Editors don't always use the bullet/number toolbar buttons — many just press
Enter between items, producing separate ``<p>`` blocks (or ``<br>`` breaks) that
render as a wall of text. ``render_list`` expands a RichText value to HTML and,
when it is just loose paragraphs/line-breaks, wraps them in a real ``<ul>`` /
``<ol>``. Content that already uses a list is returned untouched.

This lives as plain model-property logic (not a template tag library) so the dev
autoreloader picks up changes without a manual server restart.
"""
from __future__ import annotations

import re

from django.utils.safestring import mark_safe
from wagtail.rich_text import expand_db_html

_PARA_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_LIST_RE = re.compile(r"<(?:ul|ol|li)\b", re.IGNORECASE)
_EMPTY_RE = re.compile(r"^(?:\s|&nbsp;|<br\s*/?>)*$", re.IGNORECASE)


def _items(html: str) -> list[str] | None:
    """Return the items hidden in plain-paragraph content, or None if not list-like."""
    paras = [p.strip() for p in _PARA_RE.findall(html)]
    paras = [p for p in paras if not _EMPTY_RE.match(p)]
    if len(paras) >= 2:
        return paras

    # A single paragraph (or no <p> wrapper) may still hold <br>-separated items.
    inner = paras[0] if paras else html
    parts = [p.strip() for p in _BR_RE.split(inner)]
    parts = [p for p in parts if not _EMPTY_RE.match(p)]
    if len(parts) >= 2:
        return parts

    return None


def render_list(richtext_value, tag: str = "ul"):
    """Expand a RichText value to HTML, turning loose paragraphs into a ``<tag>`` list."""
    if not richtext_value:
        return ""
    html = expand_db_html(richtext_value)

    # Already a real list → leave it alone.
    if _LIST_RE.search(html):
        return mark_safe(html)

    items = _items(html)
    if not items:
        return mark_safe(html)

    body = "".join(f"<li>{item}</li>" for item in items)
    return mark_safe(f"<{tag}>{body}</{tag}>")
