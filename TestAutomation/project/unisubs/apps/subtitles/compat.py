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

"""Backwards-compatibility functionality for the subtitles data model refector.

These functions are isolated into this file to make them easier to track down
and remove in the future, once we do away with the frontend features that
require them.

"""

def subtitlelanguage_is_translation(sl):
    """Return whether this SubtitleLanguage is a "translation" of another.

    The concept of a one-to-one translation no longer exists in the data model,
    but we can fake it easily enough by looking at the lineage of the tip
    revision.

    """
    tip = sl.get_tip()

    if not tip:
        return False

    lc = sl.language_code
    ancestor_languages = set(tip.lineage.keys()) - set([lc])

    return True if ancestor_languages else False

def subtitlelanguage_original_language_code(sl):
    """Return the "original_language_code" for this SubtitleLanguage.

    In a nutshell, it will tell you what this SL is a "translation" of, even
    though that concept no longer exists in the data model.

    It's not perfect.  In particular, a translation of a translation may return
    the first language instead of the second.  For example, consider the
    following:

        en -> fr -> de

    French is a translation of English, and German is a translation of French.
    If you call this function on the German SL, it may return either English or
    French.  It may not even be consistent across calls.

    We can fix this if necessary, but it will be a lot more database intensive
    to do so.

    TODO: Determine if this edge case is worth fixing.

    """
    tip = sl.get_tip()

    if not tip:
        return None

    lc = sl.language_code
    ancestor_languages = set(tip.lineage.keys()) - set([lc])

    return list(ancestor_languages)[0] if ancestor_languages else None
