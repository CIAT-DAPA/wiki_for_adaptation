from wagtail import hooks
from django.urls import path, reverse
from wagtail.admin.menu import MenuItem
from .views import DetailedSiteHistoryView


@hooks.register("construct_explorer_page_queryset")
def order_catalog_pages(parent_page, pages, request):
    return pages.order_by("title")


@hooks.register("register_admin_urls")
def register_detailed_site_history_url():
    """Register the detailed site history URL in Wagtail admin."""
    return [
        path("reports/detailed-audit/", DetailedSiteHistoryView.as_view(), name="detailed_site_history"),
    ]


@hooks.register("register_reports_menu_item")
def register_detailed_site_history_menu_item():
    """Add the detailed site history to the Reports menu in Wagtail admin."""
    return MenuItem(
        "Detailed Audit Log",
        reverse("detailed_site_history"),
        icon_name="doc-empty-inverse",
        order=1000,
    )


@hooks.register("construct_reports_menu")
def hide_site_history_menu_item(request, menu_items):
    """Remove the default Site history from the Reports menu."""
    menu_items[:] = [item for item in menu_items if item.name != "site-history"]
