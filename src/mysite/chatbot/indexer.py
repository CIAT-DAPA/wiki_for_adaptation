"""
Extract wiki content into retrievable text chunks.

The corpus is a small, curated wiki, so we simply walk every live page,
turn its fields into plain text sections, and split long sections into
manageable chunks. Each chunk carries the metadata needed to build a
citation link back to the source page.

Both the full rebuild (``iter_chunks``) and the incremental per-page reindex
(``document_for_page``) share the same extraction logic.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Iterable

from django.utils.html import strip_tags


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

_WS = re.compile(r"[ \t\r\f\v]+")
_MULTINL = re.compile(r"\n{3,}")


def html_to_text(value) -> str:
    """Convert a RichText/HTML value (or plain string) to clean plain text."""
    if not value:
        return ""
    text = strip_tags(str(value))
    text = html.unescape(text)
    text = _WS.sub(" ", text)
    text = _MULTINL.sub("\n\n", text)
    return text.strip()


def _split_text(text: str, max_chars: int = 1500) -> list[str]:
    """Split a long text into <= max_chars pieces on whitespace boundaries."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    words = text.split(" ")
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for word in words:
        if length + len(word) + 1 > max_chars and current:
            chunks.append(" ".join(current))
            current, length = [], 0
        current.append(word)
        length += len(word) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------

@dataclass
class Section:
    heading: str
    text: str


@dataclass
class Document:
    page_id: int
    page_type: str
    title: str
    url: str
    sections: list[Section] = field(default_factory=list)


# Rich-text / char fields to index per catalog page type, in reading order.
CATALOG_FIELDS: dict[str, list[tuple[str, str]]] = {
    "IndicatorPage": [
        ("Description", "description"),
        ("Dimension", "dimension"),
        ("Indicator type", "indicator_type"),
    ],
    "MetricPage": [
        ("Description", "description"),
        ("Purpose", "purpose"),
        ("Adaptation tracking function", "adaptation_tracking_function"),
    ],
    "MethodPage": [
        ("Description", "description"),
        ("Resolution", "resolution"),
        ("Advantages", "advantages"),
        ("Limitations", "limitations"),
        ("Use case", "use_case"),
        ("Resources", "resources"),
    ],
    "SOPPage": [
        ("Definition", "definition"),
        ("Data sources", "data_sources"),
        ("Units", "units"),
        ("Frequency", "frequency"),
        ("Geographic scale", "geographic_scale"),
        ("Estimated time", "estimated_time"),
        ("Technical capacity", "technical_capacity"),
        ("Activities and steps", "activities_and_steps"),
        ("Options for enhancing robustness", "options_enhancing_robustness"),
        ("Options for reducing costs", "options_reducing_costs"),
        ("Available tools and code", "available_tools_and_code"),
        ("References", "references"),
        ("Flagship method status", "flagship_method_status"),
    ],
}

# Static (non-catalog) page types handled by _static_document().
STATIC_TYPES = {
    "FAQPage",
    "AboutPage",
    "WikiInstructionsPage",
    "TrackingFrameworkPage",
    "GuidancePage",
}

# StreamField-driven guidance pages, handled generically.
STREAM_BODY_TYPES = {"WikiInstructionsPage", "TrackingFrameworkPage", "GuidancePage"}


def _cite_url(page, page_type: str) -> str:
    """Return the front-end URL to cite for a page.

    Methods and SOPs are rendered inline on their parent Metric page, so we
    cite the parent with an anchor rather than the (redirecting) child URL.
    """
    try:
        if page_type in ("MethodPage", "SOPPage"):
            parent = page.get_parent().specific if page.get_parent() else None
            if parent is not None:
                anchor = "method" if page_type == "MethodPage" else "sop"
                base = parent.get_url() or ""
                return f"{base}#{anchor}-{page.slug}"
        return page.get_url() or ""
    except Exception:
        return ""


def _streamvalue_to_text(stream) -> str:
    """Best-effort plain-text extraction from a Wagtail StreamField value."""
    try:
        from wagtail.rich_text import RichText
    except Exception:  # pragma: no cover
        RichText = ()  # type: ignore

    def walk(value) -> str:
        if value is None:
            return ""
        if RichText and isinstance(value, RichText):
            return html_to_text(value.source)
        if isinstance(value, str):
            return html_to_text(value)
        # StructValue behaves like a dict of sub-values
        items = getattr(value, "items", None)
        if callable(items):
            try:
                return " ".join(walk(v) for _, v in value.items())
            except Exception:
                pass
        if isinstance(value, (list, tuple)):
            return " ".join(walk(v) for v in value)
        return html_to_text(str(value))

    parts: list[str] = []
    try:
        for block in stream:
            parts.append(walk(block.value))
    except Exception:
        return ""
    return "\n".join(p for p in parts if p).strip()


