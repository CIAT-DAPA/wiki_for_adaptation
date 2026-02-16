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
    """Card destacando una característica con ícono."""
    icon = blocks.ChoiceBlock(choices=[
        ('fa-globe', 'Globo (Global)'),
        ('fa-check-circle', 'Check (Validado)'),
        ('fa-users', 'Usuarios (Comunidad)'),
        ('fa-bullseye', 'Target (Objetivo)'),
        ('fa-chart-line', 'Gráfica (Datos)'),
        ('fa-leaf', 'Hoja (Ambiente)'),
        ('fa-shield', 'Escudo (Protección)'),
    ], help_text="Selecciona el ícono para la tarjeta")
    icon_color = blocks.ChoiceBlock(choices=[
        ('blue', 'Azul'),
        ('green', 'Verde'),
        ('purple', 'Morado'),
        ('orange', 'Naranja'),
        ('red', 'Rojo'),
    ], default='blue')
    title = blocks.CharBlock(max_length=100, help_text="Título de la característica")
    description = blocks.TextBlock(help_text="Descripción breve")
    
    class Meta:
        icon = 'placeholder'
        template = 'home/blocks/feature_card.html'


class PartnerBlock(blocks.StructBlock):
    """Información de una organización socia."""
    name = blocks.CharBlock(max_length=100, help_text="Nombre de la organización")
    acronym = blocks.CharBlock(max_length=20, help_text="Acrónimo (ej: IWMI, ILRI)")
    role = blocks.CharBlock(max_length=100, help_text="Rol (ej: Data Standards & Coordination)")
    description = blocks.TextBlock(help_text="Descripción de la colaboración")
    logo_url = blocks.CharBlock(max_length=255, required=False, help_text="Ruta al logo (ej: images/iwmi_logo.jpg)")
    acronym_color = blocks.ChoiceBlock(choices=[
        ('blue', 'Azul'),
        ('green', 'Verde'),
        ('purple', 'Morado'),
        ('orange', 'Naranja'),
    ], default='blue')
    
    class Meta:
        icon = 'group'
        template = 'home/blocks/partner.html'


class TeamMemberBlock(blocks.StructBlock):
    """Información de un miembro del equipo."""
    name = blocks.CharBlock(max_length=100, help_text="Nombre completo")
    role = blocks.CharBlock(max_length=100, help_text="Rol/Posición")
    description = blocks.TextBlock(help_text="Breve biografía o especialidad")
    initials = blocks.CharBlock(max_length=3, help_text="Iniciales para el avatar (ej: JD)")
    avatar_color = blocks.ChoiceBlock(choices=[
        ('blue', 'Azul'),
        ('green', 'Verde'),
        ('purple', 'Morado'),
        ('orange', 'Naranja'),
        ('red', 'Rojo'),
    ], default='blue')
    
    class Meta:
        icon = 'user'
        template = 'home/blocks/team_member.html'


class SectionBlock(blocks.StructBlock):
    """Sección con título e ícono."""
    icon = blocks.ChoiceBlock(choices=[
        ('fa-bullseye', 'Target'),
        ('fa-info-circle', 'Info'),
        ('fa-envelope', 'Email'),
        ('fa-users', 'Usuarios'),
    ])
    icon_color = blocks.ChoiceBlock(choices=[
        ('blue', 'Azul'),
        ('green', 'Verde'),
        ('purple', 'Morado'),
    ], default='blue')
    title = blocks.CharBlock(max_length=100)
    content = blocks.RichTextBlock(help_text="Contenido de la sección")
    background_color = blocks.ChoiceBlock(choices=[
        ('white', 'Blanco'),
        ('blue', 'Azul claro'),
        ('gray', 'Gris claro'),
    ], default='white')
    
    class Meta:
        icon = 'doc-full'
        template = 'home/blocks/section.html'


class ContentBlock(blocks.StreamBlock):
    """Bloques de contenido reutilizables y amigables."""
    
    heading = blocks.CharBlock(form_classname="title", icon="title", help_text="Título de sección")
    paragraph = blocks.RichTextBlock(icon="pilcrow", help_text="Texto con formato enriquecido")
    image = ImageChooserBlock(icon="image")
    feature_card = FeatureCardBlock()
    partner = PartnerBlock()
    team_member = TeamMemberBlock()
    section = SectionBlock()
    html = blocks.RawHTMLBlock(icon="code", help_text="⚠️ Avanzado: HTML personalizado")
    
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
