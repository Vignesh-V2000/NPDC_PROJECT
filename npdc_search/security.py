"""
Security and caching utilities for the search module.
Phase 11: Security Hardening
Phase 12: Caching Strategy
"""
import re
import hashlib
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings


# =============================================================================
# PHASE 11: SECURITY HARDENING
# =============================================================================

# Maximum query length to prevent DoS attacks
MAX_QUERY_LENGTH = 500

# Maximum number of filters to prevent parameter pollution
MAX_FILTERS = 20

# Allowed sort options (whitelist to prevent injection)
ALLOWED_SORT_OPTIONS = {'newest', 'oldest', 'title_asc', 'title_desc', 'relevance'}

# Characters to remove from search queries (potential SQL/script injection)
DANGEROUS_PATTERNS = [
    r'<script.*?>.*?</script>',  # Script tags
    r'javascript:',               # JavaScript protocol
    r'on\w+\s*=',                 # Event handlers
    r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]',  # Control characters
]


def sanitize_query(query: str) -> str:
    """
    Sanitize search query input.
    - Limit length
    - Remove dangerous patterns
    - Strip excessive whitespace
    """
    if not query:
        return ''
    
    # Limit length
    query = query[:MAX_QUERY_LENGTH]
    
    # Remove dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        query = re.sub(pattern, '', query, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove null bytes
    query = query.replace('\x00', '')
    
    # Normalize whitespace
    query = ' '.join(query.split())
    
    return query.strip()


def sanitize_sort(sort_option: str) -> str:
    """
    Validate sort option against whitelist to prevent ordering injection.
    """
    if sort_option in ALLOWED_SORT_OPTIONS:
        return sort_option
    return 'newest'  # Default fallback


def sanitize_filter_value(value: str, max_length: int = 100) -> str:
    """
    Sanitize filter values.
    """
    if not value:
        return ''
    
    # Limit length
    value = value[:max_length]
    
    # Remove dangerous characters
    value = re.sub(r'[<>\'\";(){}]', '', value)
    
    return value.strip()


def validate_coordinate(value: str, min_val: float, max_val: float) -> float:
    """
    Validate and parse coordinate values for bounding box.
    """
    try:
        coord = float(value)
        if min_val <= coord <= max_val:
            return coord
    except (ValueError, TypeError):
        pass
    return None


def validate_date(date_str: str) -> str:
    """
    Validate date format (YYYY-MM-DD).
    """
    if not date_str:
        return None
    
    # Simple regex validation for date format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    return None


# =============================================================================
# RATE LIMITING
# =============================================================================

def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def rate_limit(requests_per_minute: int = 60):
    """
    Rate limiting decorator for views.
    Uses Django's cache framework.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get client identifier
            if request.user.is_authenticated:
                client_id = f'user_{request.user.id}'
            else:
                client_id = f'ip_{get_client_ip(request)}'
            
            cache_key = f'ratelimit:search:{client_id}'
            
            # Get current count
            request_count = cache.get(cache_key, 0)
            
            if request_count >= requests_per_minute:
                return JsonResponse({
                    'error': 'Rate limit exceeded. Please wait before searching again.',
                    'retry_after': 60
                }, status=429)
            
            # Increment counter
            cache.set(cache_key, request_count + 1, timeout=60)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# PHASE 12: CACHING STRATEGY
# =============================================================================

# Cache timeouts (in seconds)
CACHE_TIMEOUT_FACETS = 300        # 5 minutes for facet counts
CACHE_TIMEOUT_RESULTS = 120       # 2 minutes for first page results
CACHE_TIMEOUT_POPULAR = 600       # 10 minutes for popular queries


def get_cache_key(prefix: str, *args) -> str:
    """
    Generate a consistent cache key from arguments.
    """
    key_data = ':'.join(str(arg) for arg in args if arg)
    hash_suffix = hashlib.md5(key_data.encode()).hexdigest()[:12]
    return f'{prefix}:{hash_suffix}'


def cache_facets(queryset, cache_key_prefix: str = 'facets'):
    """
    Cache facet count calculations.
    Returns cached facets or calculates and caches them.
    """
    from django.db.models import Count
    
    cache_key = f'search:{cache_key_prefix}:all'
    cached = cache.get(cache_key)
    
    if cached is not None:
        return cached
    
    # Calculate facets from base queryset (all published)
    facets = {
        'expedition': dict(queryset.values('expedition_type').annotate(count=Count('id')).values_list('expedition_type', 'count')),
        'category': dict(queryset.values('category').annotate(count=Count('id')).values_list('category', 'count')),
        'iso': dict(queryset.values('iso_topic').annotate(count=Count('id')).values_list('iso_topic', 'count')),
        'year': dict(queryset.values('expedition_year').annotate(count=Count('id')).values_list('expedition_year', 'count')),
    }
    
    cache.set(cache_key, facets, timeout=CACHE_TIMEOUT_FACETS)
    return facets


def cache_search_results(cache_key: str, results_func):
    """
    Cache first page of search results.
    """
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    results = results_func()
    cache.set(cache_key, results, timeout=CACHE_TIMEOUT_RESULTS)
    return results


def invalidate_search_cache():
    """
    Invalidate all search-related caches.
    Call this when datasets are published/updated/deleted.
    """
    cache_keys_to_clear = [
        'search:facets:all',
    ]
    
    for key in cache_keys_to_clear:
        cache.delete(key)
    
    # Also try to clear with pattern if supported
    try:
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern('search:*')
            # Clear AI search caches too
            cache.delete_pattern('ai_answer:*')
            cache.delete_pattern('ai_parse:*')
            cache.delete_pattern('ai_suggest:*')
            cache.delete_pattern('ai_summary:*')
    except Exception:
        pass


def get_cached_or_compute(cache_key: str, compute_func, timeout: int = 300):
    """
    Generic cache helper: get from cache or compute and store.
    """
    result = cache.get(cache_key)
    if result is not None:
        return result, True  # result, from_cache
    
    result = compute_func()
    cache.set(cache_key, result, timeout=timeout)
    return result, False
