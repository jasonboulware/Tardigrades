# Amara, universalsubtitles.org
#
# Copyright (C) 2014 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

import os

from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static

from staticmedia import views
from staticmedia import utils

if settings.STATIC_MEDIA_USES_S3:
    # don't serve up the media from the local server if we're using S3
    urlpatterns = []
else:
    # mimic the S3 directory structure using views from the local server
    urlpatterns = [
        # Special case requirejs since we might want to use it for different
        # JS bundles
        url(r'^js/require.js$', views.requirejs, name='requirejs'),
        url(r'^css/(?P<bundle_name>[\w\.-]+)$', views.css_bundle, name='css_bundle'),
        url(r'^js/(?P<bundle_name>[\w\.-]+)$', views.js_bundle, name='js_bundle'),
        url(r'^js/(?P<bundle_name>[\w\.-]+)/(?P<path>.*)$',
            views.js_bundle_with_path, name='js_bundle_with_path'),
        url(r'^jsi18catalog/(?P<locale>[\w-]+)\.js$', views.js_i18n_catalog,
            name='js_i18n_catalog'),
        url(r'^jslanguagedata/(?P<locale>[\w-]+)\.js$',
            views.js_language_data, name='js_language_data'),
        # embed.js is a weird file, but we want to continue support for a
        # while
        url(r'^embed.js$', views.old_embedder_js, name='old_embedder_js'),
    ] + static(
        '/images/', document_root=os.path.join(settings.STATIC_ROOT, 'images')
    ) + static(
        '/flowplayer/', document_root=os.path.join(settings.STATIC_ROOT, 'flowplayer')
    ) + static(
        '/fonts/', document_root=os.path.join(settings.STATIC_ROOT, 'fonts')
    )

    urlpatterns += [
        url(r'^(?P<path>.*)$', views.serve_add_static_media)
    ]

if settings.DEBUG:
    urlpatterns += [
        url(r'^test/old-embedder/$', views.old_embedder_test,
            name='old_embedder_test'),
        url(r'^test/embedder/$', views.embedder_test, name='embedder_test'),
    ]
