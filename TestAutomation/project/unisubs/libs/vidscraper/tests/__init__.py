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

import hashlib
import os

import mock
from feedparser import parse as org_parse

testdata_dir = os.path.join(os.path.dirname(__file__), 'testdata')

def open_file_for_url(url):
    filename = hashlib.md5(url).hexdigest()
    path = os.path.join(testdata_dir, filename)
    if not os.path.exists(path):
        raise ValueError("No file in testdata for %r" % url)
    return open(path)

def mock_url_open(url):
    # return an actual file object instead of the file-like object that
    # urllib.urlopen usually returns
    return open_file_for_url(url)

def mock_feedparser_parse(arg):
    if isinstance(arg, basestring) and arg.startswith("http:"):
        # assume this means arg is a URL.  Use the already downloaded contents
        # for the feed
        return org_parse(open_file_for_url(arg).read())
    else:
        return org_parse(arg)

patches = [
    mock.patch('urllib.urlopen', mock.Mock(side_effect=mock_url_open)),
    mock.patch('vidscraper.util.open_url_while_lying_about_agent',
               mock.Mock(side_effect=mock_url_open)),
    mock.patch('feedparser.parse',
               mock.Mock(side_effect=mock_feedparser_parse)),
]

def setup():
    for patch in patches:
        patch.start()

def teardown():
    for patch in patches:
        patch.stop()
