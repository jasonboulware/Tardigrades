# Amara, universalsubtitles.org
#
# Copyright (C) 2016 Participatory Culture Foundation
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
Index
-----

Index Resource
**************

.. http:get:: /api/

    This links to the main top-level API endpoints.
"""

from collections import OrderedDict

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse

INDEX_ENDPOINTS = [
    ('videos', 'api:video-list'),
    ('users', 'api:users-list'),
    ('teams', 'api:teams-list'),
    ('languages', 'api:languages'),
    ('messages', 'api:messages'),
]


@api_view(['GET'])
def index(request):
    """
    Welcome to the Amara API.

    Follow a link to start exploring.
    """
    return Response(OrderedDict(
        (name, reverse(view_name, request=request))
        for name, view_name in INDEX_ENDPOINTS
    ))

@api_view(['GET', 'HEAD', 'POST', 'DELETE', 'PUT'])
@permission_classes([AllowAny])
def not_found(request):
    """
    Resource not found
    """
    return Response({
        'path': request.path,
    }, status=status.HTTP_404_NOT_FOUND)
