from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.template.response import TemplateResponse
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from wagtail.models import Page

# To enable logging of search queries for use with the "Promoted search results" module
# <https://docs.wagtail.org/en/stable/reference/contrib/searchpromotions.html>
# uncomment the following line and the lines indicated in the search function
# (after adding wagtail.contrib.search_promotions to INSTALLED_APPS):

# from wagtail.contrib.search_promotions.models import Query


def search(request):
    search_query = request.GET.get("query", None)
    page = request.GET.get("page", 1)
    content_type_filter = request.GET.get("type", None)  # 'indicator', 'metric', 'sop', or None for all
    dimension_filter = request.GET.get("dimension", None)
    author_filter = request.GET.get("author", None)
    indicator_type_filter = request.GET.get("indicator_type", None)
    geographic_scale_filter = request.GET.get("geographic_scale", None)
    frequency_filter = request.GET.get("frequency", None)

    # Search
    if search_query:
        search_results = Page.objects.live().search(search_query)
        
        # Convert search results to a list of PKs to use with regular querysets
        search_pks = [r.pk for r in search_results]
        search_results = Page.objects.filter(pk__in=search_pks)

        # Filter by content type if specified
        if content_type_filter:
            if content_type_filter == 'indicator':
                content_type = ContentType.objects.get(app_label='catalog', model='indicatorpage')
                search_results = search_results.filter(content_type=content_type)
            elif content_type_filter == 'metric':
                content_type = ContentType.objects.get(app_label='catalog', model='metricpage')
                search_results = search_results.filter(content_type=content_type)
            elif content_type_filter == 'sop':
                content_type = ContentType.objects.get(app_label='catalog', model='soppage')
                search_results = search_results.filter(content_type=content_type)
        
        # Filter by dimension if specified (only applies to IndicatorPage)
        if dimension_filter and dimension_filter != 'all':
            from catalog.models import IndicatorPage
            indicator_ct = ContentType.objects.get(app_label='catalog', model='indicatorpage')
            search_results = search_results.filter(
                content_type=indicator_ct,
                indicatorpage__dimension=dimension_filter
            )
        
        # Filter by author if specified
        if author_filter and author_filter != 'all':
            search_results = search_results.filter(
                Q(indicatorpage__entry_author=author_filter) |
                Q(metricpage__entry_author=author_filter) |
                Q(soppage__entry_author=author_filter)
            )
        
        # Filter by indicator type if specified (only applies to IndicatorPage)
        if indicator_type_filter and indicator_type_filter != 'all':
            from catalog.models import IndicatorPage
            indicator_ct = ContentType.objects.get(app_label='catalog', model='indicatorpage')
            search_results = search_results.filter(
                content_type=indicator_ct,
                indicatorpage__indicator_type=indicator_type_filter
            )
        
        # Filter by geographic scale if specified (only applies to SOPPage)
        if geographic_scale_filter and geographic_scale_filter != 'all':
            from catalog.models import SOPPage
            sop_ct = ContentType.objects.get(app_label='catalog', model='soppage')
            search_results = search_results.filter(
                content_type=sop_ct,
                soppage__geographic_scale=geographic_scale_filter
            )
        
        # Filter by frequency if specified (only applies to SOPPage)
        if frequency_filter and frequency_filter != 'all':
            from catalog.models import SOPPage
            sop_ct = ContentType.objects.get(app_label='catalog', model='soppage')
            search_results = search_results.filter(
                content_type=sop_ct,
                soppage__frequency=frequency_filter
            )

        # Calculate counts by type for tabs (use the original search PKs)
        all_results = Page.objects.filter(pk__in=search_pks)
        
        indicator_ct = ContentType.objects.get(app_label='catalog', model='indicatorpage')
        metric_ct = ContentType.objects.get(app_label='catalog', model='metricpage')
        sop_ct = ContentType.objects.get(app_label='catalog', model='soppage')
        
        indicator_count = all_results.filter(content_type=indicator_ct).count()
        metric_count = all_results.filter(content_type=metric_ct).count()
        sop_count = all_results.filter(content_type=sop_ct).count()

        # To log this query for use with the "Promoted search results" module:

        # query = Query.get(search_query)
        # query.add_hit()

    else:
        search_results = Page.objects.none()
        indicator_count = 0
        metric_count = 0
        sop_count = 0

    # Get unique dimensions and authors for filter dropdowns
    from catalog.models import IndicatorPage, MetricPage, SOPPage
    
    dimensions = set()
    authors = set()
    indicator_types = set()
    geographic_scales = set()
    frequencies = set()
    
    # Only IndicatorPage has dimension and indicator_type fields
    dimensions.update(IndicatorPage.objects.live().values_list('dimension', flat=True).distinct())
    indicator_types.update(IndicatorPage.objects.live().values_list('indicator_type', flat=True).distinct())
    
    # Only SOPPage has geographic_scale and frequency fields
    geographic_scales.update(SOPPage.objects.live().values_list('geographic_scale', flat=True).distinct())
    frequencies.update(SOPPage.objects.live().values_list('frequency', flat=True).distinct())
    
    # All models have entry_author
    for model in [IndicatorPage, MetricPage, SOPPage]:
        authors.update(model.objects.live().values_list('entry_author', flat=True).distinct())
    
    # Remove None and empty values
    dimensions = sorted([d for d in dimensions if d])
    authors = sorted([a for a in authors if a])
    indicator_types = sorted([t for t in indicator_types if t])
    geographic_scales = sorted([g for g in geographic_scales if g])
    frequencies = sorted([f for f in frequencies if f])

    # Pagination
    paginator = Paginator(search_results, 10)
    try:
        search_results = paginator.page(page)
    except PageNotAnInteger:
        search_results = paginator.page(1)
    except EmptyPage:
        search_results = paginator.page(paginator.num_pages)

    return TemplateResponse(
        request,
        "search/search.html",
        {
            "search_query": search_query,
            "search_results": search_results,
            "content_type_filter": content_type_filter,
            "dimension_filter": dimension_filter,
            "author_filter": author_filter,
            "indicator_type_filter": indicator_type_filter,
            "geographic_scale_filter": geographic_scale_filter,
            "frequency_filter": frequency_filter,
            "indicator_count": indicator_count,
            "metric_count": metric_count,
            "sop_count": sop_count,
            "dimensions": dimensions,
            "authors": authors,
            "indicator_types": indicator_types,
            "geographic_scales": geographic_scales,
            "frequencies": frequencies,
        },
    )
