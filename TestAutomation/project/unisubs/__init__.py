import sys
import os
import pkgutil
sys.path.insert(0, '.')

__path__ = pkgutil.extend_path(__path__, __name__)
for importer, modname, ispkg in pkgutil.walk_packages(path=__path__, prefix=__name__+'.'):
    __import__(modname)

os.environ['DJANGO_SETTINGS_MODULE'] = 'unisubs.dev_settings'
import django
django.setup()
