from django import template
from django.conf import settings

register = template.Library()


@register.filter
def cached_url(file_url):
    """Prepend Squid reverse-proxy prefix to a file URL for local-dev caching.

    In production (DEBUG=False) the prefix is empty, so URLs are unchanged.
    """
    prefix = getattr(settings, 'SQUID_CACHE_URL_PREFIX', '')
    if prefix and file_url:
        return f"{prefix}{file_url}"
    return file_url
