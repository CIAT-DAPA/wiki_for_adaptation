from django.db import models

from wagtail.models import Page


class HomePage(Page):
    def get_context(self, request):
        context = super().get_context(request)
        
        # Import IndicatorPage model
        from catalog.models import IndicatorPage
        
        # Get the latest 3 published indicators
        context['latest_entries'] = IndicatorPage.objects.live().order_by('-first_published_at')[:3]
        
        return context
