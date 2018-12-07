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

from django.conf.urls import url

from auth import views

urlpatterns = [
    url(r'^login/$', views.login, name='login'),
    url(r'^confirm_create/(?P<account_type>\w+)/(?P<email>[^\/]+)/$', views.confirm_create_user, name='confirm_create_user'),
    url(r'^create/$', views.create_user, name='create_user'),
    url(r'^delete/$', views.delete_user, name='delete_user'),
    url(r'^login_post/$', views.login_post, name='login_post'),
    url(r'confirm_email/(?P<confirmation_key>\w+)/$', views.confirm_email, name='confirm_email'),
    url(r'auto-login/(?P<token>[\w]{40})/$', views.token_login, name='token-login'),
    url(r'resend_confirmation_email/$', views.resend_confirmation_email, name='resend_confirmation_email'),
    url(r'login-trap/$', views.login_trap, name='login_trap'),
    url(r'set-hidden-message-id/$', views.set_hidden_message_id,
        name='set-hidden-message-id'),
]
