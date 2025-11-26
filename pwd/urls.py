# [BACKEND] URL routing for PWD
# URL routing for pwd app

from django.urls import path
from . import views

app_name = 'pwd'

urlpatterns = [
    #dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    #PWD management
    path('', views.pwd_list_view, name='pwd_list'),
    path('create/', views.pwd_create_view, name='pwd_create'),
    path('<int:pwd_id>/', views.pwd_detail_view, name='pwd_detail'),

    path('<int:pwd_id>/edit/', views.pwd_edit_view, name='pwd_edit'),
    path('<int:pwd_id>/toggle-status/', views.pwd_toggle_status_view, name='pwd_toggle_status'),
    path('<int:pwd_id>/documents/<int:doc_id>/delete/', views.pwd_delete_document_view, name='pwd_delete_document'),
]