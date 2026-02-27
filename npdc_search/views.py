from collections import Counter
from django.shortcuts import render
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.db.models import Q, Count, F
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity
from django.conf import settings
from django.core.cache import cache
from django.views.decorators.http import require_POST, require_GET
from django.middleware.csrf import get_token
from datetime import datetime
import json
import re
import time
import logging
from data_submission.models import DatasetSubmission
from .models import SearchLog
from .security import (
    sanitize_query, sanitize_sort, sanitize_filter_value,
    validate_coordinate, validate_date, rate_limit,
    get_cache_key, CACHE_TIMEOUT_FACETS, CACHE_TIMEOUT_RESULTS
)
from .ai_search import (
    parse_natural_language_query,
    get_ai_suggestions,
    generate_search_summary,
    get_available_keywords,
)

logger = logging.getLogger(__name__)


RESULTS_PER_PAGE = 20


def search_view(request):
    """
    Core Search Engine with PostgreSQL Full Text Search,
    Advanced Query Builder, Keyword Facets, Map, and AI features.
    """
    start_time = time.time()
    # --------------------------------------------------
    # 1. Base Queryset (Role-Based Visibility)
    # --------------------------------------------------
    if request.user.is_staff or request.user.is_superuser:
        queryset = DatasetSubmission.objects.all()
    else:
        queryset = DatasetSubmission.objects.filter(status="published")

    queryset = queryset.select_related(
        "platform", "gps", "location", "resolution"
    ).prefetch_related(
        "scientists", "instruments"
    )

    # --------------------------------------------------
    # 2. Get & Sanitize Parameters (Security Hardening)
    # --------------------------------------------------
    query = sanitize_query(request.GET.get("query", ""))
    expedition = sanitize_filter_value(request.GET.get("expedition", ""))
    category = sanitize_filter_value(request.GET.get("category", ""))
    iso = sanitize_filter_value(request.GET.get("iso", ""))
    year = sanitize_filter_value(request.GET.get("year", ""))

    # Keyword filter (from NPDC_With_Chatbot)
    keyword_selected = request.GET.getlist('keyword')
    keyword_selected = [sanitize_filter_value(k) for k in keyword_selected if k]

    start_date = validate_date(request.GET.get("start", ""))
    end_date = validate_date(request.GET.get("end", ""))
    sort = sanitize_sort(request.GET.get("sort", "newest"))

    # --------------------------------------------------
    # 2.5 Get Filter Options for Advanced Search
    # --------------------------------------------------
    from data_submission.models import PlatformMetadata, InstrumentMetadata

    platforms = PlatformMetadata.objects.values_list('short_name', flat=True).distinct().order_by('short_name')
    instruments = InstrumentMetadata.objects.values_list('short_name', flat=True).distinct().order_by('short_name')

    # --------------------------------------------------
    # 3. PostgreSQL Full Text Search (Performance Optimized)
    # --------------------------------------------------
    search_rank = None
    if query:
        if query.startswith("10."):
            queryset = queryset.filter(doi__iexact=query)
        else:
            phrases = re.findall(r'"([^"]+)"', query)
            remaining = re.sub(r'"[^"]+', '', query).strip()
            words = remaining.split() if remaining else []
            search_terms = phrases + words

            if search_terms:
                search_string = ' & '.join(search_terms)
                search_query = SearchQuery(search_string, search_type='raw')

                search_vector = SearchVector(
                    'title', weight='A'
                ) + SearchVector(
                    'abstract', weight='B'
                ) + SearchVector(
                    'keywords', weight='A'
                ) + SearchVector(
                    'project_name', weight='C'
                )

                queryset = queryset.annotate(
                    search_rank=SearchRank(search_vector, search_query)
                ).filter(
                    Q(search_rank__gte=0.001) |
                    Q(scientists__first_name__icontains=search_terms[0]) |
                    Q(scientists__last_name__icontains=search_terms[0]) |
                    Q(instruments__short_name__icontains=search_terms[0]) |
                    Q(platform__short_name__icontains=search_terms[0])
                ).distinct()

                search_rank = True

    # --------------------------------------------------
    # 3.1 Advanced Search Query Builder
    # --------------------------------------------------
    adv_ops = request.GET.getlist('adv_op')
    adv_fields = request.GET.getlist('adv_field')
    adv_vals = request.GET.getlist('adv_val')

    if adv_ops and adv_fields and adv_vals and len(adv_ops) == len(adv_fields) == len(adv_vals):
        advanced_q = Q()
        has_adv_filter = False
        is_first_valid = True

        for i in range(len(adv_ops)):
            op = adv_ops[i]
            field = adv_fields[i]
            val = adv_vals[i].strip()[:200]

            if not val:
                continue

            has_adv_filter = True
            row_q = Q()

            if field == 'all':
                row_q = (
                    Q(title__icontains=val) |
                    Q(abstract__icontains=val) |
                    Q(keywords__icontains=val) |
                    Q(project_name__icontains=val)
                )
            elif field == 'title':
                row_q = Q(title__icontains=val)
            elif field == 'abstract':
                row_q = Q(abstract__icontains=val)
            elif field == 'person':
                row_q = (
                    Q(scientists__first_name__icontains=val) |
                    Q(scientists__last_name__icontains=val) |
                    Q(submitter__first_name__icontains=val) |
                    Q(submitter__last_name__icontains=val) |
                    Q(contact_person__icontains=val)
                )
            elif field == 'keywords':
                row_q = Q(keywords__icontains=val)
            elif field == 'project':
                row_q = Q(project_name__icontains=val)
            elif field == 'doi':
                row_q = Q(title__icontains=val)
            elif field == 'platform':
                row_q = Q(platform__short_name__icontains=val) | Q(platform__long_name__icontains=val)
            elif field == 'instrument':
                row_q = Q(instruments__short_name__icontains=val) | Q(instruments__long_name__icontains=val)
            elif field == 'submission_date':
                try:
                    date_val = datetime.strptime(val, '%Y-%m-%d').date()
                    row_q = Q(submission_date__date=date_val)
                except ValueError:
                    continue

            if is_first_valid:
                advanced_q = row_q
                is_first_valid = False
            else:
                if op == 'and':
                    advanced_q &= row_q
                elif op == 'or':
                    advanced_q |= row_q
                elif op == 'not':
                    advanced_q &= ~row_q

        if has_adv_filter:
            queryset = queryset.filter(advanced_q).distinct()

    # --------------------------------------------------
    # 4. Apply Filters
    # --------------------------------------------------
    if expedition:
        expedition_list = request.GET.getlist('expedition')
        expedition_list = [sanitize_filter_value(e) for e in expedition_list if e]
        if expedition_list:
            queryset = queryset.filter(expedition_type__in=expedition_list)

    if category:
        category_list = request.GET.getlist('category')
        category_list = [sanitize_filter_value(c) for c in category_list if c]
        if category_list:
            queryset = queryset.filter(category__in=category_list)

    if iso:
        iso_list = request.GET.getlist('iso')
        iso_list = [sanitize_filter_value(i) for i in iso_list if i]
        if iso_list:
            queryset = queryset.filter(iso_topic__in=iso_list)

    # Keyword filter (OR logic within keywords)
    if keyword_selected:
        keyword_q = Q()
        for k in keyword_selected:
            keyword_q |= Q(keywords__icontains=k)
        queryset = queryset.filter(keyword_q)

    if year:
        year_list = request.GET.getlist('year')
        year_list = [y for y in year_list if y]
        if year_list:
            queryset = queryset.filter(expedition_year__in=year_list)

    # --------------------------------------------------
    # 5. Temporal Overlap Filter
    # --------------------------------------------------
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            queryset = queryset.filter(
                temporal_start_date__lte=end_dt,
                temporal_end_date__gte=start_dt
            )
        except ValueError:
            pass

    # --------------------------------------------------
    # 6. Spatial Bounding Box Filter
    # --------------------------------------------------
    search_west = request.GET.get("bbox_west")
    search_east = request.GET.get("bbox_east")
    search_south = request.GET.get("bbox_south")
    search_north = request.GET.get("bbox_north")

    if search_west and search_east and search_south and search_north:
        try:
            sw = float(search_west)
            se = float(search_east)
            ss = float(search_south)
            sn = float(search_north)
            queryset = queryset.filter(
                west_longitude__lte=se,
                east_longitude__gte=sw,
                south_latitude__lte=sn,
                north_latitude__gte=ss
            )
        except ValueError:
            pass

    # --------------------------------------------------
    # 7. Sorting (Relevance-aware)
    # --------------------------------------------------
    sort_mapping = {
        "newest": "-submission_date",
        "oldest": "submission_date",
        "title_asc": "title",
        "title_desc": "-title",
    }

    if query and search_rank:
        queryset = queryset.order_by('-search_rank', '-submission_date')
    else:
        queryset = queryset.order_by(sort_mapping.get(sort, "-submission_date"))

    # --------------------------------------------------
    # 8. Facet Calculations
    # --------------------------------------------------
    # Use a clean queryset for facets: no ordering, distinct counts to
    # prevent duplicate rows from multi-table JOINs (scientists, instruments)
    # inflating or misrepresenting the per-group counts.
    facet_qs = queryset.order_by()
    expedition_facets = dict(
        facet_qs.values_list('expedition_type').annotate(count=Count('id', distinct=True))
    )
    category_facets = dict(
        facet_qs.values_list('category').annotate(count=Count('id', distinct=True))
    )
    iso_facets = dict(
        facet_qs.values_list('iso_topic').annotate(count=Count('id', distinct=True))
    )
    year_facets = dict(
        facet_qs.values_list('expedition_year').annotate(count=Count('id', distinct=True))
    )

    # Keyword facets (comma-separated field processed in Python)
    all_keywords_raw = facet_qs.values_list('keywords', flat=True).distinct()
    keyword_counter = Counter()
    for k_str in all_keywords_raw:
        if k_str:
            parts = [k.strip() for k in k_str.split(',') if k.strip()]
            keyword_counter.update(parts)
    top_keywords = keyword_counter.most_common(20)
    keyword_facets = dict(top_keywords)

    # --------------------------------------------------
    # 8.1 Map Data Serialization
    # --------------------------------------------------
    map_data = list(queryset.filter(
        west_longitude__isnull=False,
        east_longitude__isnull=False,
        south_latitude__isnull=False,
        north_latitude__isnull=False
    ).values(
        'id', 'title',
        'west_longitude', 'east_longitude',
        'south_latitude', 'north_latitude'
    ))

    # --------------------------------------------------
    # 9. Pagination
    # --------------------------------------------------
    paginator = Paginator(queryset, RESULTS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # --------------------------------------------------
    # 10. Build Context with Filter Choices & Facets
    # --------------------------------------------------
    platform_choices = list(platforms)
    instrument_choices = list(instruments)

    # Prepare options with facet counts for the template
    expedition_options = []
    for v, d in DatasetSubmission.EXPEDITION_TYPES:
        expedition_options.append({'value': v, 'label': d, 'count': expedition_facets.get(v, 0)})

    category_options = []
    for v, d in DatasetSubmission.CATEGORY_CHOICES:
        category_options.append({'value': v, 'label': d, 'count': category_facets.get(v, 0)})

    iso_options = []
    for v, d in DatasetSubmission.ISO_TOPIC_CHOICES:
        iso_options.append({'value': v, 'label': d, 'count': iso_facets.get(v, 0)})

    year_options = []
    for v, d in DatasetSubmission.get_expedition_year_choices():
        year_options.append({'value': str(v), 'label': str(d), 'count': year_facets.get(v, 0)})

    keyword_options = []
    for k, count in top_keywords:
        keyword_options.append({'value': k, 'label': k, 'count': count})

    # Get selected values for checkboxes
    expedition_selected = request.GET.getlist('expedition')
    category_selected = request.GET.getlist('category')
    iso_selected = request.GET.getlist('iso')
    year_selected = request.GET.getlist('year')

    # --------------------------------------------------
    # 10.1 Build Applied Filters List for UI badges
    # --------------------------------------------------
    applied_filters = []

    exp_display = dict(DatasetSubmission.EXPEDITION_TYPES)
    for val in expedition_selected:
        if val:
            applied_filters.append({
                'type': 'expedition', 'value': val,
                'label': f"Expedition: {exp_display.get(val, val)}",
                'id': f"exp_{val}",
            })

    cat_display = dict(DatasetSubmission.CATEGORY_CHOICES)
    for val in category_selected:
        if val:
            applied_filters.append({
                'type': 'category', 'value': val,
                'label': f"Category: {cat_display.get(val, val)}",
                'id': f"cat_{val}",
            })

    iso_display = dict(DatasetSubmission.ISO_TOPIC_CHOICES)
    for val in iso_selected:
        if val:
            applied_filters.append({
                'type': 'iso', 'value': val,
                'label': f"ISO: {iso_display.get(val, val)}",
                'id': f"iso_{val}",
            })

    for val in keyword_selected:
        if val:
            applied_filters.append({
                'type': 'keyword', 'value': val,
                'label': f"Keyword: {val}",
                'id': f"kw_{val}",
            })

    for val in year_selected:
        if val:
            applied_filters.append({
                'type': 'year', 'value': val,
                'label': f"Year: {val}",
                'id': f"year_{val}",
            })

    if start_date or end_date:
        label_parts = []
        if start_date:
            label_parts.append(f"From: {start_date}")
        if end_date:
            label_parts.append(f"To: {end_date}")
        applied_filters.append({
            'type': 'temporal', 'value': '',
            'label': f"Date: {' — '.join(label_parts)}",
            'id': '',
        })

    if adv_ops and adv_fields and adv_vals:
        for i in range(min(len(adv_ops), len(adv_fields), len(adv_vals))):
            val = adv_vals[i].strip() if adv_vals[i] else ''
            if val:
                field_label = adv_fields[i].replace('_', ' ').title()
                applied_filters.append({
                    'type': 'advanced', 'value': str(i),
                    'label': f"{field_label}: {val}",
                    'id': '',
                })

    context = {
        "page_obj": page_obj,
        "query": query,
        "expedition": expedition,
        "category": category,
        "iso": iso,
        "year": year,
        "start_date": start_date,
        "end_date": end_date,
        "sort": sort,
        # Selected values for checkboxes
        "expedition_selected": expedition_selected,
        "category_selected": category_selected,
        "iso_selected": iso_selected,
        "year_selected": year_selected,
        "keyword_selected": keyword_selected,
        # Bounding box parameters
        "bbox_west": search_west or "",
        "bbox_east": search_east or "",
        "bbox_south": search_south or "",
        "bbox_north": search_north or "",
        # Filter dropdown choices (for advanced search JS)
        "expedition_choices": DatasetSubmission.EXPEDITION_TYPES,
        "category_choices": DatasetSubmission.CATEGORY_CHOICES,
        "iso_choices": DatasetSubmission.ISO_TOPIC_CHOICES,
        "year_choices": DatasetSubmission.get_expedition_year_choices(),
        "platform_choices": platform_choices,
        "instrument_choices": instrument_choices,
        # Options with counts (for sidebar facets)
        "expedition_options": expedition_options,
        "category_options": category_options,
        "iso_options": iso_options,
        "year_options": year_options,
        "keyword_options": keyword_options,
        "sort_options": [
            ("newest", "Newest First"),
            ("oldest", "Oldest First"),
            ("title_asc", "Title A-Z"),
            ("title_desc", "Title Z-A"),
        ],
        "map_data": map_data,
        "platforms": list(platforms),
        "instruments": list(instruments),
        "adv_ops": adv_ops,
        "adv_fields": adv_fields,
        "adv_vals": adv_vals,
        "applied_filters": applied_filters,
    }

    # --------------------------------------------------
    # Log Search for Analytics
    # --------------------------------------------------
    response_time_ms = int((time.time() - start_time) * 1000)
    filters_dict = {
        'expedition': expedition,
        'category': category,
        'iso': iso,
        'year': year,
        'keyword': keyword_selected,
        'start_date': start_date,
        'end_date': end_date,
        'bbox_west': search_west,
        'bbox_east': search_east,
        'bbox_south': search_south,
        'bbox_north': search_north,
        'sort': sort,
    }
    filters_dict = {k: v for k, v in filters_dict.items() if v}

    try:
        SearchLog.log_search(
            request=request,
            query=query,
            filters=filters_dict,
            result_count=page_obj.paginator.count,
            response_time_ms=response_time_ms
        )
    except Exception:
        pass

    # --------------------------------------------------
    # AJAX Response for Live Filtering
    # --------------------------------------------------
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        results_html = render_to_string('search/_results.html', context, request=request)
        pagination_html = render_to_string('search/_pagination.html', context, request=request)
        applied_filters_html = render_to_string('search/_applied_filters.html', context, request=request)

        return JsonResponse({
            'results_html': results_html,
            'pagination_html': pagination_html,
            'applied_filters_html': applied_filters_html,
            'count': page_obj.paginator.count,
            'num_pages': page_obj.paginator.num_pages,
            'current_page': page_obj.number,
            'facets': {
                'expedition': expedition_facets,
                'category': category_facets,
                'iso': iso_facets,
                'year': year_facets,
                'keyword': keyword_facets,
            },
            'map_data': map_data,
        })

    return render(request, "search/search.html", context)


def simple_search_view(request):
    """Renders the simple search page."""
    from data_submission.models import DatasetSubmission
    year_choices = DatasetSubmission.get_expedition_year_choices()
    context = {"year_choices": year_choices}
    return render(request, "search/simple_search.html", context)


# ==============================================================
# AI SEARCH API ENDPOINTS
# ==============================================================

@rate_limit(10)
@require_POST
def ai_parse_query(request):
    """
    API: Parse a natural language query into structured search parameters.
    POST /search/api/ai-parse/
    Body: {"query": "glacier data from Himalaya 2024"}
    Returns: {"keywords": "glacier", "expedition": "himalaya", "year": "2024-2025", ...}
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()

        if not query or len(query) < 5:
            return JsonResponse({'error': 'Query too short'}, status=400)

        result = parse_natural_language_query(query)

        if result:
            return JsonResponse({
                'success': True,
                'parsed': result,
                'original_query': query,
            })
        else:
            return JsonResponse({
                'success': False,
                'parsed': {'keywords': query},
                'original_query': query,
            })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"AI parse error: {e}")
        return JsonResponse({'error': 'AI parsing failed'}, status=500)


@rate_limit(10)
@require_POST
def ai_suggest(request):
    """
    API: Get AI suggestions when search returns 0 results.
    POST /search/api/ai-suggest/
    Body: {"query": "artic ice sheet"}
    Returns: {"corrected_query": "arctic ice sheet", "suggestions": [...]}
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()

        if not query or len(query) < 3:
            return JsonResponse({'error': 'Query too short'}, status=400)

        available_kw = get_available_keywords()
        result = get_ai_suggestions(query, available_kw)

        if result:
            return JsonResponse({
                'success': True,
                'corrected_query': result.get('corrected_query', ''),
                'suggestions': result.get('suggestions', []),
                'off_topic': result.get('off_topic', False),
            })
        else:
            return JsonResponse({'success': False})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"AI suggest error: {e}")
        return JsonResponse({'error': 'AI suggestion failed'}, status=500)


