import sys
import os
import pkgutil
sys.path.insert(0, '.')

import django
from django.conf import settings
import dev_settings
import apps

django.conf.settings.configure(default_settings=dev_settings, DEBUG=True)
django.setup()

for importer, modname, ispkg in pkgutil.walk_packages(path=__path__, prefix=__name__+'.'):
    __import__(modname)
