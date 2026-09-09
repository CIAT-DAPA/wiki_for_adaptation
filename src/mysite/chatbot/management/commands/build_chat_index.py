"""
Rebuild the chatbot's content index.

Walks every live wiki page, splits it into text chunks, embeds each chunk
with Gemini and stores it as a ChatChunk. Run this after content changes:

    python manage.py build_chat_index
"""
from __future__ import annotations

import time

from django.core.management.base import BaseCommand, CommandError

from chatbot.gemini import GeminiError, embed_text
from chatbot.indexer import iter_chunks
from chatbot.models import ChatChunk


class Command(BaseCommand):
    help = "Rebuild the AI chatbot content index (embeds all wiki content)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the chunks that would be indexed without calling Gemini.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        chunks = list(iter_chunks())
        if not chunks:
            self.stdout.write(self.style.WARNING(
                "No content found to index. Have you created any wiki pages?"
            ))
            return

        self.stdout.write(f"Found {len(chunks)} chunks to index.")

        if dry_run:
            for c in chunks:
                self.stdout.write(f"  [{c['page_type']}] {c['title']} — {c['heading']}")
            self.stdout.write(self.style.SUCCESS("Dry run complete (nothing embedded)."))
            return

        # Clear the old index up front and save rows in batches as we go
        # (rather than holding everything in memory until the end), so a run
        # that fails partway through (e.g. the free-tier daily quota runs out)
        # still leaves whatever was successfully embedded searchable, instead
        # of losing all the API calls already spent.
        ChatChunk.objects.all().delete()

        created = 0
        batch: list[ChatChunk] = []
        BATCH_SIZE = 20
        try:
            for i, c in enumerate(chunks, start=1):
                # embed_text already retries on 429 (rate limit), so this only
                # raises for a real failure (bad key, exhausted retries, ...).
                vector = embed_text(c["text"], task_type="RETRIEVAL_DOCUMENT")
                row = ChatChunk(
                    page_id=c["page_id"],
                    page_type=c["page_type"],
                    title=c["title"],
                    url=c["url"],
                    heading=c["heading"],
                    text=c["text"],
                )
                row.embedding = vector
                batch.append(row)
                created += 1
                if len(batch) >= BATCH_SIZE:
                    ChatChunk.objects.bulk_create(batch)
                    batch.clear()
                if i % 10 == 0:
                    self.stdout.write(f"  embedded {i}/{len(chunks)}...")
                # Gentle pacing to stay well within the free-tier rate limits.
                time.sleep(0.3)
        except GeminiError as exc:
            if batch:
                ChatChunk.objects.bulk_create(batch)
            raise CommandError(
                f"{exc}\nIndexed {created}/{len(chunks)} chunks before failing "
                "(already saved — re-run this command later to pick up the rest; "
                "it will re-embed everything from scratch)."
            )

        if batch:
            ChatChunk.objects.bulk_create(batch)

        self.stdout.write(self.style.SUCCESS(
            f"Indexed {created} chunks. The chatbot is ready."
        ))
