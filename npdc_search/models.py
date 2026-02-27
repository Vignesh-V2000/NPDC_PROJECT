from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SearchLog(models.Model):
    """
    Logs all search queries for analytics purposes.
    Tracks: keywords, filters, result counts, zero-result searches.
    """
    
    # User info (nullable for anonymous users)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='search_logs'
    )
    
    # Search query
    query = models.CharField(max_length=500, blank=True, default='')
    
    # Filters applied (stored as JSON)
    filters = models.JSONField(default=dict, blank=True)
    
    # Results info
    result_count = models.PositiveIntegerField(default=0)
    is_zero_result = models.BooleanField(default=False)
    
    # Response time (for performance monitoring)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    
    # Metadata
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    
    # Session tracking
    session_key = models.CharField(max_length=40, blank=True, default='')
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['query'], name='searchlog_query_idx'),
            models.Index(fields=['is_zero_result'], name='searchlog_zero_idx'),
            models.Index(fields=['-timestamp'], name='searchlog_time_idx'),
        ]
        verbose_name = 'Search Log'
        verbose_name_plural = 'Search Logs'
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{user_str}: '{self.query}' ({self.result_count} results)"
    
    @classmethod
    def log_search(cls, request, query, filters, result_count, response_time_ms=None):
        """
        Convenience method to create a search log entry.
        """
        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        return cls.objects.create(
            user=request.user if request.user.is_authenticated else None,
            query=query[:500] if query else '',
            filters=filters or {},
            result_count=result_count,
            is_zero_result=result_count == 0,
            response_time_ms=response_time_ms,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            session_key=request.session.session_key or ''
        )
    
    @classmethod
    def get_popular_keywords(cls, days=30, limit=20):
        """
        Get most searched keywords in the last N days.
        """
        from django.db.models import Count
        from django.db.models.functions import Lower
        from datetime import timedelta
        
        since = timezone.now() - timedelta(days=days)
        return cls.objects.filter(
            timestamp__gte=since,
            query__isnull=False
        ).exclude(
            query=''
        ).values(
            keyword=Lower('query')
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:limit]
    
    @classmethod
    def get_zero_result_searches(cls, days=30, limit=20):
        """
        Get searches that returned zero results.
        """
        from django.db.models import Count
        from django.db.models.functions import Lower
        from datetime import timedelta
        
        since = timezone.now() - timedelta(days=days)
        return cls.objects.filter(
            timestamp__gte=since,
            is_zero_result=True,
            query__isnull=False
        ).exclude(
            query=''
        ).values(
            keyword=Lower('query')
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:limit]
    
    @classmethod
    def get_popular_filters(cls, filter_name, days=30, limit=10):
        """
        Get most used values for a specific filter.
        """
        from django.db.models import Count
        from datetime import timedelta
        
        since = timezone.now() - timedelta(days=days)
        logs = cls.objects.filter(timestamp__gte=since)
        
        # Extract filter values from JSONField
        filter_counts = {}
        for log in logs:
            if log.filters and filter_name in log.filters:
                value = log.filters[filter_name]
                if value:
                    filter_counts[value] = filter_counts.get(value, 0) + 1
        
        # Sort by count and return top N
        sorted_filters = sorted(filter_counts.items(), key=lambda x: -x[1])
        return sorted_filters[:limit]
    
    @classmethod
    def get_search_stats(cls, days=30):
        """
        Get overall search statistics.
        """
        from django.db.models import Avg, Count, Sum
        from datetime import timedelta
        
        since = timezone.now() - timedelta(days=days)
        logs = cls.objects.filter(timestamp__gte=since)
        
        total_searches = logs.count()
        zero_result_count = logs.filter(is_zero_result=True).count()
        avg_results = logs.aggregate(avg=Avg('result_count'))['avg'] or 0
        avg_response_time = logs.aggregate(avg=Avg('response_time_ms'))['avg'] or 0
        unique_users = logs.exclude(user__isnull=True).values('user').distinct().count()
        
        return {
            'total_searches': total_searches,
            'zero_result_count': zero_result_count,
            'zero_result_rate': (zero_result_count / total_searches * 100) if total_searches > 0 else 0,
            'avg_results_per_search': round(avg_results, 1),
            'avg_response_time_ms': round(avg_response_time, 1),
            'unique_users': unique_users,
        }