@rate_limit(10)
@require_POST
def ai_summary(request):
    """
    API: Generate AI summary of search results.
    POST /search/api/ai-summary/
    Body: {"query": "ocean temperature", "result_count": 5, "results": [...]}
    Returns: {"summary": "Found 5 datasets about ocean temperature..."}
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        result_count = data.get('result_count', 0)

        if not query or result_count == 0:
            return JsonResponse({'success': False})

        if request.user.is_staff or request.user.is_superuser:
            queryset = DatasetSubmission.objects.all()
        else:
            queryset = DatasetSubmission.objects.filter(status="published")

        phrases = re.findall(r'"([^"]+)"', query)
        remaining = re.sub(r'"[^"]+', '', query).strip()
        words = remaining.split() if remaining else []
        search_terms = phrases + words

        if search_terms:
            search_string = ' & '.join(search_terms)
            try:
                search_query = SearchQuery(search_string, search_type='raw')
                search_vector = SearchVector(
                    'title', weight='A'
                ) + SearchVector(
                    'abstract', weight='B'
                ) + SearchVector(
                    'keywords', weight='A'
                )

                top_results = queryset.annotate(
                    search_rank=SearchRank(search_vector, search_query)
                ).filter(
                    search_rank__gte=0.001
                ).order_by('-search_rank')[:5]
            except Exception:
                q_filter = Q()
                for term in search_terms:
                    q_filter |= Q(title__icontains=term) | Q(abstract__icontains=term)
                top_results = queryset.filter(q_filter)[:5]
        else:
            top_results = queryset[:5]

        results_data = []
        for d in top_results:
            results_data.append({
                'title': d.title,
                'abstract': d.abstract[:300],
                'category': d.get_category_display(),
                'expedition_type': d.get_expedition_type_display(),
                'temporal_start': str(d.temporal_start_date),
                'temporal_end': str(d.temporal_end_date),
                'south_lat': d.south_latitude,
                'north_lat': d.north_latitude,
                'west_lon': d.west_longitude,
                'east_lon': d.east_longitude,
            })

        summary = generate_search_summary(query, results_data, result_count)

        if summary:
            return JsonResponse({
                'success': True,
                'summary': summary,
            })
        else:
            return JsonResponse({'success': False})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"AI summary error: {e}")
        return JsonResponse({'error': 'AI summary failed'}, status=500)


# ==============================================================
# AI SEARCH PAGE & API (KPDC-style chat/result)
# ==============================================================

def ai_search_page(request):
    """
    GET /search/ai-search/
    Renders the AI-powered search page with a big search box and chat-style results.
    """
    # Ensure CSRF cookie is set for fetch() calls
    get_token(request)
    return render(request, "search/ai_search.html")


@rate_limit(10)
@require_POST
def ai_rag_search(request):
    """
    POST /search/api/ai-search/
    JSON API: accepts {"query": "...", "filters": {...}}
    Returns: {"question": "...", "answer": "...", "datasets": [...]}
    """
    from .ai_search import ai_search_answer
    
    try:
        data = json.loads(request.body)
        query = sanitize_query(data.get('query', '').strip())
        filters = data.get('filters', {})

        if not query or len(query) < 3:
            return JsonResponse({'error': 'Query too short (minimum 3 characters)'}, status=400)

        if len(query) > 500:
            return JsonResponse({'error': 'Query too long (maximum 500 characters)'}, status=400)

        # Sanitize filter values
        clean_filters = {}
        if filters.get('expedition'):
            clean_filters['expedition'] = sanitize_filter_value(filters['expedition'])
        if filters.get('category'):
            clean_filters['category'] = sanitize_filter_value(filters['category'])
        if filters.get('start_date'):
            clean_filters['start_date'] = filters['start_date']
        if filters.get('end_date'):
            clean_filters['end_date'] = filters['end_date']

        start_time = time.time()
        result = ai_search_answer(query, clean_filters if clean_filters else None)
        response_time_ms = int((time.time() - start_time) * 1000)

        if result is None:
            return JsonResponse({
                'question': query,
                'answer': "I couldn't process your query. Please try again with different wording.",
                'datasets': [],
                'response_time_ms': response_time_ms,
            })

        # Log search
        try:
            SearchLog.log_search(
                request=request,
                query=f"[AI] {query}",
                filters=clean_filters,
                result_count=len(result.get('datasets', [])),
                response_time_ms=response_time_ms
            )
        except Exception:
            pass

        return JsonResponse({
            'question': query,
            'answer': result.get('answer', ''),
            'datasets': result.get('datasets', []),
            'result_count': len(result.get('datasets', [])),
            'corrected_query': result.get('corrected_query'),
            'suggestions': result.get('suggestions', []),
            'response_time_ms': response_time_ms,
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"AI RAG search error: {e}")
        return JsonResponse({'error': 'AI search failed. Please try again.'}, status=500)


def browse_by_keyword(request):
    """
    Browse datasets by keyword/category.
    Shows a card grid with each category, its dataset count, and sample keywords.
    """
    from data_submission.models import DatasetSubmission

    # Get published datasets (or all for staff)
    if request.user.is_staff or request.user.is_superuser:
        queryset = DatasetSubmission.objects.all()
    else:
        queryset = DatasetSubmission.objects.filter(status="published")

    # Build category data with counts and sample keywords
    categories = []
    for value, label in DatasetSubmission.CATEGORY_CHOICES:
        cat_datasets = queryset.filter(category=value)
        count = cat_datasets.count()
        
        # Collect sample keywords from this category's datasets
        sample_keywords = set()
        for kw_str in cat_datasets.values_list('keywords', flat=True)[:10]:
            if kw_str:
                for k in kw_str.split(','):
                    k = k.strip()
                    if k:
                        sample_keywords.add(k)
                    if len(sample_keywords) >= 6:
                        break
                if len(sample_keywords) >= 6:
                    break

        categories.append({
            'value': value,
            'label': label,
            'count': count,
            'sample_keywords': list(sample_keywords)[:6],
        })

    context = {
        'categories': categories,
    }
    return render(request, "search/browse_by_keyword.html", context)


def browse_by_location(request):
    """
    Browse datasets by location.
    Shows a tabbed interface with 4 regions (Antarctic, Arctic, Southern Ocean, Himalaya),
    each containing a table of subregions with dataset counts.
    """
    from data_submission.models import DatasetSubmission, LocationMetadata
    from django.db import connection
    from django.db.models import Avg

    # Get published datasets (or all for staff)
    if request.user.is_staff or request.user.is_superuser:
        base_qs = DatasetSubmission.objects.all()
    else:
        base_qs = DatasetSubmission.objects.filter(status="published")

    # Define the 4 regions matching expedition types
    regions = [
        {'key': 'antarctic', 'label': 'ANTARCTIC', 'expedition_type': 'antarctic', 'center': [-75, 45], 'zoom': 3},
        {'key': 'arctic', 'label': 'ARCTIC', 'expedition_type': 'arctic', 'center': [80, 15], 'zoom': 3},
        {'key': 'southern_ocean', 'label': 'SOUTHERN OCEAN', 'expedition_type': 'southern_ocean', 'center': [-55, 60], 'zoom': 3},
        {'key': 'himalaya', 'label': 'HIMALAYA', 'expedition_type': 'himalaya', 'center': [32, 77], 'zoom': 5},
    ]

    # Map expedition_type to legacy location_type values
    expedition_to_legacy = {
        'antarctic': ['Antarctic', 'Antarctica', 'antarctic', 'antarctica'],
        'arctic': ['Arctic', 'arctic'],
        'southern_ocean': ['Ocean', 'Southern Ocean', 'Indian Ocean Sector', 'ocean', 'southern ocean', 'indian ocean sector'],
        'himalaya': ['Himalaya', 'himalaya'],
    }

    active_tab = request.GET.get('region', 'antarctic')

    # Try to query legacy table for subregion data
    use_legacy = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM metadata_main_table LIMIT 1")
            use_legacy = True
    except Exception:
        pass

    for region in regions:
        region['active'] = (region['key'] == active_tab)
        locations = []

        if use_legacy:
            # Query the legacy table directly for subregion data
            legacy_types = expedition_to_legacy.get(region['expedition_type'], [])
            if legacy_types:
                placeholders = ', '.join(['%s'] * len(legacy_types))
                query = f"""
                    SELECT location_subregion1, COUNT(*) as cnt
                    FROM metadata_main_table
                    WHERE location_type IN ({placeholders})
                      AND location_subregion1 IS NOT NULL
                      AND location_subregion1 != ''
                    GROUP BY location_subregion1
                    ORDER BY location_subregion1
                """
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(query, legacy_types)
                        rows = cursor.fetchall()
                    
                    for i, (subregion, count) in enumerate(rows, start=1):
                        locations.append({
                            'sl_no': i,
                            'name': subregion.strip(),
                            'count': count,
                            'lat': None,
                            'lon': None,
                        })
                except Exception:
                    pass

        # Fallback to Django ORM LocationMetadata
        if not locations:
            location_data = (
                LocationMetadata.objects
                .filter(dataset__in=base_qs, dataset__expedition_type=region['expedition_type'])
                .exclude(location_subregion='')
                .exclude(location_subregion__isnull=True)
                .values('location_subregion')
                .annotate(
                    dataset_count=Count('dataset'),
                    avg_n=Avg('dataset__north_latitude'),
                    avg_s=Avg('dataset__south_latitude'),
                    avg_e=Avg('dataset__east_longitude'),
                    avg_w=Avg('dataset__west_longitude')
                )
                .order_by('location_subregion')
            )

            for i, loc in enumerate(location_data, start=1):
                lat = (loc['avg_n'] + loc['avg_s']) / 2 if loc['avg_n'] and loc['avg_s'] else None
                lon = (loc['avg_e'] + loc['avg_w']) / 2 if loc['avg_e'] and loc['avg_w'] else None
                
                locations.append({
                    'sl_no': i,
                    'name': loc['location_subregion'],
                    'count': loc['dataset_count'],
                    'lat': lat,
                    'lon': lon,
                })

        # Final fallback: show total count for this expedition type
        if not locations:
            total = base_qs.filter(expedition_type=region['expedition_type']).count()
            if total > 0:
                locations.append({
                    'sl_no': 1,
                    'name': region['label'].title() + ' Region',
                    'count': total,
                    'lat': None,
                    'lon': None,
                })

        region['locations'] = locations

    context = {
        'regions': regions,
        'active_tab': active_tab,
    }
    return render(request, "search/browse_by_location.html", context)
