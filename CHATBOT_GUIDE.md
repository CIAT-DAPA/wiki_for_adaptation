# AI Chatbot Guide (TrackAdapt Wiki)

An AI assistant that answers questions about the wiki content, grounded strictly
in published pages and always returning citation links back to the source.

Built as a lightweight RAG (Retrieval-Augmented Generation) pipeline inside the
Django project — no third-party SaaS widget, no vector database extension.

---

## 1. How it works

Each question triggers **two** Gemini API calls:

1. **Embed the question** (`gemini-embedding-001`)
2. **Generate the answer** (`gemini-flash-lite-latest`) using only the retrieved content

Retrieval happens locally: every content chunk's embedding is stored as a JSON
float array in the `ChatChunk` table, and cosine similarity is computed in pure
Python at query time. Because the corpus is small and curated, this needs **no
`pgvector`, no numpy, and no external vector store**, and behaves identically on
SQLite (dev) and PostgreSQL (prod).

### Components

| Path | Purpose |
|---|---|
| `chatbot/models.py` | `ChatChunk` — one content chunk + its embedding + citation metadata |
| `chatbot/gemini.py` | Thin REST client for Gemini (`embed_text`, `generate_answer`) |
| `chatbot/indexer.py` | Turns wiki pages into text chunks (shared by full and incremental indexing) |
| `chatbot/indexing.py` | Incremental reindex/removal for a single page |
| `chatbot/signals.py` | Wagtail signal receivers that keep the index in sync |
| `chatbot/retrieval.py` | Cosine-similarity search over stored embeddings |
| `chatbot/views.py` | `/chat/ask/` endpoint: rate limit → cache → retrieve → generate |
| `chatbot/templates/chatbot/widget.html` | Floating chat widget (included from `base.html`) |
| `chatbot/management/commands/build_chat_index.py` | Full index rebuild |

### What content gets indexed

Only **live (published)** pages:

- **Catalog**: `IndicatorPage`, `MetricPage`, `MethodPage`, `SOPPage` (all rich-text fields)
- **Static**: `FAQPage` (per question/answer), `AboutPage`, `WikiInstructionsPage`,
  `TrackingFrameworkPage`, `GuidancePage`

Methods and SOPs render inline on their parent Metric page, so their citations
point at the parent URL with an anchor (`/metric-x/#method-slug`).

### Anti-hallucination design

This is a scientific platform, so grounding is enforced deliberately:

- The system prompt instructs the model to answer **only** from the retrieved context
- If the answer isn't in the context, it must say it couldn't find it in the wiki
- **Citation links are built by the backend**, not by the model — so sources are always real
- `temperature` is 0.2 and `maxOutputTokens` is 800

---

## 2. Configuration

All settings live in `mysite/settings/base.py` and can be overridden via `.env`:

| Setting | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | *(empty)* | Free key from https://aistudio.google.com/apikey |
| `GEMINI_EMBED_MODEL` | `gemini-embedding-001` | Embedding model |
| `GEMINI_CHAT_MODEL` | `gemini-flash-lite-latest` | Generation model |
| `CHATBOT_TOP_K` | `6` | Chunks retrieved per question |
| `CHATBOT_RATE_LIMIT_PER_MIN` | `10` | Max questions per session per minute |
| `CHATBOT_RATE_LIMIT_PER_DAY` | `100` | Max questions per session per day |
| `CHATBOT_CACHE_SECONDS` | `3600` | How long identical answers are cached |
| `CHATBOT_AUTO_INDEX` | `true` | Auto-reindex on publish/unpublish/delete |

Without `GEMINI_API_KEY` the endpoint returns HTTP 503 and the widget shows a
"not configured" message — the rest of the site is unaffected.

### Model names change — verify before assuming

Google retires models and free-tier allowances differ per model. Two failures
already hit this project:

- `text-embedding-004` → **404** (not available for this key)
- `gemini-2.0-flash` → **429** with `generate_content_free_tier_requests, limit: 0`
- `gemini-2.5-flash*` → **404** "no longer available to new users"

To list what a key actually supports:

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY"
```

Look for models whose `supportedGenerationMethods` include `embedContent` or
`generateContent`, then test one real call — availability does not guarantee quota.
Prefer `*-latest` aliases so Google's retirements don't break the site.

---

## 3. Local development

```bash
# 1. Add GEMINI_API_KEY to the repo-root .env
# 2. Create the ChatChunk table
env/Scripts/python.exe src/mysite/manage.py migrate

# 3. Build the index (one embedding call per chunk)
env/Scripts/python.exe src/mysite/manage.py build_chat_index

