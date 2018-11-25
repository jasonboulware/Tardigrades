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
Messages
--------

Message Resource
****************

.. http:post:: /api/message/

    Send a message to a user/team

    :<json user-identifier user: Recipient (see :ref:`user_ids`)
    :<json slug team: Recipient team's slug
    :<json string subject: Subject of the message
    :<json string content: Content of the message

.. note:: You can only send either ``user`` or ``team``, not both.
"""

from __future__ import absolute_import

from django.core.exceptions import PermissionDenied
from rest_framework import serializers
from rest_framework import status
from rest_framework import views
from rest_framework.response import Response

from api.fields import UserField
from auth.models import CustomUser as User
from teams.models import Team
from messages.models import Message
import teams.permissions

class MessagesSerializer(serializers.Serializer):
    user = UserField(required=False)
    team = serializers.CharField(required=False)
    subject = serializers.CharField()
    content = serializers.CharField()

    default_error_messages = {
        'unknown-team': "Unknown team: {team}",
        'no-user-or-team': "Must specify either user or team",
    }

    def validate_team(self, slug):
        try:
            team = Team.objects.get(slug=slug)
        except Team.DoesNotExist:
            self.fail('unknown-team', team=slug)
        if not teams.permissions.can_message_all_members(
            team, self.context['user']):
            raise PermissionDenied()
        return team

    def validate(self, data):
        if not ('team' in data or 'user' in data):
            self.fail('no-user-or-team')
        return data

    def recipients(self):
        if 'user' in self.validated_data:
            yield self.validated_data['user']
        else:
            qs = self.validated_data['team'].members.select_related('user')
            for member in qs:
                yield member.user

    def create_messages(self):
        messages = [
            Message(user=user,
                    content=self.validated_data['content'],
                    subject=self.validated_data['subject'],
                    message_type='M',
                    author=self.context['user'])
            for user in self.recipients()
            if user != self.context['user']
        ]
        Message.objects.bulk_create(messages)
        if len(messages) == 1:
            self.context['user'].sent_message()

class Messages(views.APIView):
    def get_serializer(self):
        return MessagesSerializer()

    def post(self, request, **kwargs):
        if not request.user.can_send_messages:
            raise PermissionDenied()
        serializer = MessagesSerializer(
            data=request.data,
            context={'user': request.user},
        )
        if serializer.is_valid():
            serializer.create_messages()
            data = {} # should we return some data?
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
