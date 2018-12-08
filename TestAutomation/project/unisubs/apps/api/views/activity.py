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
Activity
--------

Video Activity Resource
***********************

.. http:get:: /api/videos/(video-id)/activity/

    :queryparam string type: Filter by activity type (:ref:`activity_types`)
    :queryparam user-identifier user: Filter by user who performed the action
        (see :ref:`user_ids`)
    :queryparam bcp-47 language: Filter by the subtitle language
    :queryparam iso-8601 before: Only include activity before this date/time
    :queryparam iso-8601 after: Only include activity after

    :>json string type: Activity type (:ref:`activity_types`)
    :>json iso-8601 date: Date/time of the activity
    :>json user-data user: User who performed the activity (see
        :ref:`user_fields`)
    :>json video-id video: Video related to the activity (or null)
    :>json bcp-47 language: Language of the subtitles related to the activity
        (or null)
    :>json uri video_uri: Link to the video resource endpoint
    :>json uri language_uri: Link to the subtitle language resource endpoint

    Depending on the activity type, extra fields may be present in the
    response data (:ref:`activity_types`).

Team Activity Resource
**********************

.. http:get:: /api/teams/(slug)/activity/

    :queryparam string type: Filter by activity type (:ref:`activity_types`)
    :queryparam user-identifier user: Filter by user who performed the action
        (see :ref:`user_ids`)
    :queryparam video-id video: Filter by video
    :queryparam bcp-47 video_language: Filter by video language
    :queryparam bcp-47 language: Filter by the subtitle language
    :queryparam iso-8601 before: Only include activity before this date/time
    :queryparam iso-8601 after: Only include activity after

    Response data is the same as the video activity resource.

User Activity Resource
**********************

.. http:get:: /api/users/(username)/activity/

    :queryparam string type: Filter by activity type (:ref:`activity_types`)
    :queryparam video-id video: Filter by video
    :queryparam bcp-47 video_language: Filter by video language
    :queryparam bcp-47 language: Filter by the subtitle language
    :queryparam slug team: Filter by team
    :queryparam iso-8601 before: Only include activity before this date/time
    :queryparam iso-8601 after: Only include activity after

    Response data is the same as the video activity resource.

.. _activity_types:

Activity Types
**************

An activity type classifies the activity.  Some types have extra data that is
associated with them

+----------------------+----------------------------+------------------------+
| Type                 | Created When              | Notes/Extra Fields      |
+======================+===========================+=========================+
| video-added          | Video added to amara      |                         |
+----------------------+---------------------------+-------------------------+
| comment-added        | Comment posted            | ``language`` will be    |
|                      |                           | null for video comments |
|                      |                           | and set for subtitle    |
|                      |                           | comments                |
+----------------------+---------------------------+-------------------------+
| version-added        | Subtitle version added    |                         |
+----------------------+---------------------------+-------------------------+
| video-title-changed  | Video title changed       |                         |
+----------------------+---------------------------+-------------------------+
| video-url-added      | URL added to video        | ``url`` will contain    |
|                      |                           | the new URL             |
+----------------------+---------------------------+-------------------------+
| video-url-edited     | Primary video URL change  | ``old_url``/``new_url`` |
|                      |                           | will contain the        |
|                      |                           | old/new primary URL     |
+----------------------+---------------------------+-------------------------+
| video-url-deleted    | URL removed from video    | ``url`` will contain    |
|                      |                           | the deleted URL         |
+----------------------+---------------------------+-------------------------+
| video-deleted        | Video deleted from amara  | ``title`` will contain  |
|                      |                           | the deleted video's     |
|                      |                           | title                   |
+----------------------+---------------------------+-------------------------+
| **Team Related Activity**                                                  |
+----------------------+---------------------------+-------------------------+
| member-joined        | User joined team          |                         |
+----------------------+---------------------------+-------------------------+
| member-left          | User left team            |                         |
+----------------------+---------------------------+-------------------------+
| **Task Related Activity**                                                  |
+----------------------+---------------------------+-------------------------+
| version-approved     | Subtitles approved        |                         |
+----------------------+---------------------------+-------------------------+
| version-rejected     | Subtitles sent back by    |                         |
|                      | approver                  |                         |
+----------------------+---------------------------+-------------------------+
| version-accepted     | Subtitles approved by     |                         |
|                      | reviewer                  |                         |
+----------------------+---------------------------+-------------------------+
| version-declined     | Subtitles sent back by    |                         |
|                      | reviewer                  |                         |
+----------------------+---------------------------+-------------------------+


Legacy Activity Resource
************************

Deprecated API endpoint that lists contains all amara activity.  You should
use the team/video/user query param to find the activity you want.  New code
should use the Video, Team, or User, resources (see above).

List activity
^^^^^^^^^^^^^

