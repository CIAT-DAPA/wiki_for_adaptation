import json

from django.db import models


class ChatChunk(models.Model):
    """
    A single retrievable piece of wiki content plus its embedding vector.

    The corpus is small (a curated wiki), so we store the embedding as JSON
    text and compute cosine similarity in Python at query time. This keeps the
    feature portable across SQLite (dev) and PostgreSQL (prod) with no pgvector
    extension required.
    """

    # Source page metadata (used to build citations back to the wiki)
    page_id = models.IntegerField(db_index=True)
    page_type = models.CharField(max_length=100)
    title = models.CharField(max_length=500)
    url = models.CharField(max_length=1000, blank=True)

    # The text that was embedded, and its vector
    heading = models.CharField(max_length=500, blank=True)
    text = models.TextField()
    embedding_json = models.TextField(help_text="JSON array of floats")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Chat chunk"
        verbose_name_plural = "Chat chunks"

    def __str__(self):
        return f"{self.title} ({self.page_type})"

    @property
    def embedding(self) -> list[float]:
        return json.loads(self.embedding_json)

    @embedding.setter
    def embedding(self, values: list[float]) -> None:
        self.embedding_json = json.dumps([float(v) for v in values])
