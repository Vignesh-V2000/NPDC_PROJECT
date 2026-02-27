from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact-us/', views.contact_us, name='contact_us'),
    path('data-policy/', views.data_policy, name='data_policy'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path("login-redirect/", views.login_redirect, name="login_redirect"),
    path("staff/user-approval/", views.user_approval_dashboard, name="user_approval_dashboard"),
    path("staff/approve-user/<int:user_id>/", views.approve_user, name="approve_user"),
    path("staff/reject-user/<int:user_id>/", views.reject_user, name="reject_user"),
    path("staff/create-user/", views.admin_create_user, name="admin_create_user"),
    path("staff/user/<int:user_id>/", views.view_user_details, name="view_user_details"),
    path("staff/user/<int:user_id>/edit/", views.edit_user_details, name="edit_user_details"),
    path("staff/user/<int:user_id>/change-password/", views.admin_change_user_password, name="admin_change_user_password"),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('polar-directory/', views.polar_directory, name='polar_directory'),
    path('api/summary-table/', views.api_summary_table, name='api_summary_table'),
    path('station/<str:station_name>/', views.station_detail, name='station_detail'),

]

# Force reload
