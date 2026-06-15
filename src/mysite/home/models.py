from django.db import models

from wagtail.models import Page
from wagtail.fields import RichTextField, StreamField
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.images.blocks import ImageChooserBlock


class HomePage(Page):
    def get_context(self, request):
        context = super().get_context(request)
        
        # Import IndicatorPage model
        from django.core.cache import cache
        from catalog.models import IndicatorPage, MetricPage, SOPPage

        # Get the latest 3 published indicators
        context['latest_entries'] = IndicatorPage.objects.live().order_by('-first_published_at')[:3]

        # Automatic statistics counts (cached for 5 minutes)
        cache_key = 'home_stats_v1'
        stats = cache.get(cache_key)
        if not stats:
            stats = {
                'indicator_count': IndicatorPage.objects.live().count(),
                'metric_count': MetricPage.objects.live().count(),
                'sop_count': SOPPage.objects.live().count(),
                'dimension_count': IndicatorPage.objects.live().exclude(dimension='').values_list('dimension', flat=True).distinct().count(),
            }
            cache.set(cache_key, stats, 300)  # 5 minutes

        context['indicator_count'] = stats.get('indicator_count', 0)
        context['metric_count'] = stats.get('metric_count', 0)
        context['sop_count'] = stats.get('sop_count', 0)
        context['dimension_count'] = stats.get('dimension_count', 0)

        # Keyword chips under the hero: real indicators, each linking to its page.
        context['indicator_chips'] = IndicatorPage.objects.live().order_by('title')[:8]

        return context


# Bloques estructurados para componentes comunes
class FeatureCardBlock(blocks.StructBlock):
    """Card highlighting a feature with icon."""
    icon = blocks.ChoiceBlock(choices=[
        ('fa-globe', 'Globe (Global)'),
        ('fa-check-circle', 'Check (Validated)'),
        ('fa-users', 'Users (Community)'),
        ('fa-bullseye', 'Target (Goal)'),
        ('fa-chart-line', 'Chart (Data)'),
        ('fa-leaf', 'Leaf (Environment)'),
        ('fa-shield', 'Shield (Protection)'),
    ], help_text="Select the icon for the card")
    icon_color = blocks.ChoiceBlock(choices=[
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('purple', 'Purple'),
        ('orange', 'Orange'),
        ('red', 'Red'),
    ], default='blue')
    title = blocks.CharBlock(max_length=100, help_text="Feature title")
    description = blocks.TextBlock(help_text="Short description")
    
    class Meta:
        icon = 'placeholder'
        template = 'home/blocks/feature_card.html'


class PartnerBlock(blocks.StructBlock):
    """Information about a partner organization."""
    name = blocks.CharBlock(max_length=100, help_text="Organization name")
    acronym = blocks.CharBlock(max_length=20, help_text="Acronym (e.g. IWMI, ILRI)")
    role = blocks.CharBlock(max_length=100, help_text="Role (e.g. Data Standards & Coordination)")
    description = blocks.TextBlock(help_text="Collaboration description")
    logo_url = blocks.CharBlock(max_length=255, required=False, help_text="Logo path (e.g. images/iwmi_logo.jpg)")
    acronym_color = blocks.ChoiceBlock(choices=[
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('purple', 'Purple'),
        ('orange', 'Orange'),
    ], default='blue')
    
    class Meta:
        icon = 'group'
        template = 'home/blocks/partner.html'


class TeamMemberBlock(blocks.StructBlock):
    """Information about a team member."""
    name = blocks.CharBlock(max_length=100, help_text="Full name")
    role = blocks.CharBlock(max_length=100, help_text="Role/Position")
    description = blocks.TextBlock(help_text="Short biography or specialty")
    initials = blocks.CharBlock(max_length=3, help_text="Initials for avatar (e.g. JD)")
    avatar_color = blocks.ChoiceBlock(choices=[
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('purple', 'Purple'),
        ('orange', 'Orange'),
        ('red', 'Red'),
    ], default='blue')
    
    class Meta:
        icon = 'user'
        template = 'home/blocks/team_member.html'


