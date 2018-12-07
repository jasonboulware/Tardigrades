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

from __future__ import absolute_import

from django import template
from django.conf import settings
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import to_locale
from utils.translation import get_language_label

from staticmedia import bundles
from staticmedia import utils

register = template.Library()

@register.simple_tag(takes_context=True)
def media_bundle(context, bundle_name):
    if context.get('experimental') and bundle_name in ('editor.js',
                                                       'editor.css'):
        return experimental_editor_tag(bundle_name)
    bundle = bundles.get_bundle(bundle_name)
    return mark_safe(bundle.get_html())

def experimental_editor_tag(bundle_name):
    # somewhat hacky code to handle the experimental editor
    if bundle_name == 'editor.js':
        url = "https://s3.amazonaws.com/{}/experimental/js/editor.js".format(
            settings.STATIC_MEDIA_EXPERIMENTAL_EDITOR_BUCKET)
        return format_html('<script src="{}"></script>', url)
    elif bundle_name == 'editor.css':
        url = "https://s3.amazonaws.com/{}/experimental/css/editor.css".format(
            settings.STATIC_MEDIA_EXPERIMENTAL_EDITOR_BUCKET)
        return format_html(
            '<link href="{}" rel="stylesheet" type="text/css" />', url)
    else:
        raise ValueError("Unkown bundle name: {}").format(bundle_name)


@register.simple_tag
def url_for(bundle_name):
    return bundles.get_bundle(bundle_name).get_url()

@register.simple_tag
def static_url():
    return utils.static_url()

@register.simple_tag(takes_context=True)
def js_i18n_catalog(context):
    locale = to_locale(context['LANGUAGE_CODE'])
    if settings.STATIC_MEDIA_USES_S3:
        src = utils.static_url() + 'jsi18catalog/{}.js'.format(locale)
    else:
        src = reverse('staticmedia:js_i18n_catalog', args=(locale,))
    return format_html('<script type="text/javascript" src="{}"></script>', src)

@register.simple_tag(takes_context=True)
def js_language_data(context):
    locale = to_locale(context['LANGUAGE_CODE'])
    if settings.STATIC_MEDIA_USES_S3:
        src = utils.static_url() + 'jslanguagedata/{}.js'.format(locale)
    else:
        src = reverse('staticmedia:js_language_data', args=(locale,))
    return format_html('<script type="text/javascript" src="{}"></script>', src)

@register.simple_tag(takes_context=True)
def current_language_name(context):
    return get_language_label(context['LANGUAGE_CODE'])
