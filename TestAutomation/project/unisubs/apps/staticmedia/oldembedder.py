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

"""staticmedia.oldembedder -- Code to handle the old embedder widget"""

from django.conf import settings
from django.template.loader import render_to_string

from staticmedia import bundles
from staticmedia import utils

def js_code():
    """Build the JS for the old embed.js file """
    bundle = bundles.get_bundle('unisubs-offsite-compiled.js')
    context = {
        'BASE_URL': "%s://%s"  % (settings.DEFAULT_PROTOCOL,
                                  settings.HOSTNAME),
        'STATIC_URL': utils.static_url(),
        "js_file": bundle.get_url(),
    }
    return render_to_string('widget/embed.js', context)
