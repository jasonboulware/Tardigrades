# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
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
"""
Languages
---------

Languages Resource
******************

API endpoint that lists all available languages on the Amara platform.

.. http:get:: /api/languages/

    :>json languages: maps language codes to language names
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response

from utils import translation

@api_view(['GET'])
def languages(request):
    return Response({
        'languages': dict(translation.SUPPORTED_LANGUAGE_CHOICES)
    })
