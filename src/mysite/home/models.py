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
        from catalog.models import IndicatorPage
        
        # Get the latest 3 published indicators
        context['latest_entries'] = IndicatorPage.objects.live().order_by('-first_published_at')[:3]
        
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


class AboutPage(Page):
    """About page with editable rich content."""
    
    subtitle = models.CharField(max_length=255, blank=True, help_text="Subtitle shown below the title")
    body = StreamField(ContentBlock(), use_json_field=True, blank=True)
    
    content_panels = Page.content_panels + [
        FieldPanel('subtitle'),
        FieldPanel('body'),
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
