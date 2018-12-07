# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
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

from __future__ import absolute_import

from django.conf.urls import url
from django.views.generic.base import TemplateView
import django.contrib.auth.views
import thirdpartyaccounts.views

from utils.genericviews import JSTemplateView

from widget import views

urlpatterns = [
    url(r'^rpc/xd/(\w+)$', views.xd_rpc),
    url(r'^null_rpc/xd/(\w+)$', views.xd_rpc, kwargs={'null':True}),
    url(r'^rpc/xhr/(\w+)$', views.rpc, name='rpc'),
    url(r'^null_rpc/xhr/(\w+)$', views.rpc, kwargs={'null':True}),
    url(r'^rpc/jsonp/(\w+)$', views.jsonp),
    url(r'^null_rpc/jsonp/(\w+)$', views.jsonp, kwargs={'null':True}),
    url(r'^widgetizerbootloader\.js$', views.widgetizerbootloader,
        name='widgetizerbootloader'),
    url(r'^convert_subtitles/$', views.convert_subtitles,
        name='convert_subtitles'),
    url(r'^save_emailed_translations/$',
        views.save_emailed_translations),
]

urlpatterns += [
    url(r'^login/$', django.contrib.auth.views.login),
    url(r'^twitter_login/', thirdpartyaccounts.views.twitter_login,
        kwargs={'next': '/widget/close_window/'}),
    url(r'^facebook_login/', thirdpartyaccounts.views.facebook_login),
    url(r'^close_window/$',
        TemplateView.as_view(template_name='widget/close_window.html')),
    url(r'^config.js$',
        JSTemplateView.as_view(template_name='widget/config.js')),
    url(r'^statwidgetconfig.js$',
        JSTemplateView.as_view(template_name='widget/statwidgetconfig.js')),
    url(r'^extension_demo.html$',
        TemplateView.as_view(template_name='widget/extension_demo.html')),
]
