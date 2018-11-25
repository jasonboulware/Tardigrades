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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

import logging

from django import template
from django.utils.translation import get_language

from auth.models import AnonymousUserCacheGroup

register = template.Library()

logger = logging.getLogger('caching.amara_cache')

def cache_by_tag(parser, token, CacheNodeClass):
    nodelist = parser.parse(('endcache',))
    try:
        tag_name, key = token.split_contents()
    except ValueError:
        tag_name = token.contents.split()[0]
        msg = "{0} tag requires a cache key as an single argument".format(
            tag_name)
        raise template.TemplateSyntaxError(msg)
    parser.delete_first_token()
    key += '-{}'.format(get_language())
    return CacheNodeClass(key, nodelist)

@register.tag('cache-by-user')
def cache_by_user(parser, token):
    return cache_by_tag(parser, token, CacheByUserNode)

@register.tag('cache-by-video')
def cache_by_video(parser, token):
    return cache_by_tag(parser, token, CacheByVideoNode)

class CacheNode(template.Node):
    def __init__(self, key, nodelist):
        self.key = key
        self.nodelist = nodelist

    def render(self, context):
        try:
            cache_group = self.get_cache_group(context)
        except StandardError:
            logger.warn("error getting cache group", exc_info=True)
            return self.nodelist.render(context)
        content = cache_group.get(self.key)
        if content is None:
            content = self.nodelist.render(context)
            cache_group.set(self.key, content)
        return content

class CacheByUserNode(CacheNode):
    def get_cache_group(self, context):
        user = context['request'].user
        if user.is_authenticated():
            return user.cache
        else:
            return AnonymousUserCacheGroup()

class CacheByVideoNode(CacheNode):
    def get_cache_group(self, context):
        return context['video'].cache
