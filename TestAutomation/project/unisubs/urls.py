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

import importlib

from django import http
from django.conf.urls import include, url
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import render
from django.template import RequestContext, loader
from django.views.generic.base import TemplateView, RedirectView
from django.views.decorators.clickjacking import xframe_options_exempt
import django.contrib.auth.views
import django.views.static

from auth.forms import CustomPasswordResetForm
from utils.genericviews import JSTemplateView
import optionalapps
import api.views
import auth.views
import crossdomain_views
import teams.views
import videos.views
import views
import widget.views

admin.autodiscover()
admin.site.login = auth.views.login

def calc_homepage_view():
    module_name, func_name = settings.HOMEPAGE_VIEW.rsplit('.', 1)
    mod = importlib.import_module(module_name)
    return getattr(mod, func_name)

urlpatterns = [
    url('^500/$', TemplateView.as_view(template_name='500.html')),
    url('^404/$', TemplateView.as_view(template_name='404.html')),
    url('^robots.txt$', TemplateView.as_view(template_name='robots.txt')),
    url(r'^crossdomain.xml$',
        crossdomain_views.root_crossdomain),
    url(r'^comments/',
        include('comments.urls', namespace='comments')),
    url(r'^messages/',
        include('messages.urls', namespace='messages')),
    # TODO: Not sure what this is.  It's breaking the app under Django 1.4
    # url(r'^pcf-targetter/',
    #     include('targetter.urls', namespace='targetter')),
    url(r'^logout/', auth.views.logout, name='logout'),
    url(r'^errortest', views.errortest, name='errortest'),
    url(r'^one_time_url/(?P<token>.+)$', views.one_time_url, name='one_time_url'),
    url(r'^admin/billing/$', teams.views.billing, name='billing'),
    url(r'^admin/password_reset/$', auth.views.password_reset, name='password_reset'),
    url(r'^password_reset/done/$',
        django.contrib.auth.views.password_reset_done,
        name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/'
        '(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth.views.password_reset_confirm, {'post_reset_redirect': '/reset/done/'}, name='password_reset_confirm'),
    url(r'^reset-external/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        django.contrib.auth.views.password_reset_confirm,
        {'extra_context': {'external_account': True}, 'post_reset_redirect': '/reset/done/'},
        name='password_reset_confirm_external'),
    url(r'^reset/done/$', auth.views.password_reset_complete,
        name='password_reset_complete'),
    url(r'^styleguide/', include('styleguide.urls', namespace='styleguide')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^staff/', include('staff.urls', namespace='staff')),
    url(r'^subtitles/',
        include('subtitles.urls', namespace='subtitles')),
    url(r'^embed(?P<version_no>\d+)?.js$', widget.views.embed,
        name="widget-embed"),
    url(r'^onsite_widget/$',
        widget.views.onsite_widget, name='onsite_widget'),
    url(r'^onsite_widget_resume/$', widget.views.onsite_widget_resume,
        name='onsite_widget_resume'),
    url(r'^widget/', include('widget.urls', namespace='widget',
        app_name='widget')),
    url(r'^search/',
        include('search.urls', 'search')),
    url(r'^community$',
        TemplateView.as_view(template_name='community.html'),
        name='community'),
    url(r'^dfxp-wrapper-test/$',
        TemplateView.as_view(template_name='dfxp-wrapper-test.html'),
        name='dfxp-wrapper-test'),
    url(r'^embedder/$', TemplateView.as_view(template_name='embedder.html'),
        'embedder_page'),
    url(r'^embedder-iframe/$',
        JSTemplateView.as_view(template_name='embedder-iframe.js'),
        name='embedder_iframe'),
    url(r'^embedder-offsite/$',
        TemplateView.as_view(template_name='embedder-offsite.html'),
        name='embedder_page_offsite'),
    url(r'^embedder-widget-iframe/(?P<analytics>.*)', widget.views.embedder_widget, name='embedder_widget'),
    url(r'^streaming-transcript/$',
        TemplateView.as_view(template_name='streaming-transcript.html'),
        name='streaming_transcript_demo'),
    url(r'^w3c/p3p.xml$',
        TemplateView.as_view(template_name='p3p.xml')),
    url(r'^w3c/Policies.xml$',
        TemplateView.as_view(template_name='Policies.xml'),
        name='policy_page'),
    url(r'^about$', TemplateView.as_view(template_name='about.html'),
        name='about_page'),
    url(r'^security', TemplateView.as_view(template_name='security.html'),
        name='security_page'),
    url(r'^get-code/$',
        TemplateView.as_view(template_name='embed_page.html'),
        name='get_code_page'),
    url(r'^dmca$',  TemplateView.as_view(template_name='dmca.html'),
        name='dmca_page'),
    url(r'^faq$',  TemplateView.as_view(template_name='faq.html'),
        name='faq_page'),
    url(r'^terms$', RedirectView.as_view(url='https://about.amara.org/tos/')),
    url(r'^opensubtitles2010$',
        TemplateView.as_view(template_name='opensubtitles2010.html'),
        name='opensubtitles2010_page'),
    url(r'^test-ogg$',
        TemplateView.as_view(template_name='alpha-test01-ogg.htm'),
        name='test-ogg-page'),
    url(r'^test-mp4$',
        TemplateView.as_view(template_name='alpha-test01-mp4.htm'),
        name='test-mp4-page'),
    url(r"helpers/",
        include('testhelpers.urls', namespace='helpers')),
    url(r'^videos/', include('videos.urls', namespace='videos',
        app_name='videos')),
    url(r'^teams/', include('teams.urls', namespace='teams',
        app_name='teams')),
    url(r'^ui/', include('ui.urls', namespace='ui', app_name='ui')),
    url(r'^profiles/', include('profiles.urls', namespace='profiles',
        app_name='profiles')),
    url(r'^externalsites/', include('externalsites.urls',
                                    namespace='externalsites',
                                    app_name='externalsites')),
    url(r'^media/', include('staticmedia.urls',
                            namespace='staticmedia',
                            app_name='staticmedia')),
    url(r'^auth/', include('auth.urls', namespace='auth', app_name='auth')),
    url(r'^auth/', include('thirdpartyaccounts.urls', namespace='thirdpartyaccounts', app_name='thirdpartyaccounts')),
    url(r'^api/', include('api.urls', namespace='api')),
    url(r'^api2/partners/', include('api.urls', namespace='api-legacy')),
    ## Video shortlinks
    url(r'^v/(?P<encoded_pk>\w+)/$', videos.views.shortlink,
        name='shortlink'),
    url(r'^captcha/', include('captcha.urls')),
    url(r'^commit$', RedirectView.as_view(
        url='https://github.com/pculture/unisubs/commit/{}'.format(settings.LAST_COMMIT_GUID))),
    url(r'^django-rq/', include('django_rq.urls')),
    url(r'^$', calc_homepage_view(), name="home"),
]

urlpatterns.extend(optionalapps.get_urlpatterns())

urlpatterns.extend([
    url(r'^api/', api.views.index.not_found, name='api-not-found'),
])

if settings.DEBUG:
    urlpatterns += [
        url(r'^site_media/(?P<path>.*)$', django.views.static.serve,
            {'document_root': settings.STATIC_ROOT, 'show_indexes': True}),
        url(r'^user-data/(?P<path>.*)$', django.views.static.serve,
            {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    ]
try:
    import debug_toolbar
except ImportError:
    pass
else:
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]

def ensure_user(request):
    if not hasattr(request, 'user'):
        request.user = AnonymousUser()

def handler500(request):
    ensure_user(request)
    return render(request, '500.html', status=500)

def handler403(request, exception):
    ensure_user(request)
    return render(request, '403.html', status=403)
