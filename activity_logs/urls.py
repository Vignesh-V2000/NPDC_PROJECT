from django.urls import path
from .views import SystemLogListView

app_name = 'activity_logs'

urlpatterns = [
    path('system-logs/', SystemLogListView.as_view(), name='system_logs'),
]
