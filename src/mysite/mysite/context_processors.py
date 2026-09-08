"""
Context processors for making settings available in templates.
"""
from django.conf import settings


def google_analytics(request):
    """
    Add Google Analytics ID to template context.
    Example in template: {% if GOOGLE_ANALYTICS_ID %}...{% endif %}
    """
    return {
        'GOOGLE_ANALYTICS_ID': settings.GOOGLE_ANALYTICS_ID,
    }


def chatbot_enabled(request):
    """
    Whether the chatbot widget should be shown. False when GEMINI_API_KEY
    isn't set, so the floating button doesn't appear only to error out when
    clicked (e.g. right after a deploy, before the key is configured).
    """
    return {
        'CHATBOT_ENABLED': bool(settings.GEMINI_API_KEY),
    }
