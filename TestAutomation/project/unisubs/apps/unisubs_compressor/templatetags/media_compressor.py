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

import logging
import string

from django import template
from django.template.loader import render_to_string
from django.conf import settings
from urlparse import urlparse

logger = logging.getLogger(__name__)
register = template.Library()
should_compress = None

def should_include_js_base_dependencies(bundle_type, bundle):
    return (bundle_type == "js" and
            bundle.get('use_closure') and
            bundle.get('include_js_base_dependencies', True))

def _bundle_output(bundle_name, bundle):
    if 'output' in bundle:
        return bundle['output']
    elif bundle_name == 'embedder':
        # have to special case this for some reason
        return "release/public/embedder.js"
    else:
        raise ValueError("Don't know how to get bundle output for %s" %
                         bundle_name)

def calc_should_compress_from_settings():
    default = not getattr(settings, "DEBUG", False)
    return getattr(settings, "COMPRESS_MEDIA", default)

def calc_static_url():
    if calc_should_compress_from_settings():
        return settings.STATIC_URL
    else:
        return settings.STATIC_URL_BASE

def _urls_for(bundle_name, should_compress):
    # if we want to turn off compilation at runtime (eg/ on javascript unit tests)
    # then we need to know the media url prior the the unique mungling
    media_url = settings.STATIC_URL
    if should_compress is None :
        should_compress = calc_should_compress_from_settings()
    else:
        should_compress = bool(should_compress)
        if bool(should_compress) is False:
            media_url = settings.STATIC_URL_BASE
    bundle = settings.MEDIA_BUNDLES.get(bundle_name)
    bundle_type = bundle["type"]

    urls = []
    
    if should_compress == True and bundle.get('release_url', False):
        media_url = settings.STATIC_URL_BASE
        urls += [_bundle_output(bundle_name, bundle)]
    elif  should_compress == True:
        base = ""
        suffix = ""
        if bundle_type == "css":
            base =  "css-compressed/"
        elif bundle_type == "js":
            base = "js/"
            if 'bootloader' in bundle and not bundle['bootloader']['render_bootloader']:
                suffix = "-inner"
        urls += ["%s%s%s.%s" % ( base, bundle_name, suffix, bundle_type)]
    else:
        if should_include_js_base_dependencies(bundle_type, bundle):
            urls = list(settings.JS_BASE_DEPENDENCIES)
        urls += settings.MEDIA_BUNDLES.get(bundle_name)["files"]
        
        if should_compress:
            logger.warning("could not find final url for %s" % bundle_name)
    return urls, media_url, bundle_type

def render_links(files, media_url, bundle_type):
    if bundle_type == 'css':
        link_template = string.Template('<link rel="stylesheet" '
                                        'type="text/css" '
                                        'href="${media_url}${file}">')
    elif bundle_type == 'js':
        link_template = string.Template('<script type="text/javascript" '
                                        'src="${media_url}${file}"></script>')
    else:
        raise ValueError("Unknown bundle type: %s" % bundle_type)

    output = []
    for file in files:
        special_handler = _special_files_handlers.get(file)
        if special_handler is None:
            output.append(link_template.substitute(media_url=media_url,
                                                   file=file))
        else:
            output.append(special_handler())
    return "\n".join(output)
    
@register.simple_tag
def include_bundle(bundle_name, should_compress=None):
    return render_links(*_urls_for(bundle_name, should_compress))

@register.simple_tag
def include_bootstrapped_bundle(bundle_name):
    should_compress = calc_should_compress_from_settings()
    if should_compress:
        return include_bootstrapped_bundle_compressed(bundle_name)
    else:
        return include_bootstrapped_bundle_uncompressed(bundle_name)

def include_bootstrapped_bundle_uncompressed(bundle_name):
    media_url = settings.STATIC_URL
    bundle_settings = settings.MEDIA_BUNDLES[bundle_name]
    bootloader_settings = bundle_settings['bootloader']
    files = list(bundle_settings['files'])
    bootstrapped_file = bootloader_settings['file']
    files.remove(bootstrapped_file)

    bootloader = render_to_string("uni_compressor/bootloader.html", {
        'url': media_url + bootstrapped_file,
    })

    links = render_links(files, media_url, 'js')

    return "\n".join([links, bootloader])

def include_bootstrapped_bundle_compressed(bundle_name):
    return render_to_string("uni_compressor/bootloader.html", {
        'url': full_url_for(bundle_name),
    })

@register.simple_tag
def url_for(bundle_name, should_compress=True):
    return _urls_for(bundle_name, should_compress)[0][0]

@register.simple_tag
def full_url_for(bundle_name, should_compress=True):
    urls, media_url, bundle_type = _urls_for(bundle_name, should_compress)
    return media_url + urls[0]