.. http:get:: /api/activity/

    :queryparam slug team: Show only items related to a given team
    :queryparam boolean team-activity: If team is given, we normally return
        activity on the team's videos.  If you want to see activity for the
        team itself (members joining/leaving and team video deletions, then
        add team-activity=1)
    :queryparam video-id video: Show only items related to a given video
    :queryparam integer type: Show only items with a given activity type.
        Possible values:

        1.  Add video
        2.  Change title
        3.  Comment
        4.  Add version
        5.  Add video URL
        6.  Add translation
        7.  Subtitle request
        8.  Approve version
        9.  Member joined
        10. Reject version
        11. Member left
        12. Review version
        13. Accept version
        14. Decline version
        15. Delete video

    :queryparam bcp-47 language: Show only items with a given language code
    :queryparam timestamp before: Only include items before this time
    :queryparam timestamp after: Only include items after this time

.. note::
    If both team and video are given as GET params, then team will be used and
    video will be ignored.

Get details on one activity item
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/activity/[activity-id]/

    :>json integer type: activity type.  The values are listed above
    :>json datetime date: date/time of the activity
    :>json video-id video: ID of the video
    :>json uri video_uri: Video Resource
    :>json bcp-47 language: language for the activity
    :>json uri language_url: Subtile Language Resource
    :>json uri resource_uri: Activity Resource
    :>json username user: username of the user user associated with the
        activity, or null
    :>json string comment: comment body for comment activity, null for other
        types
    :>json string new_video_title: new title for the title-change activity, null
        for other types
    :>json integer id: object id **(deprecated use resource_uri if you need to
        get details on a particular activity)**
