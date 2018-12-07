# Copyright (c) 2008 Joost Cassee
# Licensed under the terms of the MIT License (see LICENSE.txt)

django_reverse = None

def patch_reverse():
    global django_reverse
    from django import urls
    from django.conf import settings
    from django.core import urlresolvers
    from django.utils import translation
    import localeurl.settings
    from localeurl import utils    

    if not django_reverse and localeurl.settings.URL_TYPE == 'path_prefix' and settings.USE_I18N:
        def reverse(*args, **kwargs):
            no_locale = kwargs.pop('no_locale', False)
            locale = translation.get_language()
            path = django_reverse(*args, **kwargs)
            if not locale or no_locale:
                return path
            return utils.locale_url(path, utils.supported_language(locale))
        
        django_reverse = urls.reverse
        urlresolvers.reverse = reverse
        urls.reverse = reverse
