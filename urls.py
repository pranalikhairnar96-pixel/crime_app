from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'dashboard'

urlpatterns = [
    # ========== Main/Index ==========
    path('', views.index, name='index'),
    
    # ========== Landing & Authentication ==========
    path('landing/', views.landing, name='landing'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup, name='signup'),
    path('role-select/', views.role_select, name='role_select'),
    
    # ========== Citizen Registration & Login ==========
    path('citizen/signup/', views.citizen_signup, name='citizen_signup'),
    path('citizen/login/', views.citizen_login, name='citizen_login'),
    path('citizen/complete-profile/', views.complete_citizen_profile, name='complete_citizen_profile'),
    
    # ========== Police Officer Login ==========
    path('police/login/', views.police_login, name='police_login'),
    
    # ========== Password Reset ==========
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    
    # ========== Citizen Views ==========
    path('citizen/home/', views.citizen_homepage, name='citizen_home'),
    path('citizen/report-crime/', views.report_crime, name='report_crime'),
    path('citizen/my-reports/', views.my_reports, name='my_reports'),
    
    # ========== Police Officer Views ==========
    path('police/home/', views.police_homepage, name='police_home'),
    path('police/reports/', views.view_reports, name='police_reports'),
    path('report/<int:report_id>/', views.report_detail, name='report_detail'),
    path('police/report/<int:report_id>/update/', views.update_report, name='update_report'),
    path('police/notifications/', views.notifications, name='notifications'),
    path('police/notification/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    
    # ========== Dashboard & Analytics ==========
    path('heatmap/', views.heatmap_view, name='heatmap'),
    path('prediction/', views.prediction_view, name='prediction'),
    path('patrol/', views.patrol_view, name='patrol'),
    path('ranking/', views.ranking_view, name='ranking'),
]
