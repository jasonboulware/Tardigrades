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
import functools

from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.translation import get_language
from django import template

register = template.Library()

from staticmedia import utils
from utils.basexconverter import base62
from videos.views import LanguageList
from videos.types import video_type_registrar, VideoTypeError
from videos import permissions, share_utils, video_size

def cached_by_video(cache_prefix):
    """Wrapper function for tags that cache their content per-video.  """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(video, *args, **kwargs):
            cache_key = '{}-{}'.format(cache_prefix, get_language())
            cached = video.cache.get(cache_key)
            if cached:
                return mark_safe(cached)
            computed = func(video, *args, **kwargs)
            video.cache.set(cache_key, computed)
            return computed
        return wrapper
    return decorator

@register.filter
def is_follower(obj, user):
    # obj is Video or SubtitleLanguage
    if not user.is_authenticated():
        return False

    if not obj:
        return False

    return obj.user_is_follower(user)

@register.filter
def can_user_edit_video_urls(video, user):
    return permissions.can_user_edit_video_urls(video, user)

@register.filter
def can_user_resync(video, user):
    return permissions.can_user_resync(video, user)

from django.template.defaulttags import URLNode
class VideoURLNode(URLNode):
    def render(self, video, request):
        if self.asvar:
            context[self.asvar]= urlparse.urljoin(domain, context[self.asvar])
            return ''
        else:
            return urlparse.urljoin(domain, path)
        path = super(AbsoluteURLNode, self).render(context)

        return urlparse.urljoin(domain, path)

def video_url(parser, token, node_cls=VideoURLNode):
    """
    Does the logic to decide if a video must have a secret url passed into it or not.
    If video must be acceceed thourgh private url, the 40chars hash are inserted instead
    of the video_id.
    """
    bits = token.split_contents()
    print "token", token
    print "bits", bits
    node_instance = url(parser, token)
    return node_cls(view_name=node_instance.view_name,
        args=node_instance.args,
        kwargs=node_instance.kwargs,
        asvar=node_instance.asvar)
video_url = register.tag(video_url)

@register.filter
def in_progress(language):
    return (not language.get_tip(public=True) and
        language.get_tip(public=False))

@register.filter
def format_duration(value):

    """
    Based on a Template Tag by Dan Ward 2009 (http://d-w.me)
    Usage: {{ VALUE|format_duration }}
    """

    if value is None:
        return _("Unknown")

    # Place seconds in to integer
    secs = int(value)

    # If seconds are greater than 0
    if secs > 0:

        # Import math library
        import math

        # Place durations of given units in to variables
        daySecs = 86400
        hourSecs = 3600
        minSecs = 60

        # Create string to hold outout
        durationString = ''

        # Calculate number of hours from seconds
        hours = int(math.floor(secs / int(hourSecs)))

        # Subtract hours from seconds
        secs = secs - (hours * int(hourSecs))

        # Calculate number of minutes from seconds (minus number of hours)
        minutes = int(math.floor(secs / int(minSecs)))

        # Subtract minutes from seconds
        secs = secs - (minutes * int(minSecs))

        # Calculate number of seconds (minus hours and minutes)
        seconds = secs

        # Determine if next string is to be shown
        if hours > 0:

            durationString += '%02d' % (hours,) + ':'

        # If number of minutes is greater than 0
        if minutes > 0 or hours > 0:

            durationString += '%02d' % (minutes,) + ':'

        # If number of seconds is greater than 0
        if seconds > 0 or minutes > 0 or hours > 0:

            if minutes == 0 and hours == 0:
                durationString += '0:%02d' % (seconds,)
            else:
                durationString += '%02d' % (seconds,)

        # Return duration string
        return durationString.strip()

    # If seconds are not greater than 0
    else:

        # Provide 'No duration' message
        return 'No duration'


def shortlink_for_video( video):
    """Return a shortlink string for the video.

    The pattern is http://amara.org/v/<pk>
    """
    protocol = getattr(settings, 'DEFAULT_PROTOCOL')
    domain = settings.HOSTNAME
    # don't www me, we'll redirect users and save three
    # chars. Yay for our twitter-brave-new-world
    domain = domain.replace("www.", '')
    encoded_pk = base62.from_decimal(video.pk)
    path = reverse('shortlink', args=[encoded_pk], no_locale=True)

    return u"{0}://{1}{2}".format(unicode(protocol),
                                  unicode(domain), 
                                  unicode(path))

@register.filter
def multi_video_create_subtitles_data_attrs(video):
    attrs = [
        ('data-video-id', video.id),
        ('data-video-langs', ':'.join(l.language_code for l in
                                      video.all_subtitle_languages())),
    ]
    if video.primary_audio_language_code:
        attrs.append(('data-video-primary-audio-lang-code',
                      video.primary_audio_language_code))
    return mark_safe(' '.join('%s="%s"' % (key, value)
                              for (key, value) in attrs))

@register.simple_tag(name='language-list')
@cached_by_video('language-list')
def language_list(video):
    video.prefetch_languages(with_public_tips=True,
                             with_private_tips=True)
    return mark_safe(render_to_string('videos/_language-list.html', {
        'video': video,
        'language_list': LanguageList(video),
        'STATIC_URL': utils.static_url(),
    }))

@register.simple_tag(name='embedder-code')
@cached_by_video('embedder-code')
def embedder_code(video):
    video.prefetch_languages(with_public_tips=True,
                             with_private_tips=True)
    return mark_safe(render_to_string('videos/_embed_link.html', {
        'video_url': video.get_video_url(),
        'team': video.get_team(),
        'height': video_size["large"]["height"],
        'width': video_size["large"]["width"],
    }))

@register.simple_tag(name='video-metadata', takes_context=True)
def video_metadata(context, video):
    request = context['request']
    metadata = video.get_metadata_for_locale(request.LANGUAGE_CODE)
    return format_html_join(u'\n', u'<h4>{0}: {1}</h4>', [
        (field['label'], field['content'])
        for field in metadata.convert_for_display()
    ])

@register.simple_tag(name='sharing-widget-for-video')
@cached_by_video('sharing-widget')
def sharing_widget_for_video(video):
    context = share_utils.share_panel_context_for_video(video)
    content = mark_safe(render_to_string('_sharing_widget.html', context))
    return content

@register.filter
def speaker_name(video):
    return video.get_metadata().get('speaker-name')
