from django.urls import path
from . import views

app_name = 'pwd'

urlpatterns = [
    # Primary (namespaced) routes
    path('login/', views.login_view, name='login'),
    path('register/', views.pwd_register_and_login_view, name='register'),
    path('create/', views.pwd_create_view, name='create'),
    path('profile/', views.profile_view, name='profile'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Listing / detail / edit
    path('list/', views.pwd_list_view, name='pwd_list'),
    path('detail/<int:pwd_id>/', views.pwd_detail_view, name='pwd_detail'),
    path('edit/<int:pwd_id>/', views.pwd_edit_view, name='pwd_edit'),
    path('toggle/<int:pwd_id>/', views.pwd_toggle_status_view, name='pwd_toggle_status'),
    path('delete-doc/<int:pwd_id>/<int:doc_id>/', views.pwd_delete_document_view, name='pwd_delete_document'),

    # Fingerprint endpoints
    path('fingerprint/poll/', views.fingerprint_poll, name='fingerprint_poll'),
    path('fingerprint/next-slot/', views.next_fingerprint_slot_view, name='next_fingerprint_slot'),
    path('fingerprint/register/', views.register_fingerprint_view, name='register_fingerprint'),

    # --- Legacy / compatibility names (aliases) ---
    # Keep legacy names so existing templates that use them keep working.
    path('create/', views.pwd_create_view, name='pwd_create'),
    path('list/', views.pwd_list_view, name='list'),
    path('list/', views.pwd_list_view, name='pwdlist'),
    path('detail/<int:pwd_id>/', views.pwd_detail_view, name='pwd_detail_legacy'),
    path('claim/', views.claim_profile_view, name='claim_profile'),
]