from django.views.generic import ListView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponse
from django.db.models import Q, Count, Sum, Avg
from datetime import datetime, timedelta
from django.utils import timezone
import csv
from .models import ActivityLog, SiteHit
from django.contrib.auth.models import User
from data_submission.models import DatasetSubmission, DatasetRequest
from django.views import View
from django.shortcuts import render


class SystemLogListView(UserPassesTestMixin, ListView):
    model = ActivityLog
    template_name = 'activity_logs/system_log.html'
    context_object_name = 'logs'
    paginate_by = 50

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def get_queryset(self):
        queryset = ActivityLog.objects.all().order_by('-action_time')
        
        # Exclude site hits (anonymous ACCESS events) from user activity logs
        queryset = queryset.exclude(actor__isnull=True, action_type='ACCESS')
        
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
            if user_id == 'anonymous':
                queryset = queryset.filter(actor__isnull=True)
            else:
                queryset = queryset.filter(actor_id=user_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'User Activity Logs'
        context['is_site_hits'] = False
        # Get unique action types for filter dropdown
        context['action_types'] = ActivityLog.objects.values_list('action_type', flat=True).distinct().order_by('action_type')
        # Get action type display
        context['action_type_choices'] = ActivityLog._meta.get_field('action_type').choices
        # Get unique users for filter dropdown (excluding anonymous)
        from django.contrib.auth.models import User
        context['users'] = User.objects.filter(is_staff=True).order_by('username')
        
        # Current filter values
        context['selected_action'] = self.request.GET.get('action_type', '')
        context['selected_user'] = self.request.GET.get('user', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        
        return context


class SiteHitListView(UserPassesTestMixin, ListView):
    model = SiteHit
    template_name = 'activity_logs/system_log.html'
    context_object_name = 'logs'
    paginate_by = 50

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        return SiteHit.objects.all().order_by('-action_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Site Hit Logs'
        context['is_site_hits'] = True
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
                log.actor.username if log.actor else 'anonymous user',
                log.get_action_type_display(),
                log.entity_name or '—',
                log.ip_address or '—',
                log.status or '—',
                log.remarks or '—',
            ])
        
        return response


class SystemReportView(UserPassesTestMixin, View):
    template_name = 'activity_logs/system_report.html'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def _get_date_range(self, request):
        """Parse date_from / date_to from query string."""
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        from_dt, to_dt = None, None
        if date_from:
            try:
                from_dt = datetime.strptime(date_from, '%Y-%m-%d')
            except ValueError:
                pass
        if date_to:
            try:
                to_dt = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            except ValueError:
                pass
        return from_dt, to_dt, date_from, date_to

    def _build_context(self, request):
        from_dt, to_dt, date_from_str, date_to_str = self._get_date_range(request)
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # ── Base querysets (optionally filtered by date) ──
        users_qs = User.objects.all()
        datasets_qs = DatasetSubmission.objects.all()
        requests_qs = DatasetRequest.objects.all()
        logs_qs = ActivityLog.objects.all()

        if from_dt:
            users_qs = users_qs.filter(date_joined__gte=from_dt)
            datasets_qs = datasets_qs.filter(submission_date__gte=from_dt)
            requests_qs = requests_qs.filter(request_date__gte=from_dt)
            logs_qs = logs_qs.filter(action_time__gte=from_dt)

        if to_dt:
            users_qs = users_qs.filter(date_joined__lte=to_dt)
            datasets_qs = datasets_qs.filter(submission_date__lte=to_dt)
            requests_qs = requests_qs.filter(request_date__lte=to_dt)
            logs_qs = logs_qs.filter(action_time__lte=to_dt)

        # ── 1. USER STATISTICS ──
        total_users = User.objects.count()  # always total
        active_users = User.objects.filter(is_active=True).count()
        staff_users = User.objects.filter(is_staff=True).count()
        superusers = User.objects.filter(is_superuser=True).count()
        new_users_30d = User.objects.filter(date_joined__gte=thirty_days_ago).count()
        users_in_range = users_qs.count()

        # ── 2. DATASET SUBMISSIONS ──
        total_datasets = DatasetSubmission.objects.count()
        datasets_in_range = datasets_qs.count()

        # By status
        status_breakdown = list(
            datasets_qs.values('status')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        status_map = dict(DatasetSubmission.STATUS_CHOICES)
        for item in status_breakdown:
            item['label'] = status_map.get(item['status'], item['status'])

        # By expedition type
        expedition_breakdown = list(
            datasets_qs.values('expedition_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        exp_map = dict(DatasetSubmission.EXPEDITION_TYPES)
        for item in expedition_breakdown:
            item['label'] = exp_map.get(item['expedition_type'], item['expedition_type'] or 'Unknown')

        # By category
        category_breakdown = list(
            datasets_qs.exclude(category='').values('category')
            .annotate(count=Count('id'))
            .order_by('-count')[:15]
        )
        cat_map = dict(DatasetSubmission.CATEGORY_CHOICES)
        for item in category_breakdown:
            item['label'] = cat_map.get(item['category'], item['category'])

        # By expedition year (top 10)
        year_breakdown = list(
            datasets_qs.exclude(expedition_year='').values('expedition_year')
            .annotate(count=Count('id'))
            .order_by('-expedition_year')[:10]
        )

        # Monthly trend (last 12 months – not affected by filters)
        monthly_submissions = []
        for i in range(11, -1, -1):
            month_start = (now - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i > 0:
                month_end = (now - timedelta(days=30 * (i - 1))).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                month_end = now
            count = DatasetSubmission.objects.filter(
                submission_date__gte=month_start,
                submission_date__lt=month_end
            ).count()
            monthly_submissions.append({
                'month': month_start.strftime('%b %Y'),
                'count': count
            })

        # Storage stats
        storage = DatasetSubmission.objects.aggregate(
            total_size=Sum('file_size_mb'),
            avg_size=Avg('file_size_mb')
        )

        # ── 3. DATA REQUESTS ──
        total_requests = DatasetRequest.objects.count()
        requests_in_range = requests_qs.count()

        request_status_breakdown = list(
            requests_qs.values('status')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        req_status_map = dict(DatasetRequest.STATUS_CHOICES)
        for item in request_status_breakdown:
            item['label'] = req_status_map.get(item['status'], item['status'])

        # Top requested datasets
        top_datasets = list(
            requests_qs.values('dataset__metadata_id', 'dataset__title')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Requests by country
        country_breakdown = list(
            requests_qs.exclude(country='').values('country')
            .annotate(count=Count('id'))
            .order_by('-count')[:15]
        )

        # Requests by institute
        institute_breakdown = list(
            requests_qs.exclude(institute='').values('institute')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # ── 4. ACTIVITY LOGS ──
        total_logs = ActivityLog.objects.count()
        logs_in_range = logs_qs.count()
        logs_30d = ActivityLog.objects.filter(action_time__gte=thirty_days_ago).count()

        action_type_breakdown = list(
            logs_qs.values('action_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        try:
            action_choices = dict(ActivityLog._meta.get_field('action_type').choices)
        except Exception:
            action_choices = {}
        for item in action_type_breakdown:
            item['label'] = action_choices.get(item['action_type'], item['action_type'])

        # ── 5. DATASETS BY EXPEDITION TYPE + STATUS CROSS TAB ──
        exp_status_cross = []
        for exp_key, exp_label in DatasetSubmission.EXPEDITION_TYPES:
            row = {'expedition': exp_label}
            exp_datasets = datasets_qs.filter(expedition_type=exp_key)
            row['total'] = exp_datasets.count()
            status_counts = []
            for st_key, st_label in DatasetSubmission.STATUS_CHOICES:
                status_counts.append({
                    'key': st_key,
                    'label': st_label,
                    'count': exp_datasets.filter(status=st_key).count()
                })
            row['status_counts'] = status_counts
            exp_status_cross.append(row)

        context = {
            'date_from': date_from_str,
            'date_to': date_to_str,
            # Users
            'total_users': total_users,
            'active_users': active_users,
            'staff_users': staff_users,
            'superusers': superusers,
            'new_users_30d': new_users_30d,
            'users_in_range': users_in_range,
            # Datasets
            'total_datasets': total_datasets,
            'datasets_in_range': datasets_in_range,
            'status_breakdown': status_breakdown,
            'expedition_breakdown': expedition_breakdown,
            'category_breakdown': category_breakdown,
            'year_breakdown': year_breakdown,
            'monthly_submissions': monthly_submissions,
            'storage_total': round(storage['total_size'] or 0, 2),
            'storage_avg': round(storage['avg_size'] or 0, 2),
            # Data Requests
            'total_requests': total_requests,
            'requests_in_range': requests_in_range,
            'request_status_breakdown': request_status_breakdown,
            'top_datasets': top_datasets,
            'country_breakdown': country_breakdown,
            'institute_breakdown': institute_breakdown,
            # Logs
            'total_logs': total_logs,
            'logs_in_range': logs_in_range,
            'logs_30d': logs_30d,
            'action_type_breakdown': action_type_breakdown,
            # Cross tab
            'exp_status_cross': exp_status_cross,
            'status_choices': DatasetSubmission.STATUS_CHOICES,
        }
        return context

    def get(self, request):
        export = request.GET.get('export', '')
        if export:
            return self._export_section(request, export)
        context = self._build_context(request)
        context['expedition_types'] = DatasetSubmission.EXPEDITION_TYPES
        context['selected_expedition'] = request.GET.get('expedition', '')
        return render(request, self.template_name, context)

    # ── CSV helpers ──

    def _csv_response(self, filename):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def _write_header(self, w, title, ctx):
        w.writerow([f'NPDC {title}'])
        w.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        if ctx.get('date_from') or ctx.get('date_to'):
            w.writerow(['Date Range', f"{ctx.get('date_from') or 'Start'} to {ctx.get('date_to') or 'Now'}"])
        w.writerow([])

    def _export_section(self, request, section):
        ctx = self._build_context(request)
        expedition_filter = request.GET.get('expedition', '')

        if section == 'users':
            return self._export_users(ctx)
        elif section == 'datasets':
            return self._export_datasets(ctx, expedition_filter)
        elif section == 'requests':
            return self._export_requests(ctx)
        elif section == 'logs':
            return self._export_logs(ctx)
        elif section == 'storage':
            return self._export_storage(ctx)
        else:
            return self._export_full(ctx)

    def _export_users(self, ctx):
        response = self._csv_response('user_statistics_report.csv')
        w = csv.writer(response)
        self._write_header(w, 'User Statistics Report', ctx)
        w.writerow(['Metric', 'Value'])
        w.writerow(['Total Users', ctx['total_users']])
        w.writerow(['Active Users', ctx['active_users']])
        w.writerow(['Staff Users', ctx['staff_users']])
        w.writerow(['Superusers', ctx['superusers']])
        w.writerow(['New Users (Last 30 Days)', ctx['new_users_30d']])
        return response

    def _export_datasets(self, ctx, expedition_filter=''):
        exp_map = dict(DatasetSubmission.EXPEDITION_TYPES)
        if expedition_filter and expedition_filter in exp_map:
            label = exp_map[expedition_filter]
            fname = f'datasets_{expedition_filter}_report.csv'
            ds_qs = DatasetSubmission.objects.filter(expedition_type=expedition_filter)
        else:
            label = 'All Expeditions'
            fname = 'datasets_full_report.csv'
            ds_qs = DatasetSubmission.objects.all()

        response = self._csv_response(fname)
        w = csv.writer(response)
        self._write_header(w, f'Dataset Submissions Report - {label}', ctx)

        total = ds_qs.count()
        w.writerow(['Total Datasets', total])
        w.writerow([])

        w.writerow(['Status', 'Count'])
        for st_key, st_label in DatasetSubmission.STATUS_CHOICES:
            c = ds_qs.filter(status=st_key).count()
            if c > 0:
                w.writerow([st_label, c])
        w.writerow([])

        w.writerow(['Category', 'Count'])
        cat_map = dict(DatasetSubmission.CATEGORY_CHOICES)
        for item in ds_qs.exclude(category='').values('category').annotate(count=Count('id')).order_by('-count'):
            w.writerow([cat_map.get(item['category'], item['category']), item['count']])
        w.writerow([])

        w.writerow(['Expedition Year', 'Count'])
        for item in ds_qs.exclude(expedition_year='').values('expedition_year').annotate(count=Count('id')).order_by('-expedition_year')[:15]:
            w.writerow([item['expedition_year'], item['count']])
        w.writerow([])

        w.writerow(['Metadata ID', 'Title', 'Status', 'Expedition Type', 'Expedition Year', 'Category', 'Submitter', 'Submission Date'])
        for ds in ds_qs.select_related('submitter').order_by('-submission_date')[:500]:
            w.writerow([
                ds.metadata_id or '',
                ds.title or '',
                ds.get_status_display(),
                ds.get_expedition_type_display() if ds.expedition_type else '',
                ds.expedition_year or '',
                dict(DatasetSubmission.CATEGORY_CHOICES).get(ds.category, ds.category),
                ds.submitter.get_full_name() or ds.submitter.username,
                ds.submission_date.strftime('%Y-%m-%d') if ds.submission_date else '',
            ])
        return response

    def _export_requests(self, ctx):
        response = self._csv_response('data_requests_report.csv')
        w = csv.writer(response)
        self._write_header(w, 'Data Requests Report', ctx)

        w.writerow(['Total Requests', ctx['total_requests']])
        w.writerow([])
        w.writerow(['Status', 'Count'])
        for item in ctx['request_status_breakdown']:
            w.writerow([item['label'], item['count']])
        w.writerow([])
        w.writerow(['Top Requested Datasets'])
        w.writerow(['Dataset Title', 'Metadata ID', 'Request Count'])
        for item in ctx['top_datasets']:
            w.writerow([item['dataset__title'], item['dataset__metadata_id'], item['count']])
        w.writerow([])
        w.writerow(['Requests by Country'])
        w.writerow(['Country', 'Count'])
        for item in ctx['country_breakdown']:
            w.writerow([item['country'], item['count']])
        w.writerow([])
        w.writerow(['Requests by Institute'])
        w.writerow(['Institute', 'Count'])
        for item in ctx['institute_breakdown']:
            w.writerow([item['institute'], item['count']])
        w.writerow([])
        w.writerow(['All Requests'])
        w.writerow(['Date', 'Name', 'Email', 'Institute', 'Country', 'Research Area', 'Dataset', 'Metadata ID', 'Status'])
        for req in DatasetRequest.objects.select_related('dataset').order_by('-request_date')[:500]:
            w.writerow([
                req.request_date.strftime('%Y-%m-%d') if req.request_date else '',
                f"{req.first_name} {req.last_name}",
                req.email, req.institute, req.country, req.research_area,
                req.dataset.title if req.dataset else '',
                req.dataset.metadata_id if req.dataset else '',
                req.get_status_display(),
            ])
        return response

    def _export_logs(self, ctx):
        response = self._csv_response('activity_logs_report.csv')
        w = csv.writer(response)
        self._write_header(w, 'Activity Logs Report', ctx)
        w.writerow(['Total Logs', ctx['total_logs']])
        w.writerow(['Logs (Last 30 Days)', ctx['logs_30d']])
        w.writerow([])
        w.writerow(['Action Type', 'Count'])
        for item in ctx['action_type_breakdown']:
            w.writerow([item['label'], item['count']])
        return response

    def _export_storage(self, ctx):
        response = self._csv_response('storage_report.csv')
        w = csv.writer(response)
        self._write_header(w, 'Storage Report', ctx)
        w.writerow(['Metric', 'Value'])
        w.writerow(['Total Dataset Storage (MB)', ctx['storage_total']])
        w.writerow(['Average per Dataset (MB)', ctx['storage_avg']])
        w.writerow([])
        w.writerow(['Storage by Expedition Type'])
        w.writerow(['Expedition', 'Total Size (MB)', 'Dataset Count'])
        for exp_key, exp_label in DatasetSubmission.EXPEDITION_TYPES:
            agg = DatasetSubmission.objects.filter(expedition_type=exp_key).aggregate(
                total=Sum('file_size_mb'), cnt=Count('id')
            )
            w.writerow([exp_label, round(agg['total'] or 0, 2), agg['cnt']])
        return response

    def _export_full(self, ctx):
        response = self._csv_response('system_full_report.csv')
        w = csv.writer(response)
        self._write_header(w, 'Full System Report', ctx)

        w.writerow(['=== USER STATISTICS ==='])
        w.writerow(['Total Users', ctx['total_users']])
        w.writerow(['Active Users', ctx['active_users']])
        w.writerow(['Staff Users', ctx['staff_users']])
        w.writerow(['Superusers', ctx['superusers']])
        w.writerow(['New Users (Last 30 Days)', ctx['new_users_30d']])
        w.writerow([])

        w.writerow(['=== DATASET SUBMISSIONS ==='])
        w.writerow(['Total Datasets', ctx['total_datasets']])
        w.writerow([])
        w.writerow(['Status', 'Count'])
        for item in ctx['status_breakdown']:
            w.writerow([item['label'], item['count']])
        w.writerow([])
        w.writerow(['Expedition Type', 'Count'])
        for item in ctx['expedition_breakdown']:
            w.writerow([item['label'], item['count']])
        w.writerow([])

        w.writerow(['=== DATASETS BY EXPEDITION x STATUS ==='])
        if ctx['exp_status_cross']:
            header = ['Expedition', 'Total'] + [sc['label'] for sc in ctx['exp_status_cross'][0]['status_counts']]
        else:
            header = ['Expedition', 'Total']
        w.writerow(header)
        for row in ctx['exp_status_cross']:
            line = [row['expedition'], row['total']]
            for sc in row['status_counts']:
                line.append(sc['count'])
            w.writerow(line)
        w.writerow([])

        w.writerow(['=== DATA REQUESTS ==='])
        w.writerow(['Total Requests', ctx['total_requests']])
        w.writerow([])
        w.writerow(['Request Status', 'Count'])
        for item in ctx['request_status_breakdown']:
            w.writerow([item['label'], item['count']])
        w.writerow([])
        w.writerow(['Country', 'Requests'])
        for item in ctx['country_breakdown']:
            w.writerow([item['country'], item['count']])
        w.writerow([])

        w.writerow(['=== ACTIVITY LOGS ==='])
        w.writerow(['Total Logs', ctx['total_logs']])
        w.writerow(['Logs (Last 30 Days)', ctx['logs_30d']])
        w.writerow([])
        w.writerow(['Action Type', 'Count'])
        for item in ctx['action_type_breakdown']:
            w.writerow([item['label'], item['count']])

        return response


