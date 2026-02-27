from django.urls import path
from . import views

app_name = 'data_submission'

urlpatterns = [
    # User views
    path('submit/instructions/', views.submission_instructions, name='instructions'),
    path('submit/', views.submit_dataset, name='submit_dataset'),
    path('submit/upload/<int:submission_id>/', views.upload_dataset_files, name='upload_dataset_files'),
    path('success/<int:submission_id>/', views.submission_success, name='submission_success'),
    path('my-submissions/', views.my_submissions, name='my_submissions'),
    path('view/<int:submission_id>/', views.view_submission, name='view_submission'),

    # AJAX endpoints
    path('ajax/load-states/', views.load_states, name='ajax_load_states'),

    # AI-powered API endpoints
    path('api/ai-classify/', views.ai_classify_view, name='ai_classify'),
    path('api/ai-keywords/', views.ai_keywords_view, name='ai_keywords'),
    path('api/ai-check-abstract/', views.ai_check_abstract_view, name='ai_check_abstract'),
    path('api/ai-extract-spatial/', views.ai_extract_spatial_view, name='ai_extract_spatial'),
    path('api/ai-prefill/', views.ai_prefill_view, name='ai_prefill'),
    path('api/ai-generate-title/', views.ai_generate_title_view, name='ai_generate_title'),
    path('api/ai-generate-purpose/', views.ai_generate_purpose_view, name='ai_generate_purpose'),
    path('api/ai-suggest-resolution/', views.ai_suggest_resolution_view, name='ai_suggest_resolution'),
    path('api/ai-review-assist/', views.ai_review_assist_view, name='ai_review_assist'),

    # Admin / reviewer views
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/review/', views.review_submissions, name='review_submissions'),
    path(
        'admin/review/<int:submission_id>/',
        views.review_submission_detail,
        name='review_submission_detail'
    ),
    path(
        'admin/edit/<int:submission_id>/',
        views.admin_edit_submission,
        name='admin_edit_submission'
    ),
]
