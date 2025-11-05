from __future__ import annotations

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.search import index
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django.utils import timezone
from django.http import HttpResponseRedirect

class BaseWikiPage(Page):
    """Minimal base page with common Wagtail configuration only."""

    # Keep panels minimal; specific pages will add their own fields
    content_panels = Page.content_panels
    promote_panels = Page.promote_panels

    search_fields = Page.search_fields + [
        index.AutocompleteField("title"),
    ]

    class Meta:
        abstract = True


class IndicatorPage(BaseWikiPage):
    parent_page_types = ["home.HomePage"]
    subpage_types = ["catalog.MetricPage"]

    template = "catalog/indicator_page.html"

    # High Level Indicator fields
    description = RichTextField(features=["h2", "h3", "bold", "italic", "ol", "ul", "link"], blank=True)
    dimension = models.CharField(max_length=150, blank=True)
    indicator_type = models.CharField(max_length=150, blank=True)
    entry_author = models.CharField(max_length=255, blank=True)

    content_panels = BaseWikiPage.content_panels + [
        FieldPanel("description"),
        FieldPanel("dimension"),
        FieldPanel("indicator_type"),
    ]

    promote_panels = Page.promote_panels + [
        MultiFieldPanel([FieldPanel("entry_author")], heading="Metadata"),
    ]

    search_fields = BaseWikiPage.search_fields + [
        index.SearchField("description"),
    ]

    def clean(self):
        super().clean()
        # Limit to max 3 children operational indicators per requirement RF03
        if self.pk:
            existing = self.get_children().live().count()
            # When creating via admin, children aren't created yet; enforce in child clean too
            if existing > 3:
                raise ValidationError({"title": _("An Indicator can only have up to 3 Operational Indicators.")})

    class Meta:
        verbose_name = "Indicator"
        verbose_name_plural = "Indicators"


class MetricPage(BaseWikiPage):
    """
    Metric page (formerly Operational Indicator).
    Now hosts one or more Method pages which in turn contain SOPs.
    """
    parent_page_types = ["catalog.IndicatorPage"]
    subpage_types = ["catalog.MethodPage", "catalog.SOPPage"]

    # Metric-specific attributes
    description = RichTextField(features=["h2", "h3", "bold", "italic", "ol", "ul", "link"], blank=True)
    purpose = RichTextField(features=["h2", "h3", "bold", "italic", "ol", "ul", "link"], blank=True)
    entry_author = models.CharField(max_length=255, blank=True)

    content_panels = BaseWikiPage.content_panels + [
        FieldPanel("description"),
        FieldPanel("purpose"),
    ]

    promote_panels = Page.promote_panels + [
        MultiFieldPanel([FieldPanel("entry_author")], heading="Metadata"),
    ]

    search_fields = BaseWikiPage.search_fields + [
        index.SearchField("description"),
    ]

    template = "catalog/metric_page.html"

    def clean(self):
        super().clean()
        # Ensure parent exists and enforce max children on parent
        if self.get_parent() and isinstance(self.get_parent().specific, IndicatorPage):
            parent = self.get_parent().specific
            # If creating new (no pk) include pending addition; else count children excluding self
            count = parent.get_children().type(MetricPage).count()
            if not self.pk:
                count += 1
            if count > 3:
                raise ValidationError({"title": _("Each Indicator can only have up to 3 Metrics.")})

    class Meta:
        verbose_name = "Metric"
        verbose_name_plural = "Metrics"


class MethodPage(BaseWikiPage):
    """Method section within a Metric; holds SOP children."""
    parent_page_types = ["catalog.MetricPage"]
    subpage_types = []

    # Method-specific fields
    description = RichTextField(features=["h2", "h3", "bold", "italic", "ol", "ul", "link"], blank=True)
    resolution = models.CharField(max_length=150, blank=True)
    advantages = RichTextField(blank=True)
    limitations = RichTextField(blank=True)
    use_case = RichTextField(blank=True)

    content_panels = BaseWikiPage.content_panels + [
        FieldPanel("description"),
        FieldPanel("resolution"),
        FieldPanel("advantages"),
        FieldPanel("limitations"),
        FieldPanel("use_case"),
    ]

    search_fields = BaseWikiPage.search_fields + [
        index.SearchField("description"),
    ]

    template = "catalog/method_page.html"

    def clean(self):
        super().clean()
        # No explicit limit on methods per metric for now
        pass

    def serve(self, request):
        """
        Display Methods inline on the parent Metric page.
        If a Method URL is accessed directly, redirect to the parent Metric
        with an anchor to this method section.
        """
        parent = self.get_parent().specific if self.get_parent() else None
        if parent:
            return HttpResponseRedirect(f"{parent.url}#method-{self.slug}")
        return super().serve(request)

    class Meta:
        verbose_name = "Method"
        verbose_name_plural = "Methods"