# 4. Run
env/Scripts/python.exe src/mysite/manage.py runserver 127.0.0.1:8000
```

Preview what would be indexed without spending any API quota:

```bash
env/Scripts/python.exe src/mysite/manage.py build_chat_index --dry-run
```

The dev database is PostgreSQL in Docker. The container **must publish port 5432
to the host**, otherwise Django fails with `connection refused`:

```bash
docker run -d --name wiki_db -p 5432:5432 -v wiki_db_vol:/var/lib/postgresql/data \
  -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=adminpass \
  -e POSTGRES_DB=wiki_for_adaptation_db backup_wiki_db
```

A container showing `5432/tcp` (instead of `0.0.0.0:5432->5432/tcp`) in
`docker ps` is exposed only inside Docker's network and will not accept
connections from the host.

---

## 4. Keeping the index fresh

**Automatic (default).** `chatbot/signals.py` hooks Wagtail's signals:

- `page_published` → re-embeds **only that page's** chunks
- `page_unpublished` / `post_delete` → removes that page's chunks

Indexing errors are logged and swallowed, so a Gemini outage or a missing API
key can never block an editor from publishing.

**Manual full rebuild** — needed after bulk imports, after changing the
embedding model, or if the index drifts:

```bash
env/Scripts/python.exe src/mysite/manage.py build_chat_index
```

> Changing `GEMINI_EMBED_MODEL` **requires a full rebuild**: documents and
> questions must be embedded by the same model, or similarity scores are
> meaningless. Changing `GEMINI_CHAT_MODEL` does not.

For bulk imports, set `CHATBOT_AUTO_INDEX=false` to avoid one API call per page,
then run a single full rebuild afterwards.

---

## 5. Production deployment notes

### ⚠️ Use a shared cache (important)

Django's default cache is `LocMemCache`, which is **per-process**. Production
runs multiple Gunicorn workers, so with the default:

- rate limits are enforced *per worker* (N workers ⇒ N× the intended limit)
- the answer cache is duplicated per worker, wasting API quota

Configure a shared cache in `mysite/settings/production.py`. The database cache
needs no extra infrastructure:

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache_table",
    }
}
```

Then create the table once:

```bash
python manage.py createcachetable
```

Redis is preferable if it's already available (`django.core.cache.backends.redis.RedisCache`).

Note this also affects the existing `home_stats_v1` cache in `home/models.py`.

### Quota and cost

The free tier has both per-minute and per-day limits. For a low-traffic wiki it
is sufficient, especially with the answer cache. Watch usage at
https://ai.dev/rate-limit.

If traffic grows, enable pay-as-you-go billing — the `flash-lite` models cost a
small fraction of a cent per answer, and the free-tier ceilings disappear.

Levers to reduce consumption, in order of impact:

1. Answer cache (`CHATBOT_CACHE_SECONDS`) — repeated questions cost nothing
2. Rate limits — stop a single user or bot from draining the daily quota
3. `CHATBOT_TOP_K` — fewer chunks means fewer input tokens per answer
4. Incremental indexing — avoids re-embedding the whole corpus on every edit

### Deployment checklist

1. Add `GEMINI_API_KEY` to the production `.env` (never commit it; keep it
   server-side — it is never exposed to the browser)
2. `python manage.py migrate` (creates the `ChatChunk` table)
3. Configure a shared `CACHES` backend and run `createcachetable` if using the DB
4. `python manage.py build_chat_index` (first-time index build)
5. `python manage.py collectstatic --no-input`
6. Restart Gunicorn

### Security

- The API key stays on the server; the widget only calls the same-origin `/chat/ask/`
- The endpoint is POST-only and CSRF-protected
- Questions are truncated to 500 characters
- Only **published** content is indexed, so drafts are never exposed via the chatbot

---

## 6. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `The chatbot is not configured` (503) | `GEMINI_API_KEY` missing from `.env` |
| `Embedding error 404` | Embedding model unavailable for the key — list models, update `GEMINI_EMBED_MODEL`, then **full rebuild** |
| `Generation error 429` | Free-tier quota exhausted or the model has `limit: 0` — switch `GEMINI_CHAT_MODEL` (e.g. `gemini-flash-lite-latest`) or enable billing |
| `No content found to index` | No **published** pages in the database — the indexer skips drafts |
| Answers ignore recent edits | Page saved as draft (not published), or `CHATBOT_AUTO_INDEX=false` — run a full rebuild |
| Rate limits look too permissive in prod | `LocMemCache` per worker — configure a shared cache (see §5) |
| `connection refused` on port 5432 | Postgres container not publishing the port (see §3) |

---

## 7. Possible next steps

- Move indexing to a background task queue (Celery) so publishing never waits on
  the Gemini call — currently the reindex is synchronous
- Feedback buttons on answers to spot weak retrieval and content gaps
- Log questions (anonymously) to learn what users look for and find content gaps
- Suggested starter questions in the widget
