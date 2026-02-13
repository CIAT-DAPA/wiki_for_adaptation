from wagtail import hooks
from django.urls import path, reverse
from wagtail.admin.menu import MenuItem
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Group
from .views import DetailedSiteHistoryView
import logging

logger = logging.getLogger(__name__)


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


# ==============================================================================
# Workflow Email Notifications
# ==============================================================================

def send_workflow_notification(page, workflow_state, event_type, user=None, comment=None):
    """
    Send email notifications for workflow events.
    
    Args:
        page: The page object
        workflow_state: The WorkflowState object
        event_type: Type of event ('submitted', 'approved', 'rejected', 'cancelled')
        user: User who triggered the action
        comment: Optional comment from reviewer
    """
    try:
        # Get the page URL in admin
        admin_url = f"{settings.WAGTAILADMIN_BASE_URL}/admin/pages/{page.id}/edit/"
        
        if event_type == 'submitted':
            # Notify reviewers that content needs review
            reviewer_group = Group.objects.filter(name='Reviewers').first()
            if reviewer_group:
                reviewer_emails = list(
                    reviewer_group.user_set.filter(is_active=True)
                    .values_list('email', flat=True)
                    .exclude(email='')
                )
                
                if reviewer_emails:
                    subject = f'[TrackAdapt Wiki] New content for review: {page.title}'
                    message = f"""
Hello,

A new page has been submitted for review:

Page: {page.title}
Submitted by: {user.get_full_name() if user else 'Unknown'} ({user.email if user else 'N/A'})
Type: {page.content_type.model if hasattr(page, 'content_type') else 'Page'}

Please review this content at:
{admin_url}

Thank you,
TrackAdapt Wiki System
"""
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        reviewer_emails,
                        fail_silently=False,
                    )
                    logger.info(f"Sent review notification for page '{page.title}' to {len(reviewer_emails)} reviewers")
        
        elif event_type == 'approved':
            # Notify author that content was approved
            if page.owner and page.owner.email:
                subject = f'[TrackAdapt Wiki] Your content has been approved: {page.title}'
                message = f"""
Hello {page.owner.get_full_name()},

Your page has been approved and published:

Page: {page.title}
Approved by: {user.get_full_name() if user else 'Unknown'} ({user.email if user else 'N/A'})

View the page at:
{admin_url}

Thank you for your contribution!

TrackAdapt Wiki System
"""
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [page.owner.email],
                    fail_silently=False,
                )
                logger.info(f"Sent approval notification for page '{page.title}' to {page.owner.email}")
        
        elif event_type == 'rejected':
            # Notify author that content needs changes
            if page.owner and page.owner.email:
                subject = f'[TrackAdapt Wiki] Changes requested for: {page.title}'
                comment_text = f"\n\nReviewer comments:\n{comment}" if comment else ""
                message = f"""
Hello {page.owner.get_full_name()},

Your page requires changes before it can be published:

Page: {page.title}
Reviewed by: {user.get_full_name() if user else 'Unknown'} ({user.email if user else 'N/A'}){comment_text}

Please make the requested changes and resubmit:
{admin_url}

Thank you,
TrackAdapt Wiki System
"""
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [page.owner.email],
                    fail_silently=False,
                )
                logger.info(f"Sent rejection notification for page '{page.title}' to {page.owner.email}")
        
        elif event_type == 'cancelled':
            # Notify reviewers that submission was cancelled
            reviewer_group = Group.objects.filter(name='Reviewers').first()
            if reviewer_group:
                reviewer_emails = list(
                    reviewer_group.user_set.filter(is_active=True)
                    .values_list('email', flat=True)
                    .exclude(email='')
                )
                
                if reviewer_emails:
                    subject = f'[TrackAdapt Wiki] Review cancelled: {page.title}'
                    message = f"""
Hello,

A review has been cancelled:

Page: {page.title}
Cancelled by: {user.get_full_name() if user else 'Unknown'} ({user.email if user else 'N/A'})

No further action is required.

TrackAdapt Wiki System
"""
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        reviewer_emails,
                        fail_silently=False,
                    )
                    logger.info(f"Sent cancellation notification for page '{page.title}' to {len(reviewer_emails)} reviewers")
    
    except Exception as e:
        logger.error(f"Failed to send workflow notification: {e}", exc_info=True)


@hooks.register('after_submit_for_moderation')
def notify_on_submit(request, page):
    """Send notification when content is submitted for review."""
    workflow_state = page.current_workflow_state
    if workflow_state:
        send_workflow_notification(page, workflow_state, 'submitted', request.user)


@hooks.register('after_approve_moderation')
def notify_on_approve(request, page_revision):
    """Send notification when content is approved."""
    page = page_revision.page
    send_workflow_notification(page, None, 'approved', request.user)


@hooks.register('after_reject_moderation')
def notify_on_reject(request, page_revision):
    """Send notification when content is rejected."""
    page = page_revision.page
    # Try to get comment from request
    comment = request.POST.get('comment', '')
    send_workflow_notification(page, None, 'rejected', request.user, comment)


@hooks.register('after_cancel_workflow')
def notify_on_cancel(request, page, workflow_state):
    """Send notification when workflow is cancelled."""
    send_workflow_notification(page, workflow_state, 'cancelled', request.user)
