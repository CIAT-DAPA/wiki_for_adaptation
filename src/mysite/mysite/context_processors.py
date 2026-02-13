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
