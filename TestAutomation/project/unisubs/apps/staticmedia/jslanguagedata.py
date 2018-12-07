# Amara, universalsubtitles.org
#
# Copyright (C) 2016 Participatory Culture Foundation
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

"""Render javascript language data

This module allows you to render javascript code to handle language data for
the current locale.  It provides some of the functionality of the
utils.translation module to our javascript code.  In particular:

  - Listing all languages
  - Listing popular languages
  - Getting a display name of a language choice in a selectbox

The main reason this exists is the lists are fairly long, so we need to be
careful about them exploding the size of the pages.  In particular, it would
take ~10K of code to display a selectbox that lists all languages and
sometimes we want to display many on a page.

To combat this, we place the code in static files on S3 -- one for each locale.
This eliminates the issue of having to duplicate the options and also allows
the script to be stored in the browser cache.
"""
from __future__ import absolute_import
import json

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import ugettext

from utils import translation

def render_js_language_script():
    return render_to_string('languageData.js', {
        'languages': sorted(
            ((code, translation.choice_label (code)) 
                for code, en_label in translation.SUPPORTED_LANGUAGE_CHOICES), 
                key=lambda x: x[0]
            ),
        'popular_languages': translation.POPULAR_LANGUAGES,
        'locale_choices': [code for (code, label) in settings.LANGUAGES],
        'allLanguagesLabel': json.dumps(ugettext('All Languages')),
        'popularLanguagesLabel': json.dumps(ugettext('Popular Languages')),
    }).encode('utf-8')