class SOPPage(BaseWikiPage):
    parent_page_types = ["catalog.MetricPage"]
    subpage_types: list[str] = []

    # SOP specific fields (new structure)
    definition = RichTextField(blank=True)
    data_sources = RichTextField(blank=True)
    units = models.CharField(max_length=100, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    geographic_scale = models.CharField(max_length=150, blank=True)
    technical_capacity = RichTextField(blank=True)

    activities_and_steps = RichTextField(blank=True)
    options_enhancing_robustness = RichTextField(blank=True)
    options_reducing_costs = RichTextField(blank=True)
    available_tools_and_code = RichTextField(blank=True)
    references = RichTextField(blank=True)
    visual_content = RichTextField(blank=True)
    flagship_method_status = RichTextField(blank=True)

    entry_author = models.CharField(max_length=255, blank=True)

    content_panels = BaseWikiPage.content_panels + [
        FieldPanel("definition"),
        FieldPanel("data_sources"),
        FieldPanel("units"),
        FieldPanel("frequency"),
        FieldPanel("geographic_scale"),
        FieldPanel("technical_capacity"),
        FieldPanel("activities_and_steps"),
        FieldPanel("options_enhancing_robustness"),
        FieldPanel("options_reducing_costs"),
        FieldPanel("available_tools_and_code"),
        FieldPanel("references"),
        FieldPanel("visual_content"),
        FieldPanel("flagship_method_status"),
    ]

    promote_panels = Page.promote_panels + [
        MultiFieldPanel([FieldPanel("entry_author")], heading="Metadata"),
    ]

    template = "catalog/sop_page.html"

    def clean(self):
        super().clean()
        # Enforce max 3 SOPs per metric (SOPs are children of Metric)
        if self.get_parent() and isinstance(self.get_parent().specific, MetricPage):
            parent = self.get_parent().specific
            count = parent.get_children().type(SOPPage).count()
            if not self.pk:
                count += 1
            if count > 3:
                raise ValidationError({"title": _("Each Metric can only have up to 3 SOPs.")})

    class Meta:
        verbose_name = "SOP"
        verbose_name_plural = "SOPs"


class AuditLog(models.Model):
    ACTION_CHOICES = (
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
    )
    entity_type = models.CharField(max_length=100)
    entity_id = models.IntegerField()
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    changed_at = models.DateTimeField(default=timezone.now)
    fields = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-changed_at",)


def _page_to_summary_dict(instance: Page) -> dict:
    # Only include common fields safely
    data = {"title": instance.title}
    data["id"] = instance.id
    data["type"] = instance.specific_class.__name__
    return data


@receiver(post_save, sender=Page)
def log_page_save(sender, instance: Page, created, **kwargs):
    if instance.specific_class in {IndicatorPage, MetricPage, MethodPage, SOPPage}:
        prev_action = "create" if created else "update"
        AuditLog.objects.create(
            entity_type=instance.specific_class.__name__,
            entity_id=instance.id,
            action=prev_action,
            changed_by=getattr(instance, "owner", None),
            fields=_page_to_summary_dict(instance),
        )


@receiver(post_delete, sender=Page)
def log_page_delete(sender, instance: Page, **kwargs):
    if instance.specific_class in {IndicatorPage, MetricPage, MethodPage, SOPPage}:
        AuditLog.objects.create(
            entity_type=instance.specific_class.__name__,
            entity_id=instance.id,
            action="delete",
            changed_by=None,
            fields={"title": instance.title, "id": instance.id},
        )