"""

from __future__ import absolute_import

from datetime import datetime

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters
from rest_framework import generics
from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.reverse import reverse
import dateutil.parser

from activity.models import ActivityRecord
from api import userlookup
from api.fields import TimezoneAwareDateTimeField, UserField
from api.views.apiswitcher import APISwitcherMixin
from subtitles.models import SubtitleLanguage
from auth.models import CustomUser as User
from teams.models import Team
from videos.models import Video
import auth.permissions
import teams.permissions
import videos.permissions

class ActivitySerializer(serializers.ModelSerializer):
    type = serializers.SlugField()
    user = UserField(read_only=True)
    date = TimezoneAwareDateTimeField(source='created')
    video = serializers.CharField(source='video.video_id')
    language = serializers.SerializerMethodField()
    video_uri = serializers.HyperlinkedRelatedField(
        source='video',
        view_name='api:video-detail',
        lookup_field='video_id',
        read_only=True)
    language_uri = serializers.SerializerMethodField()

    def get_language(self, record):
        return record.language_code or None

    def get_language_uri(self, record):
        if not (record.language_code and record.video):
            return None
        return reverse('api:subtitle-language-detail', kwargs={
            'video_id': record.video.video_id,
            'language_code': record.language_code,
        }, request=self.context['request'])

    def to_representation(self, record):
        data = super(ActivitySerializer, self).to_representation(record)
        extra_data_method_name = 'get_{}_extra'.format(
            record.type.replace('-', '_'))
        extra_field_method = getattr(self, extra_data_method_name, None)
        if extra_field_method:
            data.update(extra_field_method(record))
        return data

    def get_video_url_added_extra(self, record):
        url_edit = record.get_related_obj()
        return {
            'url': url_edit.new_url,
        }

    def get_video_url_edited_extra(self, record):
        url_edit = record.get_related_obj()
        return {
            'old_url': url_edit.old_url,
            'new_url': url_edit.new_url,
        }

    def get_video_url_deleted_extra(self, record):
        url_edit = record.get_related_obj()
        return {
            'url': url_edit.old_url,
        }

    def get_video_deleted_extra(self, record):
        video_deletion = record.get_related_obj()
        return {
            'title': video_deletion.title,
        }

    class Meta:
        model = ActivityRecord
        fields = (
            'type', 'date', 'user', 'video', 'language', 'video_uri',
            'language_uri',
        )

class ActivityFilterBackend(filters.BaseFilterBackend):
    # map filter query params to the model field to filter on
    filter_map = {
        'type': 'type',
        'user': 'user',
        'team': 'team__slug',
        'language': 'language_code',
        'video': 'video__video_id',
        'video_language': 'video_language_code',
        'before': 'created__lt',
        'after': 'created__gte',
    }

    def filter_queryset(self, request, queryset, view):
        for name in request.GET:
            if name in self.filter_map and name in view.enabled_filters:
                try:
                    value = self.parse_value(name, request.GET[name])
                    queryset = queryset.filter(**{
                        self.filter_map[name]: value
                    })
                except (ValueError, KeyError):
                    # This happens if you specify an invalid type, date, etc.
                    raise Http404()
        return queryset

    def parse_value(self, name, value):
        if name in ('before', 'after'):
            try:
                return timezone.make_naive(dateutil.parser.parse(value),
                                           timezone.get_default_timezone())
            except ValueError:
                # Case where there is no time zone
                return dateutil.parser.parse(value)
        elif name == 'user':
            return userlookup.lookup_user(value)
        else:
            return value

class VideoActivityView(generics.ListAPIView):
    serializer_class = ActivitySerializer
    filter_backends = (ActivityFilterBackend,)
    enabled_filters = ['type', 'user', 'language', 'before', 'after']

    def get_queryset(self):
        video = get_object_or_404(Video, video_id=self.kwargs['video_id'])
        if not videos.permissions.can_view_activity(video, self.request.user):
            # Raise 404 so we don't give away the fact the video exists
            raise Http404()
        return ActivityRecord.objects.for_video(video)

class TeamActivityView(generics.ListAPIView):
    serializer_class = ActivitySerializer
    filter_backends = (ActivityFilterBackend,)
    enabled_filters = ['video', 'video_language', 'type', 'user',
                       'language', 'before', 'after']

    def get_queryset(self):
        team = get_object_or_404(Team, slug=self.kwargs['slug'])
        if not teams.permissions.can_view_activity(team, self.request.user):
            if team.team_private():
                # raise a 404 here to not give away if the slug exists or not
                raise Http404()
            else:
                raise PermissionDenied()
        return ActivityRecord.objects.for_team(team)

class UserActivityView(generics.ListAPIView):
    serializer_class = ActivitySerializer
    filter_backends = (ActivityFilterBackend,)
    enabled_filters = ['video', 'team', 'video_language', 'type', 
                       'language', 'before', 'after']

    def get_queryset(self):
        try:
            user = userlookup.lookup_user(self.kwargs['identifier'])
        except User.DoesNotExist:
            raise Http404()
        if not auth.permissions.can_view_activity(user, self.request.user):
            raise Http404()
        if not user.is_active:
            raise Http404()
        return ActivityRecord.objects.for_user(user)

class LegacyActivitySerializer(serializers.ModelSerializer):
    type = serializers.IntegerField(source='type_code')
    type_name = serializers.SlugField(source='type')
    user = serializers.CharField(source='user.username')
    comment = serializers.SerializerMethodField()
    new_video_title = serializers.SerializerMethodField()
    created = TimezoneAwareDateTimeField(read_only=True)
    video = serializers.CharField(source='video.video_id')
    video_uri = serializers.HyperlinkedRelatedField(
        source='video',
        view_name='api:video-detail',
        lookup_field='video_id',
        read_only=True)
    language = serializers.SerializerMethodField()
    language_url = serializers.SerializerMethodField()
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name='api:activity-detail',
        lookup_field='id',
    )

    def get_language(self, record):
        return record.language_code or None

    def get_comment(self, record):
        if record.type == 'comment-added':
            return record.get_related_obj().content
        else:
            return None

    def get_new_video_title(self, record):
        if record.type == 'video-title-changed':
            return record.get_related_obj().new_title
        else:
            return None

    def get_language_url(self, record):
        if not (record.language_code and record.video):
            return None
        return reverse('api:subtitle-language-detail', kwargs={
            'video_id': record.video.video_id,
            'language_code': record.language_code,
        }, request=self.context['request'])

    class Meta:
        model = ActivityRecord
        fields = (
            'id', 'type', 'type_name', 'created', 'video', 'video_uri',
            'language', 'language_url', 'user', 'comment', 'new_video_title',
            'resource_uri'
        )

class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = 'id'
    serializer_class = LegacyActivitySerializer
    paginate_by = 20

    def get_queryset(self):
        params = self.request.query_params
        if 'team' in params:
            try:
                team = Team.objects.get(slug=params['team'])
            except Team.DoesNotExist:
                return ActivityRecord.objects.none()
            if not team.user_is_member(self.request.user):
                raise PermissionDenied()
            qs = ActivityRecord.objects.for_team(team)
            if 'team-activity' in params:
                qs = qs.team_activity()
            else:
                qs = qs.team_video_activity()
        elif 'video' in params:
            try:
                video = Video.objects.get(video_id=params['video'])
            except Video.DoesNotExist:
                return ActivityRecord.objects.none()
            team_video = video.get_team_video()
            if (team_video and not
                team_video.team.user_is_member(self.request.user)):
                raise PermissionDenied()
            qs = video.activity.original()
        else:
            qs = ActivityRecord.objects.for_api_user(self.request.user)
        return qs.select_related('video', 'user', 'team')

    def filter_queryset(self, queryset):
        params = self.request.query_params
        if 'type' in params:
            try:
                type_filter = int(params['type'])
            except ValueError:
                queryset = ActivityRecord.objects.none()
            else:
                queryset = queryset.filter(type=type_filter)
        if 'language' in params:
            queryset = queryset.filter(language_code=params['language'])
        if 'before' in params:
            queryset = queryset.filter(
                created__lt=datetime.fromtimestamp(int(params['before'])))
        if 'after' in params:
            queryset = queryset.filter(
                created__gte=datetime.fromtimestamp(int(params['after'])))
        return queryset
