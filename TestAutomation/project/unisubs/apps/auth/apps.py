import sys
sys.path.insert(0, '/home/williamsjd2/unisubs/apps')
from django.apps import AppConfig

class AuthConfig(AppConfig):
    label = 'amara_auth'
    name = 'auth'
    verbose_name = "Auth"