class SectionBlock(blocks.StructBlock):
    """Section with title and icon."""
    icon = blocks.ChoiceBlock(choices=[
        ('fa-bullseye', 'Target'),
        ('fa-info-circle', 'Info'),
        ('fa-envelope', 'Email'),
        ('fa-users', 'Users'),
    ])
    icon_color = blocks.ChoiceBlock(choices=[
        ('blue', 'Blue'),
        ('green', 'Green'),
        ('purple', 'Purple'),
    ], default='blue')
    title = blocks.CharBlock(max_length=100)
    content = blocks.RichTextBlock(help_text="Section content")
    background_color = blocks.ChoiceBlock(choices=[
        ('white', 'White'),
        ('blue', 'Light blue'),
        ('gray', 'Light gray'),
    ], default='white')
    
    class Meta:
        icon = 'doc-full'
        template = 'home/blocks/section.html'


class ContentBlock(blocks.StreamBlock):
    """Reusable and user-friendly content blocks."""
    
    heading = blocks.CharBlock(form_classname="title", icon="title", help_text="Section title")
    paragraph = blocks.RichTextBlock(icon="pilcrow", help_text="Rich formatted text")
    image = ImageChooserBlock(icon="image")
    feature_card = FeatureCardBlock()
    partner = PartnerBlock()
    team_member = TeamMemberBlock()
    section = SectionBlock()
    html = blocks.RawHTMLBlock(icon="code", help_text="⚠️ Advanced: Custom HTML")
    
    class Meta:
        icon = "doc-full"


class AboutFeatureBlock(blocks.StructBlock):
    """A 'Key features' card with a coloured icon."""
    icon = blocks.ChoiceBlock(choices=[
        ('fa-people-group', 'People (Community)'),
        ('fa-globe', 'Globe'),
        ('fa-chart-line', 'Chart'),
        ('fa-leaf', 'Leaf'),
        ('fa-bullseye', 'Target'),
        ('fa-shield', 'Shield'),
        ('fa-circle-check', 'Check'),
    ], default='fa-leaf')
    color = blocks.ChoiceBlock(choices=[
        ('purple', 'Purple'), ('blue', 'Blue'), ('emerald', 'Green'),
        ('orange', 'Orange'), ('rose', 'Rose'),
    ], default='emerald')
    title = blocks.CharBlock(max_length=120)
    description = blocks.TextBlock()

    class Meta:
        icon = 'pick'
        label = 'Feature'


class AboutPartnerBlock(blocks.StructBlock):
    """A partner institution card (clickable to its official site)."""
    name = blocks.CharBlock(max_length=150)
    tag = blocks.CharBlock(max_length=80, required=False, help_text="Small green label, e.g. 'Research & data'")
    description = blocks.TextBlock(required=False)
    logo = ImageChooserBlock(required=False, help_text="Upload a logo (preferred)")
    logo_url = blocks.CharBlock(max_length=255, required=False, help_text="Or a static path, e.g. images/ilri_logo.jpg")
    url = blocks.URLBlock(required=False, help_text="Official website (opens in a new tab)")

    class Meta:
        icon = 'group'
        label = 'Partner'


class AboutTeamBlock(blocks.StructBlock):
    """A team member card with an initials avatar."""
    initials = blocks.CharBlock(max_length=3)
    color = blocks.ChoiceBlock(choices=[
        ('blue', 'Blue'), ('emerald', 'Green'), ('amber', 'Amber'),
        ('purple', 'Purple'), ('rose', 'Rose'),
    ], default='blue')
    name = blocks.CharBlock(max_length=120)
    role = blocks.CharBlock(max_length=120, required=False)
    description = blocks.TextBlock(required=False)

    class Meta:
        icon = 'user'
        label = 'Team member'


class AboutContactBlock(blocks.StructBlock):
    """A 'Get in touch' card with a call-to-action button."""
    icon = blocks.ChoiceBlock(choices=[
        ('fa-envelope', 'Envelope'), ('fa-plus', 'Plus'),
        ('fa-comment', 'Comment'), ('fa-handshake', 'Handshake'),
    ], default='fa-envelope')
    title = blocks.CharBlock(max_length=120)
    description = blocks.TextBlock(required=False)
    button_label = blocks.CharBlock(max_length=60, required=False)
    button_url = blocks.CharBlock(max_length=255, required=False)
    primary = blocks.BooleanBlock(required=False, help_text="Green (filled) button. Leave unchecked for an outline button.")

    class Meta:
        icon = 'mail'
        label = 'Contact card'


