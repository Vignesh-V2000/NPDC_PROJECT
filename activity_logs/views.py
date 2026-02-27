from django.views.generic import ListView
from django.contrib.auth.mixins import UserPassesTestMixin
from .models import ActivityLog

class SystemLogListView(UserPassesTestMixin, ListView):
    model = ActivityLog
    template_name = 'activity_logs/system_log.html'
    context_object_name = 'logs'
    paginate_by = 50

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
