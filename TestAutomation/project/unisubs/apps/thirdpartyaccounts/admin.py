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

from django.contrib import admin

from thirdpartyaccounts.models import TwitterAccount, FacebookAccount


class TwitterAccountAdmin(admin.ModelAdmin):
    search_fields = ('username', 'user__username', 'user__email')
    list_display = ('twitter_username', 'amara_user')
    list_filter = ('created', 'modified')
    raw_id_fields = ['user']
    readonly_fields = ['last_login']

    def twitter_username(self, o):
        return '@%s' % o.username
    twitter_username.admin_order_field = 'username'

    def amara_user(self, o):
        return o.user.username
    amara_user.admin_order_field = 'user__username'
    amara_user.short_description = 'Amara User'

class FacebookAccountAdmin(admin.ModelAdmin):
    search_fields = ('uid', 'user__username', 'user__email')
    list_display = ('facebook_uid', 'amara_user')
    list_filter = ('created', 'modified')
    raw_id_fields = ['user']
    readonly_fields = ['last_login']

    def facebook_uid(self, o):
        return o.uid
    facebook_uid.admin_order_field = 'uid'
    facebook_uid.short_description = 'Facebook UID'

    def amara_user(self, o):
        return o.user.username
    amara_user.admin_order_field = 'user__username'
    amara_user.short_description = 'Amara User'


admin.site.register(TwitterAccount, TwitterAccountAdmin)
admin.site.register(FacebookAccount, FacebookAccountAdmin)
