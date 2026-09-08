from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chatbot"
    verbose_name = "AI Chatbot"

    def ready(self):
        # Register the Wagtail signal receivers that keep the index in sync.
        from . import signals  # noqa: F401