class AboutPage(Page):
    """About page — fully editable from the admin without touching HTML."""

    # Hero
    badge_text = models.CharField(max_length=80, blank=True, default="About the project")
    hero_title = models.CharField(max_length=255, default="Built to standardize how adaptation gets measured")
    hero_highlight = models.CharField(
        max_length=80, blank=True, default="standardize",
        help_text="A word within the title shown in green (optional).",
    )
    hero_intro = models.TextField(blank=True)

    # About this project
    about_heading = models.CharField(max_length=120, blank=True, default="About this project")
    about_body = RichTextField(blank=True, features=["bold", "italic", "link", "ol", "ul"])
    about_tags = StreamField([('tag', blocks.CharBlock(label="Tag"))], use_json_field=True, blank=True)

    # Sections
    key_features = StreamField([('feature', AboutFeatureBlock())], use_json_field=True, blank=True)
    partners = StreamField([('partner', AboutPartnerBlock())], use_json_field=True, blank=True)
    team = StreamField([('member', AboutTeamBlock())], use_json_field=True, blank=True)

    # Get in touch
    contact_heading = models.CharField(max_length=120, blank=True, default="Get in touch")
    contact_cards = StreamField([('card', AboutContactBlock())], use_json_field=True, blank=True)

    @property
    def hero_title_html(self):
        """Render the hero title with the highlight word wrapped in a green span."""
        from django.utils.html import escape
        from django.utils.safestring import mark_safe
        title = self.hero_title or ""
        hl = (self.hero_highlight or "").strip()
        if hl and hl in title:
            before, _, after = title.partition(hl)
            return mark_safe(
                f'{escape(before)}<span class="text-brand-green">{escape(hl)}</span>{escape(after)}'
            )
        return escape(title)

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('badge_text'),
            FieldPanel('hero_title'),
            FieldPanel('hero_highlight'),
            FieldPanel('hero_intro'),
        ], heading="Hero"),
        MultiFieldPanel([
            FieldPanel('about_heading'),
            FieldPanel('about_body'),
            FieldPanel('about_tags'),
        ], heading="About this project"),
        FieldPanel('key_features'),
        FieldPanel('partners'),
        FieldPanel('team'),
        MultiFieldPanel([
            FieldPanel('contact_heading'),
            FieldPanel('contact_cards'),
        ], heading="Get in touch"),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]

    max_count = 1  # Only allow one About page

    class Meta:
        verbose_name = "About Page"


class FAQPage(Page):
    """FAQ page with questions and answers."""
    
    subtitle = models.CharField(max_length=255, blank=True, help_text="Subtitle shown below the title")
    
    body = StreamField([
        ('faq_item', blocks.StructBlock([
            ('question', blocks.CharBlock(max_length=255)),
            ('answer', blocks.RichTextBlock()),
        ], icon="help")),
        ('paragraph', blocks.RichTextBlock(icon="pilcrow")),
    ], use_json_field=True, blank=True)
    
    content_panels = Page.content_panels + [
        FieldPanel('subtitle'),
        FieldPanel('body'),
    ]
    
    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]
    
    max_count = 1  # Only allow one FAQ page
    
    class Meta:
        verbose_name = "FAQ Page"


class WikiInstructionsPage(Page):
    """Wiki instructions page with step-by-step guides."""
    
    subtitle = models.CharField(max_length=255, blank=True, help_text="Subtitle shown below the title")
    body = StreamField(ContentBlock(), use_json_field=True, blank=True)
    
    content_panels = Page.content_panels + [
        FieldPanel('subtitle'),
        FieldPanel('body'),
    ]
    
    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]
    
    max_count = 1  # Only allow one Wiki Instructions page
    
    class Meta:
        verbose_name = "Wiki Instructions Page"


class TrackingFrameworkPage(Page):
    """Tracking framework page with guidance content."""
    
    subtitle = models.CharField(max_length=255, blank=True, help_text="Subtitle shown below the title")
    body = StreamField(ContentBlock(), use_json_field=True, blank=True)
    
    content_panels = Page.content_panels + [
        FieldPanel('subtitle'),
        FieldPanel('body'),
    ]
    
    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]
    
    max_count = 1  # Only allow one Tracking Framework page
    
    class Meta:
        verbose_name = "Tracking Framework Page"


class GuidancePage(Page):
    """Guidance pages for impact pathways and other topics."""
    
    subtitle = models.CharField(max_length=255, blank=True, help_text="Subtitle shown below the title")
    body = StreamField(ContentBlock(), use_json_field=True, blank=True)
    
    content_panels = Page.content_panels + [
        FieldPanel('subtitle'),
        FieldPanel('body'),
    ]
    
    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]
    
    class Meta:
        verbose_name = "Guidance Page"
