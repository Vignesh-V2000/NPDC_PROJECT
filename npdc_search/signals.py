"""
Signals for the search module.
Handles cache invalidation when datasets are modified.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from data_submission.models import DatasetSubmission
from .security import invalidate_search_cache


@receiver(post_save, sender=DatasetSubmission)
def invalidate_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate search cache when a dataset is created or updated.
    """
    if instance.status == 'published' or (hasattr(instance, '_original_status') and 
                                           instance._original_status != 'published' and 
                                           instance.status == 'published'):
        invalidate_search_cache()


@receiver(post_delete, sender=DatasetSubmission)
def invalidate_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate search cache when a dataset is deleted.
    """
    if instance.status == 'published':
        invalidate_search_cache()