# ---------------------------------------------------------------------------
# Per-page document builders
# ---------------------------------------------------------------------------

def _catalog_document(page, type_name: str) -> Document | None:
    sections: list[Section] = []
    for heading, attr in CATALOG_FIELDS[type_name]:
        text = html_to_text(getattr(page, attr, ""))
        if text:
            sections.append(Section(heading, text))

    # Extra: adaptation-tracking booleans on Metric pages
    if type_name == "MetricPage":
        flags = []
        if getattr(page, "tracks_vulnerability", False):
            flags.append("tracks vulnerability")
        if getattr(page, "tracks_intervention_impacts", False):
            flags.append("assesses intervention impacts")
        if flags:
            sections.append(
                Section("Adaptation tracking", "This metric " + " and ".join(flags) + ".")
            )

    if not sections:
        return None
    return Document(page.id, type_name, page.title, _cite_url(page, type_name), sections)


def _static_document(page, type_name: str) -> Document | None:
    sections: list[Section] = []

    if type_name == "FAQPage":
        try:
            for block in page.body:
                if block.block_type == "faq_item":
                    q = html_to_text(block.value.get("question"))
                    a = html_to_text(block.value.get("answer"))
                    if q or a:
                        sections.append(Section(q or "FAQ", f"Q: {q}\nA: {a}"))
                elif block.block_type == "paragraph":
                    t = html_to_text(block.value)
                    if t:
                        sections.append(Section("FAQ", t))
        except Exception:
            pass

    elif type_name == "AboutPage":
        for heading, attr in [("Introduction", "hero_intro"), ("About", "about_body")]:
            t = html_to_text(getattr(page, attr, ""))
            if t:
                sections.append(Section(heading, t))

    elif type_name in STREAM_BODY_TYPES:
        subtitle = html_to_text(getattr(page, "subtitle", ""))
        if subtitle:
            sections.append(Section("Overview", subtitle))
        body_text = _streamvalue_to_text(getattr(page, "body", []))
        if body_text:
            sections.append(Section(page.title, body_text))

    if not sections:
        return None
    return Document(page.id, type_name, page.title, _cite_url(page, type_name), sections)


def document_for_page(page) -> Document | None:
    """Build the Document for a single page, or None if it isn't indexable.

    Accepts any Page; returns None for unsupported types, drafts and pages
    that are no longer live (so callers can drop their chunks).
    """
    from wagtail.models import Page

    if not isinstance(page, Page):
        return None
    page = page.specific
    if not page.live:
        return None

    type_name = type(page).__name__
    if type_name in CATALOG_FIELDS:
        return _catalog_document(page, type_name)
    if type_name in STATIC_TYPES:
        return _static_document(page, type_name)
    return None


def chunks_from_document(doc: Document) -> Iterable[dict]:
    """Split a Document's sections into indexable chunk dicts."""
    for section in doc.sections:
        for piece in _split_text(section.text):
            yield {
                "page_id": doc.page_id,
                "page_type": doc.page_type,
                "title": doc.title,
                "url": doc.url,
                "heading": section.heading,
                "text": f"{section.heading}: {piece}" if section.heading else piece,
            }


# ---------------------------------------------------------------------------
# Full corpus walk
# ---------------------------------------------------------------------------

def _all_documents() -> Iterable[Document]:
    from catalog.models import IndicatorPage, MetricPage, MethodPage, SOPPage
    from home.models import (
        AboutPage,
        FAQPage,
        WikiInstructionsPage,
        TrackingFrameworkPage,
        GuidancePage,
    )

    catalog_models = [IndicatorPage, MetricPage, MethodPage, SOPPage]
    static_models = [
        FAQPage,
        AboutPage,
        WikiInstructionsPage,
        TrackingFrameworkPage,
        GuidancePage,
    ]

    for model in catalog_models:
        type_name = model.__name__
        for page in model.objects.live().specific():
            doc = _catalog_document(page, type_name)
            if doc:
                yield doc

    for model in static_models:
        type_name = model.__name__
        for page in model.objects.live().specific():
            doc = _static_document(page, type_name)
            if doc:
                yield doc


def iter_chunks() -> Iterable[dict]:
    """Yield indexable chunks across the whole wiki.

    Each chunk dict has: page_id, page_type, title, url, heading, text.
    ``text`` is what gets embedded and later fed to the LLM as context.
    """
    for doc in _all_documents():
        yield from chunks_from_document(doc)
