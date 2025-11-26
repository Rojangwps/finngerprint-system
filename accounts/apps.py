# [BACKEND] Accounts app configuration


# accounts/apps.py
# Accounts app configuration

from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'