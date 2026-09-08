from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from wagtail.log_actions import registry as log_registry
from wagtail.models import PageLogEntry
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType


def compare(request):
    """Side-by-side comparison of selected metrics (with their SOPs and methods).

    Reached from the "Compare" selection tray; ``?ids=`` is a comma-separated list
    of MetricPage ids (max 4), which also makes the comparison shareable.
    """
    from catalog.models import MetricPage, SOPPage, MethodPage

    raw = request.GET.get("ids", "")
    id_list = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and int(part) not in id_list:
            id_list.append(int(part))
    id_list = id_list[:4]

    metrics = {m.id: m for m in MetricPage.objects.live().filter(id__in=id_list).specific()}
    columns = []
    for pk in id_list:  # preserve the order the user selected
        metric = metrics.get(pk)
        if metric is None:
            continue
        sop = metric.get_children().type(SOPPage).live().specific().first()
        methods = list(metric.get_children().type(MethodPage).live().specific())
        parent = metric.get_parent()
        columns.append({
            "metric": metric,
            "sop": sop,
            "methods": methods,
            "indicator": parent.specific if parent else None,
        })

    return render(request, "catalog/compare.html", {"columns": columns})


def is_admin(user):
    """Check if user is staff or superuser."""
    return user.is_staff or user.is_superuser


@method_decorator(user_passes_test(is_admin), name='dispatch')
class DetailedSiteHistoryView(View):
    """
    Extended Site History view that combines Wagtail's PageLogEntry
    with django-auditlog's LogEntry to show field-level JSONB diffs.
    """
    
    def get(self, request):
        # Get all Wagtail page log entries
        wagtail_logs = PageLogEntry.objects.select_related(
            'user', 'page', 'content_type'
        ).order_by('-timestamp')[:100]  # Limit to recent 100 entries
        
        # Get all auditlog entries for catalog models
        catalog_content_types = ContentType.objects.filter(
            app_label='catalog',
            model__in=['indicatorpage', 'metricpage', 'methodpage', 'soppage']
        )
        
        auditlog_entries = LogEntry.objects.filter(
            content_type__in=catalog_content_types
        ).select_related('actor', 'content_type').order_by('-timestamp')[:100]
        
        # Combine and sort by timestamp
        combined_logs = []
        
        # Process Wagtail logs
        for log in wagtail_logs:
            # Safely get action label, fallback to action string if not registered
            try:
                action_label = log_registry.get_action_label(log.action)
            except (KeyError, AttributeError):
                action_label = log.action.replace('wagtail.', '').replace('.', ' ').title()
            
            combined_logs.append({
                'timestamp': log.timestamp,
                'user': log.user,
                'action': action_label,
                'page_title': log.page.title if log.page else 'Deleted page',
                'content_type': log.content_type.model if log.content_type else 'page',
                'changes': None,  # Wagtail doesn't store field diffs
                'source': 'wagtail'
            })
        
        # Process auditlog entries with field-level diffs
        for log in auditlog_entries:
            changes = {}
            if log.changes:
                # Filter out system fields from changes
                excluded_fields = {'live_revision', 'last_published_at', 'has_unpublished_changes'}
                changes = {k: v for k, v in log.changes.items() if k not in excluded_fields}
            
            combined_logs.append({
                'timestamp': log.timestamp,
                'user': log.actor,
                'action': log.get_action_display(),
                'page_title': str(log.object_repr) if log.object_repr else f'{log.content_type.model} #{log.object_id}',
                'content_type': log.content_type.model,
                'changes': changes,
                'source': 'auditlog'
            })
        
        # Sort by timestamp descending
        combined_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        context = {
            'logs': combined_logs[:100],  # Limit to 100 most recent
        }
        
        return render(request, 'catalog/detailed_site_history.html', context)
