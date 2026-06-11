from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.template.response import TemplateResponse
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from wagtail.models import Page


def search(request):
    search_query = request.GET.get("query", None)
    dimension_filter = request.GET.get("dimension", None)
    indicator_type_filter = request.GET.get("indicator_type", None)
    tracking_function_filter = request.GET.get("tracking_function", None)

    indicator_ct = ContentType.objects.get(app_label='catalog', model='indicatorpage')
    metric_ct = ContentType.objects.get(app_label='catalog', model='metricpage')
    sop_ct = ContentType.objects.get(app_label='catalog', model='soppage')
    searchable_content_types = [indicator_ct, metric_ct, sop_ct]

    # Some requests send query as literal strings like "None" or "null".
    if search_query is not None:
        search_query = search_query.strip()
        if search_query.lower() in {"", "none", "null"}:
            search_query = None

    # Normalize filter values: treat empty and "all" as "no filter".
    def _norm(value):
        return value if value and value != 'all' else None

    dimension_filter = _norm(dimension_filter)
    indicator_type_filter = _norm(indicator_type_filter)
    tracking_function_filter = _norm(tracking_function_filter)

    from catalog.models import IndicatorPage, MetricPage, SOPPage

    # Base querysets for each column. The page always shows both Indicators and
    # Metrics; the filters below narrow them with criteria that actually exist
    # in the data (so no option silently filters nothing).
    indicator_qs = IndicatorPage.objects.live()
    metric_qs = MetricPage.objects.live()

    # Free-text search applies across both columns.
    if search_query:
        search_pks = {
            r.pk for r in
            Page.objects.live().filter(content_type__in=searchable_content_types).search(search_query)
        }
        indicator_qs = indicator_qs.filter(pk__in=search_pks)
        metric_qs = metric_qs.filter(pk__in=search_pks)

    # Dimension / Subdimension are Indicator attributes. They filter Indicators
    # directly, and Metrics via their parent Indicator so both columns stay in sync.
    # Matching is normalized (trim + casefold) so a single cleaned dropdown option
    # still matches records stored with inconsistent whitespace/casing.
    def _matching_indicator_ids(field, value):
        target = value.strip().lower()
        return [
            obj.pk for obj in IndicatorPage.objects.live().only('pk', field)
            if (getattr(obj, field) or '').strip().lower() == target
        ]

    if dimension_filter:
        indicator_qs = indicator_qs.filter(pk__in=_matching_indicator_ids('dimension', dimension_filter))
    if indicator_type_filter:
        indicator_qs = indicator_qs.filter(pk__in=_matching_indicator_ids('indicator_type', indicator_type_filter))

    if dimension_filter or indicator_type_filter:
        parent_indicators = IndicatorPage.objects.live()
        if dimension_filter:
            parent_indicators = parent_indicators.filter(pk__in=_matching_indicator_ids('dimension', dimension_filter))
        if indicator_type_filter:
            parent_indicators = parent_indicators.filter(pk__in=_matching_indicator_ids('indicator_type', indicator_type_filter))
        parent_paths = list(parent_indicators.values_list('path', flat=True))
        if parent_paths:
            path_q = Q()
            for p in parent_paths:
                path_q |= Q(path__startswith=p)
            metric_qs = metric_qs.filter(path_q)
        else:
            metric_qs = metric_qs.none()

    # Adaptation tracking function is a Metric attribute and filters Metrics only.
    if tracking_function_filter == 'vulnerability':
        metric_qs = metric_qs.filter(tracks_vulnerability=True)
    elif tracking_function_filter == 'intervention':
        metric_qs = metric_qs.filter(tracks_intervention_impacts=True)

    indicator_qs = indicator_qs.order_by('title')
    metric_qs = metric_qs.order_by('title')

    indicator_count = indicator_qs.count()
    metric_count = metric_qs.count()
    has_results = indicator_count > 0 or metric_count > 0

    # Dropdown options, built from real data so every option matches something.
    # Collapse near-duplicates (differing only by surrounding whitespace/casing)
    # so the same label doesn't appear twice, while keeping a value that matches
    # actual stored records.
    def _distinct_options(values):
        seen = {}
        for v in values:
            if not v or not v.strip():
                continue
            key = v.strip().lower()
            seen.setdefault(key, v.strip())
        return sorted(seen.values(), key=str.lower)

    dimensions = _distinct_options(
        IndicatorPage.objects.live().values_list('dimension', flat=True)
    )
    indicator_types = _distinct_options(
        IndicatorPage.objects.live().values_list('indicator_type', flat=True)
    )

    # Paginate each column independently (tree order otherwise pushes all metrics
    # onto later pages, leaving the Metrics column empty on page 1).
    def _paginate(queryset, page_param):
        paginator = Paginator(queryset, 10)
        page_number = request.GET.get(page_param, 1)
        try:
            return paginator.page(page_number)
        except PageNotAnInteger:
            return paginator.page(1)
        except EmptyPage:
            return paginator.page(paginator.num_pages)

    indicator_results = _paginate(indicator_qs, "ipage")
    metric_results = _paginate(metric_qs, "mpage")

    return TemplateResponse(
        request,
        "search/search.html",
        {
            "search_query": search_query,
            "has_results": has_results,
            "indicator_results": indicator_results,
            "metric_results": metric_results,
            "indicator_count": indicator_count,
            "metric_count": metric_count,
            "dimension_filter": dimension_filter,
            "indicator_type_filter": indicator_type_filter,
            "tracking_function_filter": tracking_function_filter,
            "dimensions": dimensions,
            "indicator_types": indicator_types,
        },
    )
