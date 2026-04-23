from django.urls import path
from . import views

app_name = 'cruise'

urlpatterns = [
    # Cruise summary/listing page
    path('summary/', views.cruise_summary_view, name='summary'),
    
    # Cruise detail page
    path('detail/<int:cruise_id>/', views.cruise_detail, name='detail'),
    
    # AJAX endpoints
    path('api/dropdown/', views.get_cruise_dropdown, name='dropdown_api'),
    path('api/list/', views.cruise_api_list, name='api_list'),
    
    # File download
    path('download/', views.download_cruise_file, name='download'),
]
