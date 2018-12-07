# -*- coding: utf-8 -*-
# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program.  If not, see http://www.gnu.org/licenses/agpl-3.0.html.

import string

from django import template
from django.urls import reverse
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from babelsubs.generators import HTMLGenerator
from subtitles.forms import SubtitlesUploadForm

register = template.Library()

@register.filter
def visibility_display(subtitle_version):
    '''
    Returns a human readable representation of the interaction between
    visibility and visibility_override for display purposes.
    '''
    visibility = subtitle_version.visibility_override or subtitle_version.visibility
    return force_unicode({
        'public': _("Public"),
        'private': _("Private"),
        'deleted': _("Deleted")
    }[visibility])

@register.filter
def visibility(subtitle_version):
    '''
    Returns a programmatic representation of the interaction between
    visibility and visibility_override.
    '''
    return (subtitle_version.visibility_override or subtitle_version.visibility)

def format_time(milliseconds):
    if milliseconds is None:
        return ''
    t = int(round(milliseconds / 1000.0))
    s = t % 60
    s = s > 9 and s or '0%s' % s
    return '%s:%s' % (t / 60, s)

@register.filter
def render_subtitles(subtitle_version):
    """Render the subtitles for a SubtitleVersion

    This would be much nicer in a django template, but for versions with
    thousands of subtitles that gets slow
    """
    subtitles = subtitle_version.get_subtitles()
    is_rtl = " is-rtl" if subtitle_version.subtitle_language.is_rtl() else ""
    timing_template = string.Template(u"""\
<div class="subtitlesList-time">
    <a class="subtitlesList-seek no-underline" href="#" data-start-time="$start_time" title="{}">
        $start_time_display - $end_time_display
    </a>
</div>""".format(_('Play video here')))
    not_synced_timing = u'<div class="subtitlesList-time">{}</div>'.format(_('Not Synced'))
    text_template = string.Template(u'<div class="subtitlesList-subtitle{}">$text</div>'.format(is_rtl))
    text_template_new_p = string.Template(
        u'<div class="subtitlesList-subtitle topicSentence{}">$text</div>'.format(is_rtl))

    synced_subs = []
    unsynced_subs = []

    for item in subtitles.subtitle_items(HTMLGenerator.MAPPINGS):
        if item.start_time is not None:
            synced_subs.append(item)
        else:
            unsynced_subs.append(item)
    synced_subs.sort(key=lambda item: item.start_time)

    parts = []
    parts.append(u'<ul class="subtitlesList{} text-small">'.format(is_rtl))
    for item in synced_subs + unsynced_subs:
        new_paragraph = item.meta.get('new_paragraph', False)
        parts.append(u'<li>')
        if item.start_time is not None:
            parts.append(timing_template.substitute(
                start_time=item.start_time,
                start_time_display=format_time(item.start_time),
                end_time_display=format_time(item.end_time)))
        else:
            parts.append(not_synced_timing)
        if new_paragraph:
            parts.append(text_template_new_p.substitute(text=item.text))
        else:
            parts.append(text_template.substitute(text=item.text))
        parts.append(u'</li>')
    parts.append(u'</ul>')
    return mark_safe(u"\n".join(parts))

@register.assignment_tag
def subtitle_download_url(version, format_name):
    filename = '.'.join([
        version.video.get_download_filename(),
        version.language_code
    ])
    return reverse('subtitles:download', kwargs={
        'video_id': version.video.video_id,
        'language_code': version.language_code,
        'filename': filename,
        'format': format_name,
        'version_number': version.version_number,
    })

@register.filter
def old_render_subtitles(subtitle_version):
    """Render the subtitles for a SubtitleVersion

    This would be much nicer in a django template, but for versions with
    thousands of subtitles that gets slow
    """
    subtitles = subtitle_version.get_subtitles()
    timing_template = string.Template(u"""\
<div class="timing">
    <a class="time_link" href="#" title="Play video here">
        <span class="data">$start_time</span>
        $start_time_display - $end_time_display
    </a>
</div>""")
    not_synced_timing = u"""\
<div class="timing">
    %s
</div>""" % _('Not Synced')
    text_template = string.Template(u"""\
<div class="translation-text">
    $text
</div>""")
    text_template_new_p = string.Template(u"""\
<div class="translation-text">
    $text
    <p class='quiet'>¶</p>
</div>""")

    synced_subs = []
    unsynced_subs = []

    for item in subtitles.subtitle_items(HTMLGenerator.MAPPINGS):
        if item.start_time is not None:
            synced_subs.append(item)
        else:
            unsynced_subs.append(item)
    synced_subs.sort(key=lambda item: item.start_time)

    parts = []
    for item in synced_subs + unsynced_subs:
        new_paragraph = item.meta.get('new_paragraph', False)
        if new_paragraph:
            parts.append(u'<li class="subtitle-item start-of-paragraph">')
        else:
            parts.append(u'<li class="subtitle-item">')
        if item.start_time is not None:
            parts.append(timing_template.substitute(
                start_time=item.start_time,
                start_time_display=format_time(item.start_time),
                end_time_display=format_time(item.end_time)))
        else:
            parts.append(not_synced_timing)
        if new_paragraph:
            parts.append(text_template_new_p.substitute(text=item.text))
        else:
            parts.append(text_template.substitute(text=item.text))
    return mark_safe(u"\n".join(parts))

