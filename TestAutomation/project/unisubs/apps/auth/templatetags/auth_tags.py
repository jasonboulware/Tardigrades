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
from datetime import datetime, timedelta
from django import template
from django.utils.translation import ugettext_lazy as _


register = template.Library()

@register.inclusion_tag('auth/_new_user_notification.html', takes_context=True)
def new_user_notification(context, force=False):
    """
    To make clear to users when authenticating with an
    external service actually created a new account
    """
    user = context['request'].user
    if user.is_authenticated() and user.date_joined > datetime.now() - timedelta(minutes=2) and user.is_external:
        context['new_user'] = True
    return context

@register.inclusion_tag('auth/_email_confirmation_notification.html', takes_context=True)
def email_confirmation_notification(context, force=False):
    user = context['request'].user
    content = ''
    if user.is_authenticated():
        if not user.email:
            content = _(u'Fill email field, please.')
        elif not user.valid_email:
            content = _(u'Confirm your email, please.')

    context['notification_content'] = content
    return context

@register.filter
def show_youtube_prompt(request):
    """
    Returns a boolean for whether to show the Youtube syncing prompt.

    Current logic is that we show it for:
        * unauthenticated visitors
        * authenticated users who haven't synced a YT account and haven't
          dismissed the prompt
    """

    if request.COOKIES.get('hide-yt-prompt') == 'yes':
        return False

    user = request.user if request.user.is_authenticated() else None

    if not user:
        return True

    accounts = user.third_party_accounts.all()
    types = [a.get_type_display() for a in accounts]

    if 'Youtube' not in types:
        return True
    else:
        return False
