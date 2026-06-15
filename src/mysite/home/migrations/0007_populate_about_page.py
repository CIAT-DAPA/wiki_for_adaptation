from django.db import migrations

HERO_INTRO = (
    "The Adaptation Tracking Wiki is a collaborative, open knowledge base "
    "providing standardized indicators, metrics, and SOPs for practitioners "
    "and policymakers tracking climate change adaptation worldwide."
)

ABOUT_BODY = (
    '<p>The Adaptation Tracking Wiki was developed as part of the '
    '<a href="https://alliancebioversityciat.org">Adaptation Insights project</a>, '
    "aimed at enhancing understanding of climate adaptation tracking and providing "
    "practical tools for assessing adaptation effectiveness. As the wiki grows, we "
    "welcome additional partners and contributors to expand its reach and impact.</p>"
)

ABOUT_TAGS = [
    ("tag", "Adaptation Insights project"),
    ("tag", "2024 – 2026"),
    ("tag", "Funded by the Gates Foundation"),
]

KEY_FEATURES = [
    ("feature", {
        "icon": "fa-people-group", "color": "purple", "title": "Community driven",
        "description": (
            "Built collaboratively with people active in adaptation programs and "
            "research. Wiki contributors can update entries to reflect the state of "
            "the art. Standard operating procedures reflect best practices and are "
            "reviewed to ensure accuracy and scientific rigor."
        ),
    }),
    ("feature", {
        "icon": "fa-globe", "color": "blue", "title": "Comprehensive indicators",
        "description": (
            "Indicators span climate change hazards, adaptation interventions, and "
            "adaptation impacts in agriculture — reflecting commonly tracked aspects "
            "of adaptation projects and programs worldwide."
        ),
    }),
    ("feature", {
        "icon": "fa-chart-line", "color": "emerald", "title": "Radically practical",
        "description": (
            "Identifies easy-to-operationalize methods and approaches that support "
            "robust and low-effort adaptation tracking — designed so that field "
            "practitioners can apply them without specialist data infrastructure."
        ),
    }),
]

PARTNERS = [
    ("partner", {
        "name": "Alliance of Bioversity International and CIAT",
        "tag": "Research & coordination",
        "description": (
            "Delivering research-based solutions that harness agricultural "
            "biodiversity to support sustainable, climate-resilient food systems."
        ),
        "logo_url": "images/Alliance_Logo.png",
        "url": "https://alliancebioversityciat.org",
    }),
    ("partner", {
        "name": "International Water Management Institute",
        "tag": "Data standards & coordination",
        "description": (
            "Providing international standards for meteorological observations and "
            "data exchange across climate monitoring networks."
        ),
        "logo_url": "images/IWMI_Logo.jpg",
        "url": "https://www.iwmi.cgiar.org",
    }),
    ("partner", {
        "name": "International Livestock Research Institute",
        "tag": "Research & data",
        "description": (
            "Supporting climate research initiatives and providing comprehensive "
            "datasets for agricultural adaptation indicators."
        ),
        "logo_url": "images/ilri_logo.jpg",
        "url": "https://www.ilri.org",
    }),
]

TEAM = [
    ("member", {
        "initials": "MR", "color": "blue", "name": "Dr. Maria Rodriguez",
        "role": "Lead Editor",
        "description": (
            "Climate scientist specialising in adaptation indicators and measurement "
            "frameworks for agricultural systems."
        ),
    }),
    ("member", {
        "initials": "JC", "color": "emerald", "name": "Dr. James Chen",
        "role": "Technical Editor",
        "description": (
            "Expert in climate data, remote sensing, and geospatial analysis for "
            "environmental monitoring."
        ),
    }),
    ("member", {
        "initials": "AO", "color": "amber", "name": "Dr. Amara Okafor",
        "role": "Contributing Editor",
        "description": (
            "Managing content quality and community contributions across the wiki's "
            "growing knowledge base."
        ),
    }),
]

CONTACT_CARDS = [
    ("card", {
        "icon": "fa-envelope", "title": "General inquiries",
        "description": (
            "Questions about the wiki, how to use it, or how to suggest additions or "
            "corrections to existing entries."
        ),
        "button_label": "Send a message", "button_url": "/feedback", "primary": False,
    }),
    ("card", {
        "icon": "fa-plus", "title": "Become a contributor",
        "description": (
            "Share your expertise by contributing new indicators, metrics, or SOPs. "
            "All contributions are reviewed by the editorial team."
        ),
        "button_label": "Start contributing", "button_url": "/become-editor", "primary": True,
    }),
]


def populate_about(apps, schema_editor):
    """Seed the existing About page with the previous (hard-coded) content so
    editors see it in the admin and can tweak it in place. Best-effort: skips if
    there is no About page yet (fresh installs)."""
    try:
        from home.models import AboutPage
    except Exception:
        return

    page = AboutPage.objects.first()
    if page is None:
        return

    page.hero_intro = HERO_INTRO
    page.about_body = ABOUT_BODY
    page.about_tags = ABOUT_TAGS
    page.key_features = KEY_FEATURES
    page.partners = PARTNERS
    page.team = TEAM
    page.contact_cards = CONTACT_CARDS
    page.save()

    # Publish a revision so the populated content shows in the admin editor too.
    try:
        page.save_revision().publish()
    except Exception:
        pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0006_remove_aboutpage_body_remove_aboutpage_subtitle_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_about, noop),
    ]
