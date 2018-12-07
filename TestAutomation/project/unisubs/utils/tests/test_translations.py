# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
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

from collections import defaultdict

from utils import translation

def test_babel_language_lookup_unique():
    language_map = defaultdict(list)
    for code, label in translation.ALL_LANGUAGE_CHOICES:
        language = translation.lookup_babel_locale(code)
        if language is None:
            continue
        key = str(language)
        language_map[key].append(code)
    duplicate_languages = [
        (key, languages)
        for key, languages in language_map.items()
        if len(languages) > 1
    ]
    if duplicate_languages:
        raise AssertionError("Duplicate language lookups: {}".format(
            duplicate_languages))
