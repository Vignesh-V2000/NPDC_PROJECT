from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class ActivityLog(models.Model):
    ACTION_TYPES = [
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('SUBMIT', 'Submit'),
        ('OTHER', 'Other'),
    ]

    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    action_time = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='SUCCESS')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    entity_name = models.CharField(max_length=100, blank=True, null=True)
    path = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-action_time']
        verbose_name = _('Activity Log')
        verbose_name_plural = _('Activity Logs')

    def __str__(self):
        return f"{self.action_type} by {self.actor} at {self.action_time}"
