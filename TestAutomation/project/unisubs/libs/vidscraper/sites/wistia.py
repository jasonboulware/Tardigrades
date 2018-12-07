# Miro - an RSS based video player application
# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of vidscraper.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import datetime
import json
import re
import urllib

from lxml import builder
from lxml import etree
from lxml.html import builder as E
from lxml.html import tostring
import oauth2

from vidscraper.decorators import provide_shortmem, parse_url, returns_unicode
from vidscraper import util
from vidscraper.errors import Error
from django.conf import settings

class WistiaError(Error):
    pass

WISTIA_OEMBED_API_URL = 'http://fast.wistia.com/oembed?embedType=seo&url='
#'http://fast.wistia.com/oembed?url=http://home.wistia.com/medias/'

EMaker = builder.ElementMaker()
EMBED = EMaker.embed

EMBED_WIDTH = 425
EMBED_HEIGHT = 344

def get_shortmem(url):
    shortmem = {}
    video_id = WISTIA_REGEX.match(url).groupdict()['video_id']
    apiurl = '%s?%s' % (WISTIA_OEMBED_API_URL, urllib.quote(url))
    finalexcept = None
    
    backoff = util.random_exponential_backoff(2)

    for i in range(3):
        try:
            reponse = urllib.urlopen(apiurl)
            
            api_raw_data = response.read()
            api_data = json.loads(api_raw_data)
        except Exception as e:
            finalexcept = e
            continue
        else:
            shortmem['oembed'] = api_data
            break
                    
        backoff.next()
        
    
    if 'oembed' in shortmem:
        return shortmem

    errmsg = u'Wistia API error : '
    if finalexcept is not None:
        """if isinstance(finalexcept, urllib.HTTPError):
            errmsg += finalexcept.code + " - " + HTTPResponseMessages[ finalexcept.code ][0]
        elif isinstance(finalexcept, urllib.URLError):
            errmsg += "Could not connect - " + finalexcept.reason
        else:"""
        errmsg += str(finalexcept)
    else:
        errmsg += u' Unrecognized error. Sorry about that, chief.'
    
    return None

def parse_api(scraper_func, shortmem=None):
    def new_scraper_func(url, shortmem={}, *args, **kwargs):
        if not shortmem:
            shortmem = get_shortmem(url)
        return scraper_func(url, shortmem=shortmem, *args, **kwargs)
    return new_scraper_func

@parse_api
@returns_unicode
def scrape_title(url, shortmem={}):
    try:
        return shortmem['oembed']['title'] or u''
    except KeyError:
        return u''

@parse_api
@returns_unicode
def scrape_description(url, shortmem={}):
    try:
        description = shortmem['oembed']['title'] # No desc provided in oembed. Use title.
    except KeyError:
        description = ''
    return util.clean_description_html(description)

@returns_unicode
def get_embed(url, shortmem={}, width=EMBED_WIDTH, height=EMBED_HEIGHT):
    return shortmem['oembed']['html']

@parse_api
@returns_unicode
def get_thumbnail_url(url, shortmem={}):
    return shortmem['oembed']['thumbnail_url']

@parse_api
@returns_unicode
def get_user(url, shortmem={}):
    return shortmem['oembed']['provider_name']

@parse_api
@returns_unicode
def get_user_url(url, shortmem={}):
    return shortmem['oembed']['provider_url']

@parse_api
@returns_unicode
def get_duration(url, shortmem={}):
    return shortmem['oembed']['duration']

WISTIA_REGEX = re.compile(r'https?://(.+)?(wistia\.com|wi\.st|wistia\.net)/(medias|embed/iframe)/(?P<video_id>\w+)')

SUITE = {
    'regex': WISTIA_REGEX,
    'funcs': {
        'title': scrape_title,
        'description': scrape_description,
        'embed': get_embed,
        'thumbnail_url': get_thumbnail_url,
        'user': get_user,
        'user_url': get_user_url,
        'duration': get_duration
    },
    'order': ['title', 'description', 'file_url', 'embed']}
