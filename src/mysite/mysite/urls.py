from django.conf import settings
from django.urls import include, path
from django.contrib import admin
from django.views.generic import TemplateView

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from search import views as search_views
from mysite.oidc_views import oidc_logout_view

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    path("wiki-instructions/", TemplateView.as_view(template_name="wiki_instructions.html"), name="wiki_instructions"),
    path("faq/", TemplateView.as_view(template_name="faq.html"), name="faq"),
    path("become-editor/", TemplateView.as_view(template_name="become_editor.html"), name="become_editor"),
    path("feedback/", TemplateView.as_view(template_name="feedback.html"), name="feedback"),
    path("tracking-framework/", TemplateView.as_view(template_name="tracking_framework.html"), name="tracking_framework"),
    path("impact-pathways/guidance/", TemplateView.as_view(template_name="guidance_project_vs_policy.html"), name="guidance_project_vs_policy"),
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("admin/logout/", oidc_logout_view, name="wagtailadmin_logout"),  # Override Wagtail logout
    path("logout/", oidc_logout_view, name="oidc_logout"),  # Custom OIDC logout
    path("admin/", include(wagtailadmin_urls)),  # Include wagtail admin after logout override
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
]
