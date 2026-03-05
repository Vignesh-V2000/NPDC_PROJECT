from django.views.generic import ListView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponse
from django.db.models import Q
from datetime import datetime, timedelta
import csv
from .models import ActivityLog
from django.contrib.auth.models import User
from data_submission.models import DatasetSubmission
from django.views import View

class SystemLogListView(UserPassesTestMixin, ListView):
    model = ActivityLog
    template_name = 'activity_logs/system_log.html'
    context_object_name = 'logs'
    paginate_by = 50

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def get_queryset(self):
        queryset = ActivityLog.objects.all().order_by('-action_time')
        
        # Filter by action type
        action_type = self.request.GET.get('action_type', '')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(action_time__gte=from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d')
                to_date = to_date.replace(hour=23, minute=59, second=59)
                queryset = queryset.filter(action_time__lte=to_date)
            except ValueError:
                pass
        
        # Filter by user
        user_id = self.request.GET.get('user', '')
        if user_id:
            queryset = queryset.filter(actor_id=user_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get unique action types for filter dropdown
        context['action_types'] = ActivityLog.objects.values_list('action_type', flat=True).distinct().order_by('action_type')
        # Get action type display
        context['action_type_choices'] = ActivityLog._meta.get_field('action_type').choices
        # Get unique users for filter dropdown
        from django.contrib.auth.models import User
        context['users'] = User.objects.filter(is_staff=True).order_by('username')
        
        # Current filter values
        context['selected_action'] = self.request.GET.get('action_type', '')
        context['selected_user'] = self.request.GET.get('user', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        return context
    
    def get(self, request, *args, **kwargs):
        # Handle CSV export
        if request.GET.get('export') == 'csv':
            return self.export_csv()
        return super().get(request, *args, **kwargs)
    
    def export_csv(self):
        queryset = self.get_queryset()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="system_logs.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Time', 'User', 'Action', 'Entity', 'IP Address', 'Status', 'Details'])
        
        for log in queryset:
            writer.writerow([
                log.action_time.strftime('%Y-%m-%d %H:%M:%S') if log.action_time else '',
                log.actor.username if log.actor else 'System',
                log.get_action_type_display(),
                log.entity_name or '—',
                log.ip_address or '—',
                log.status or '—',
                log.remarks or '—',
            ])
        
        return response


class SystemReportView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def get(self, request):
        # Generate system report CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="system_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Metric', 'Value'])
        
        # User statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        staff_users = User.objects.filter(is_staff=True).count()
        superuser_users = User.objects.filter(is_superuser=True).count()
        
        # Users joined in last 30 days
        thirty_days_ago = datetime.now() - timedelta(days=30)
        new_users_30d = User.objects.filter(date_joined__gte=thirty_days_ago).count()
        
        # Dataset statistics
        total_submissions = DatasetSubmission.objects.count()
        published_submissions = DatasetSubmission.objects.filter(status='PUBLISHED').count()
        pending_submissions = DatasetSubmission.objects.filter(status='PENDING').count()
        rejected_submissions = DatasetSubmission.objects.filter(status='REJECTED').count()
        
        # Activity logs
        total_logs = ActivityLog.objects.count()
        logs_last_30d = ActivityLog.objects.filter(action_time__gte=thirty_days_ago).count()
        
        # Write the data
        writer.writerow(['Total Users', total_users])
        writer.writerow(['Active Users', active_users])
        writer.writerow(['Staff Users', staff_users])
        writer.writerow(['Superuser Users', superuser_users])
        writer.writerow(['New Users (Last 30 Days)', new_users_30d])
        writer.writerow(['Total Dataset Submissions', total_submissions])
        writer.writerow(['Published Datasets', published_submissions])
        writer.writerow(['Pending Datasets', pending_submissions])
        writer.writerow(['Rejected Datasets', rejected_submissions])
        writer.writerow(['Total Activity Logs', total_logs])
        writer.writerow(['Activity Logs (Last 30 Days)', logs_last_30d])
        
        return response
