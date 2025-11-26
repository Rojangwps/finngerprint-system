# [BACKEND] URL routing for accounts

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    #login/logout
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    
    #registration (5 steps)
    path('register/step1/', views.register_step1_view, name='register_step1'),
    path('register/step2/', views.register_step2_view, name='register_step2'),
    path('register/step3/', views.register_step3_view, name='register_step3'),
    path('register/step4/', views.register_step4_view, name='register_step4'),
    path('register/step5/', views.register_step5_view, name='register_step5'),
    path('register/success/', views.register_success_view, name='register_success'),

    #user management (Admin)
    path('users/', views.user_list_view, name='user_list'),
    path('users/<int:user_id>/', views.user_detail_view, name='user_detail'),
    path('users/<int:user_id>/verify/', views.verify_user_view, name='verify_user'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status_view, name='toggle_user_status'),

    #pass management
    path('change-password/', views.change_password_view, name='change_password'),
    path('forgot-password/', views.forgot_password_step1_view, name='forgot_password_step1'),
    path('forgot-password/security-question/', views.forgot_password_step2_view, name='forgot_password_step2'),
    path('forgot-password/reset/', views.forgot_password_step3_view, name='forgot_password_step3'),

    #edit prof
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('users/<int:user_id>/reset-password/', views.admin_reset_password_view, name='admin_reset_password'),
    path('audit-log/', views.audit_log_view, name='audit_log'),
]