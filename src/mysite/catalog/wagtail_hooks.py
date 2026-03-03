from wagtail import hooks
from django.urls import path, reverse
from wagtail.admin.menu import MenuItem
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Group
from django.dispatch import receiver
from wagtail.signals import (
    task_submitted,
    workflow_submitted,
    workflow_approved,
    workflow_rejected,
    workflow_cancelled,
)
from wagtail.models import TaskState, WorkflowState
from .views import DetailedSiteHistoryView
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Log that module was imported and signal receivers will be registered
logger.info("[WORKFLOW EMAIL] wagtail_hooks.py imported - signal receivers registering")

# Disable default Wagtail "submitted" notifications to avoid console backend emails
# and custom-recipient mismatch. We handle submitted notifications below via SMTP.
task_submitted.disconnect(
    sender=TaskState,
    dispatch_uid="group_approval_task_submitted_email_notification",
)
workflow_submitted.disconnect(
    sender=WorkflowState,
    dispatch_uid="workflow_state_submitted_email_notification",
)


def _load_email_config():
    """Load email configuration from .env for production email sending."""
    env_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'
    logger.info("[WORKFLOW EMAIL] Loading env from %s (exists=%s)", env_path, env_path.exists())
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path, override=True)
        except ImportError:
            logger.warning("[WORKFLOW EMAIL] python-dotenv is not installed")

    config = {
        'host': 'smtp.gmail.com',
        'port': 587,
        'use_tls': True,
        'username': os.environ.get('EMAIL_HOST_USER', ''),
        'password': os.environ.get('EMAIL_HOST_PASSWORD', ''),
        'from_email': os.environ.get('EMAIL_HOST_USER', settings.DEFAULT_FROM_EMAIL),
    }
    logger.info(
        "[WORKFLOW EMAIL] Config loaded host=%s port=%s user_set=%s from_email=%s",
        config['host'],
        config['port'],
        bool(config['username']),
        config['from_email'],
    )
    return config


def _send_email_with_smtp(subject, message, recipient_list):
    """Send email using SMTP with credentials from .env."""
    from django.core.mail import EmailMessage, get_connection

    config = _load_email_config()
    logger.info(
        "[WORKFLOW EMAIL] Sending subject=%s recipients=%s",
        subject,
        recipient_list,
    )

    if not config['username'] or not config['password']:
        logger.warning("[WORKFLOW EMAIL] Missing SMTP credentials, using Django fallback backend")
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        return

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=config['from_email'],
        to=recipient_list,
        connection=None,
    )

    connection = get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=config['host'],
        port=config['port'],
        username=config['username'],
        password=config['password'],
        use_tls=config['use_tls'],
        timeout=30,
    )

    email.connection = connection
    sent_count = email.send(fail_silently=False)
    logger.info("[WORKFLOW EMAIL] Send completed sent_count=%s", sent_count)


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
    if not page:
        logger.error("[WORKFLOW EMAIL] Event=%s but page is None", event_type)
        return

    try:
        logger.info(
            "[WORKFLOW EMAIL] Event=%s page_id=%s title=%s user=%s",
            event_type,
            page.id,
            page.title,
            user.email if user and getattr(user, 'email', None) else 'N/A',
        )
        # Get the page URL in admin
        admin_url = f"https://trackadapt.org/admin/pages/{page.id}/edit/"
        
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
                    _send_email_with_smtp(
                        subject,
                        message,
                        reviewer_emails,
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
                _send_email_with_smtp(
                    subject,
                    message,
                    [page.owner.email],
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
                _send_email_with_smtp(
                    subject,
                    message,
                    [page.owner.email],
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
                    _send_email_with_smtp(
                        subject,
                        message,
                        reviewer_emails,
                    )
                    logger.info(f"Sent cancellation notification for page '{page.title}' to {len(reviewer_emails)} reviewers")
    
    except Exception as e:
        logger.error(f"Failed to send workflow notification: {e}", exc_info=True)


@receiver(task_submitted)
def notify_on_task_submitted(sender, instance, user=None, **kwargs):
    """Send notification when content reaches a moderation task (submit/resubmit)."""
    logger.info("[WORKFLOW EMAIL] Signal received: task_submitted instance=%s", instance)
    workflow_state = getattr(instance, 'workflow_state', None)
    page = workflow_state.content_object if workflow_state else None
    send_workflow_notification(page, workflow_state, 'submitted', user)


@receiver(workflow_approved)
def notify_on_workflow_approved(sender, instance, user=None, **kwargs):
    """Send notification when content is approved."""
    logger.info("[WORKFLOW EMAIL] Signal received: workflow_approved instance=%s", instance)
    page = instance.content_object
    send_workflow_notification(page, instance, 'approved', user)


@receiver(workflow_rejected)
def notify_on_workflow_rejected(sender, instance, user=None, **kwargs):
    """Send notification when content is rejected."""
    logger.info("[WORKFLOW EMAIL] Signal received: workflow_rejected instance=%s", instance)
    page = instance.content_object
    comment = ""
    task_state = getattr(instance, 'current_task_state', None)
    if task_state:
        comment = getattr(task_state, 'comment', '') or ''
    send_workflow_notification(page, instance, 'rejected', user, comment)


@receiver(workflow_cancelled)
def notify_on_workflow_cancelled(sender, instance, user=None, **kwargs):
    """Send notification when workflow is cancelled."""
    logger.info("[WORKFLOW EMAIL] Signal received: workflow_cancelled instance=%s", instance)
    page = instance.content_object
    send_workflow_notification(page, instance, 'cancelled', user)
