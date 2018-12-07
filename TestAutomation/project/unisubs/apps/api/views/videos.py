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
Videos
------

Videos Resource
***************

List/Search/Lookup videos on Amara

Listing Videos
^^^^^^^^^^^^^^

.. http:get:: /api/videos/

    List videos.  You probably want to specify a query filter parameter to
    limit the results

    List results are paginated.

    :queryparam url video_url: Filter by video URL
    :queryparam slug team: Filter by team.  Passing in `null` will return only
        videos that are in the public area.
    :queryparam slug project: Filter by team project.  Passing in `null` will
        return only videos that don't belong to a project
    :queryparam string order_by: Change the list ordering.  Possible values:

        - `title`: ascending
        - `-title`: descending
        - `created`: older videos first
        - `-created`: newer videos

.. note::
    - If no query parameter is given, the last 10 public videos are listed.
    - If you pass in the project filter, you need to pass in a team

Get info on a specific video
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/videos/(video-id)/

    :>json video-id id: Amara video id
    :>json bcp-47 primary_audio_language_code: Audio language code
    :>json string title: Video title
    :>json string description: Video description
    :>json integer duration: Video duration in seconds (or null if not known)
    :>json url thumbnail: URL to the video thumbnail
    :>json iso-8601 created: Video creation date/time
    :>json slug team: Slug of the Video's team (or null)
    :>json dict metadata: Dict mapping metadata names to values
    :>json list languages: List of languages that have subtitles started.  See
        below for a a description.
    :>json char video_type: Video type identifier
    :>json list all_urls: List of URLs for the video (the first one is the
      primary video URL)
    :>json uri activity_uri: Video Activity Resource
    :>json url urls_uri: Video URL Resource
    :>json uri subtitle_languages_uri: Subtitle languages Resource
    :>json uri resource_uri: Video Resource
    :>json string original_language: contains a copy of
      primary_audio_language_code **(deprecated)**

    **Language data**:

    :>json string code: Language code
    :>json string name: Human readable label for the language
    :>json boolean published: Are the subtitles publicly viewable?
    :>json string dir: Language direction ("ltr" or "rtl")
    :>json url subtitles_uri: Subtitles Resource
    :>json url resource_uri: Subtitles Language Resource

Adding a video
^^^^^^^^^^^^^^

.. http:post:: /api/videos/

    :<json url video_url: The url for the video. Any url that Amara accepts
      will work here. You can send the URL for a file (e.g.
      http:///www.example.com/my-video.ogv), or a link to one of our accepted
      providers (youtube, vimeo, dailymotion)
    :<json string title: title of the video
    :<json string description: About this video
    :<json integer duration: Duration in seconds, in case it can not be
      retrieved automatically by Amara
    :<json string primary_audio_language_code: language code for the main
      language spoken in the video.
    :<json url thumbnail: URL to the video thumbnail
    :<json dict metadata: Dictionary of metadata key/value pairs.  These handle
        extra information about the video.  Right now the type keys supported
        are `speaker-name` and `location`.  Values can be any string.
    :<json string team: team slug for the video or null to remove it from its
      team.
    :<json string project: project slug for the video or null to put it in the
        default project.

.. note::

    - When submitting URLs of external providers (i.e. youtube, vimeo), the
      metadata (title, description, duration) can be fetched from them. If
      you're submitting a link to a file (mp4, flv) then you can make sure
      those attributes are set with these parameters. Note that these
      parameters (except the video duration) override any information from the
      original provider or the file header.
    - For all fields, if you pass an empty string, we will treat it as if the
      field was not present in the input (**deprecated**).
    - For slug and project, You can use the string "null" as a synonym for the
      null object (**deprecated**).

Update an existing video
^^^^^^^^^^^^^^^^^^^^^^^^

.. http:put:: /api/videos/(video-id)/

    This uses the same fields as video creation, excluding `video_url`.

    As with creating video, an update can not override the duration received
    from the provider or specified in the file header.

Delete an existing video
^^^^^^^^^^^^^^^^^^^^^^^^

.. http:delete:: /api/videos/(video-id)/

   This deletes a video.

   If there are any subtitles/collaborations on the video, they will also be deleted.

Moving videos between teams and projects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- To move a video from one team to another, you can make a put request with a
  ``team`` value.
- Similarly, you can move a video to a different project using the
  ``project`` field.  `team` must also be given in this case.
- The user making the change must have permission to remove a video from
  the originating team and permission to add a video to the target team.

Video URL Resource
******************

Each video has at least 1 URL associated with it, but some can have more.
This allows you to associate subtitles with the video on multiple video
providers (e.g. a youtube version, a vimeo version, etc).

One video URL is flagged the `primary URL`.  This is what will gets
used in the embedder and editor.


List URLs for a video
^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/videos/(video-id)/urls/

    List results are paginated.

    :>json string video-id: Amara video ID
    :>json iso-8601 created: creation date/time
    :>json url url: URL string
    :>json boolean primary: is this the primary URL for the video?
    :>json boolean original: was this the URL that was created with the video?
    :>json uri resource_uri: Video URL Resource
    :>json string videoid: ID on the Hosting platform
    :>json string type: Video type (Youtube, Vimeo, HTML5, etc.)
    :>json integer id: Internal ID for the object **(deprecated, use
      resource_uri rather than trying to construct API URLs yourself)**.

Get details on a specific URL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: (video-url-endpoint)

    The response fields are the same as for the list endpoint

    Use the `resource_uri` from the listing to find the video URL endpoint

Add a URL for a video
^^^^^^^^^^^^^^^^^^^^^
.. http:post:: /api/videos/(video-id)/urls/

    :<json url url: Video URL.  This can be any URL that works in the add video
      form for the site (mp4 files, youtube, vimeo, etc).  Note: The URL
      cannot be in use by another video.
    :<json boolean primary: If True, this URL will be made the primary URL
    :<json boolean original: Is this is the first url for the video?

Making a URL the primary URL for a video
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:put:: (video-url-endpoint)

    :<json primary: Pass in true to make a video URL the primary for a video

    Use the `resource_uri` from the listing to find the video URL endpoint

Deleting Video URLs
^^^^^^^^^^^^^^^^^^^

.. http:delete:: (video-url-endpoint)

    Remove a video URL from a video

    Use the `resource_uri` from the listing to find the video URL endpoint

.. note:

    **A video must have a primary URL**.  If this the primary URL for a video,
    the request will fail with a 400 code.
"""

from __future__ import absolute_import
from urlparse import urljoin

from django import http
from django.db.models import Q
from django.db.models.query import QuerySet, EmptyQuerySet
from rest_framework import filters
from rest_framework import generics
from rest_framework import mixins
from rest_framework import serializers
from rest_framework import status
from rest_framework import views
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
import json

from api import extra
from api.fields import LanguageCodeField, TimezoneAwareDateTimeField
from api.views.apiswitcher import APISwitcherMixin
from teams import permissions as team_perms
from teams.models import Team, TeamVideo, Project, VideoVisibility
from subtitles.models import SubtitleLanguage
from videos import metadata
from videos.models import Video, URL_MAX_LENGTH
from videos.types import video_type_registrar, VideoTypeError
import videos.tasks

class VideoLanguageShortSerializer(serializers.Serializer):
    code = serializers.CharField(source='language_code')
    name = serializers.CharField(source='get_language_code_display')
    published = serializers.BooleanField(source='has_public_version')
    dir = serializers.CharField()
    subtitles_uri = serializers.SerializerMethodField()
    resource_uri = serializers.SerializerMethodField()

    def get_resource_uri(self, language):
        kwargs = {
            'video_id': language.video.video_id,
            'language_code': language.language_code,
        }
        return reverse('api:subtitle-language-detail', kwargs=kwargs,
                       request=self.context['request'])

    def get_subtitles_uri(self, language):
        kwargs = {
            'video_id': language.video.video_id,
            'language_code': language.language_code,
        }
        return reverse('api:subtitles', kwargs=kwargs,
                       request=self.context['request'])

class VideoMetadataSerializer(serializers.Serializer):
    default_error_messages = {
        'unknown-key': "Unknown metadata key: {name}",
    }
    def __init__(self, *args, **kwargs):
        super(VideoMetadataSerializer, self).__init__(*args, **kwargs)
        for name in metadata.all_names():
            self.fields[name] = serializers.CharField(required=False)

    def get_attribute(self, video):
        return video.get_metadata()

    def to_internal_value(self, data):
        for key in data:
            if key not in self.fields:
                self.fail('unknown-key', name=key)
        return data

class TeamSerializer(serializers.CharField):
    default_error_messages = {
        'unknown-team': 'Unknown team: {team}',
    }

    def get_attribute(self, video):
        team_video = video.get_team_video()
        return team_video.team.slug if team_video else None

    def to_internal_value(self, slug):
        try:
            return Team.objects.get(slug=slug)
        except Team.DoesNotExist:
            self.fail('unknown-team', team=slug)

class TeamTypeSerializer(serializers.CharField):
    def get_attribute(self, video):
        team_video = video.get_team_video()
        return team_video.team.workflow_type if team_video else None

class ProjectSerializer(serializers.CharField):
    def get_attribute(self, video):
        team_video = video.get_team_video()
        if not team_video:
            return None
        elif team_video.project.is_default_project:
            return None
        else:
            return team_video.project.slug

class VideoListSerializer(serializers.ListSerializer):
    def to_representation(self, qs):
        # Do some optimizations to reduce the number of queries before passing
        # the result to the default to_representation() method

        if isinstance(qs, QuerySet):
            # Note: we have to use prefetch_related the teamvideo attributes,
            # otherwise it will filter out non-team videos.  I think this is a
            # django 1.4 bug.
            qs = (qs.select_related('teamvideo')
                  .prefetch_related('teamvideo__team', 'teamvideo__project',
                                    'newsubtitlelanguage_set', 'videourl_set'))
        # run bulk_has_public_version(), otherwise we have a query for each
        # language of each video
        videos = list(qs)
        all_languages = []
        for v in videos:
            all_languages.extend(v.all_subtitle_languages())
        SubtitleLanguage.bulk_has_public_version(all_languages)
        return super(VideoListSerializer, self).to_representation(videos)

class VideoThumbnailField(serializers.URLField):
    def get_attribute(self, video):
        return video

    def to_representation(self, video):
        # If the result of get_wide_thumbnail() doesn't include a scheme, use
        # https
        return urljoin('https:', video.get_wide_thumbnail())

    def to_internal_value(self, value):
        return value

class VideoSerializer(serializers.Serializer):
    # Note we could try to use ModelSerializer, but we are so far from the
    # default implementation that it makes more sense to not inherit.
    id = serializers.CharField(source='video_id', read_only=True)
    video_url = serializers.URLField(write_only=True,
                                     required=True,
                                     max_length=URL_MAX_LENGTH)
    video_type = serializers.SerializerMethodField()
    primary_audio_language_code = LanguageCodeField(required=False,
                                                    allow_blank=True)
    original_language = serializers.CharField(source='language',
                                              read_only=True)
    title = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    duration = serializers.IntegerField(required=False)
    thumbnail = VideoThumbnailField(required=False, allow_blank=True)
    created = TimezoneAwareDateTimeField(read_only=True)
    team = TeamSerializer(required=False, allow_null=True)
    project = ProjectSerializer(required=False, allow_null=True)
    all_urls = serializers.SerializerMethodField()
    metadata = VideoMetadataSerializer(required=False)
    languages = VideoLanguageShortSerializer(source='all_subtitle_languages',
                                             many=True, read_only=True)
    activity_uri = serializers.HyperlinkedIdentityField(
        view_name='api:video-activity',
        lookup_field='video_id',
    )
    urls_uri = serializers.HyperlinkedIdentityField(
        view_name='api:video-url-list',
        lookup_field='video_id',
    )
    subtitle_languages_uri = serializers.HyperlinkedIdentityField(
        view_name='api:subtitle-language-list',
        lookup_field='video_id',
    )
    resource_uri = serializers.HyperlinkedIdentityField(
        view_name='api:video-detail',
        lookup_field='video_id')

    default_error_messages = {
        'project-without-team': "Can't specify project without team",
        'unknown-project': 'Unknown project: {project}',
        'video-exists': u'Video already added for {url}',
        'video-policy-error': (u'Video for {url} not moved because it would '
                               'conflict with the video policy for {team}'),
        'invalid-url': u'Invalid URL: {url}',
    }

    class Meta:
        list_serializer_class = VideoListSerializer

    def __init__(self, *args, **kwargs):
        super(VideoSerializer, self).__init__(*args, **kwargs)
        if self.instance:
            # video_url should only be sent for creation
            self.fields['video_url'].read_only = True

    @property
    def team_video(self):
        if self.instance:
            return self.instance.get_team_video()
        else:
            return None

    def get_all_urls(self, video):
        video_urls = list(video.get_video_urls())
        video_urls.sort(key=lambda vurl: vurl.primary, reverse=True)
        return [vurl.url for vurl in video_urls]

    def get_video_type(self, video):
        types = set()
        for url in video.get_video_urls():
            types.add(url.type)
        if len(types) == 1:
            return types.pop()
        return ""

    def will_add_video_to_team(self):
        if not self.team_video:
            return self.validated_data.get('team')
        if self.validated_data.get('team'):
            if self.validated_data['team'] != self.team_video.team:
                return True
            if 'project' in self.validated_data:
                if self.validated_data['project'] != self.team_video.project:
                    return True
        return False

    def will_remove_video_from_team(self):
        if 'team' not in self.validated_data or not self.team_video:
            return False
        return self.team_video.team != self.validated_data['team']

    def to_internal_value(self, data):
        data = self.fixup_data(data)
        return super(VideoSerializer, self).to_internal_value(data)

    def validate(self, data):
        if data.get('project'):
            if not data.get('team'):
                self.fail('project-without-team')
            try:
                data['project'] = Project.objects.get(team=data['team'],
                                                      slug=data['project'])
            except Project.DoesNotExist:
                self.fail('unknown-project', project=data['project'])
        return data

    def fixup_data(self, data):
        """Alter incoming data to support deprecated behavior."""
        data = data.copy()
        for name, value in data.items():
            if value == '':
                # Remove any field has the empty string as its value
                # This is deprecated behavior form the old API.
                del data[name]
            elif name in ('team', 'project') and value == 'null':
                # Replace "null" with None for team/project
                data[name] = None
        return data

    def to_representation(self, video):
        data = super(VideoSerializer, self).to_representation(video)
        # convert blank language codes to None
        if video.primary_audio_language_code == '':
            data['primary_audio_language_code'] = None
            data['original_language'] = None
        extra.video.add_data(self.context['request'], data, video=video)
        return data

    def create(self, validated_data):
        def setup_video(video, video_url):
            for key in ('title', 'description', 'duration', 'thumbnail',
                        'primary_audio_language_code'):
                if validated_data.get(key):
                    setattr(video, key, validated_data[key])
            if validated_data.get('metadata'):
                video.update_metadata(validated_data['metadata'],
                                      commit=False)
        try:
            team = validated_data.get('team')
            if team:
                video, video_url =  team.add_video(
                    validated_data['video_url'],
                    self.context['user'],
                    self.calc_project(validated_data),
                    setup_video)
            else:
                video, video_url = Video.add(validated_data['video_url'],
                                             self.context['user'],
                                             setup_video)
            return video
        except VideoTypeError:
            self.fail('invalid-url', url=validated_data['video_url'])
        except Video.DuplicateUrlError:
            self.fail('video-exists', url=validated_data['video_url'])

    def update(self, video, validated_data):
        simple_fields = (
            'title', 'description', 'duration', 'thumbnail',
            'primary_audio_language_code',
        )
        for field_name in simple_fields:
            if field_name in validated_data:
                if field_name == "duration":
                    if not getattr(video, field_name):
                        setattr(video, field_name, validated_data[field_name])
                else:
                    setattr(video, field_name, validated_data[field_name])
        if validated_data.get('metadata'):
            video.update_metadata(validated_data['metadata'], commit=True)
        try:
            self._update_team(video, validated_data)
        except Video.DuplicateUrlError, e:
            if e.from_prevent_duplicate_public_videos:
                self.fail('video-policy-error', url=e.video_url.url,
                          team=validated_data['team'])
            else:
                self.fail('video-exists', url=e.video_url.url)
        video.save()
        if validated_data.get('thumbnail'):
            videos.tasks.save_thumbnail_in_s3.delay(video.id)
        return video

    def calc_project(self, validated_data):
        team = validated_data.get('team')
        project = validated_data.get('project')
        if team:
            return project if project is not None else team.default_project
        else:
            return None

    def _update_team(self, video, validated_data):
        if 'team' not in validated_data:
            return
        team = validated_data['team']
        project = self.calc_project(validated_data)
        team_video = video.get_team_video()
        if team is None:
            if team_video:
                team_video.remove(self.context['user'])
            video.is_public = True
        else:
            if project is None:
                project = team.default_project
            if team_video:
                team_video.move_to(team, project, self.context['user'])
            else:
                team.add_existing_video(video, self.context['user'], project)

        video.clear_team_video_cache()

@extra.video.handler('player_urls')
def add_player_urls(user, data, video):
    video_urls = list(video.get_video_urls())
    video_urls.sort(key=lambda vurl: vurl.primary, reverse=True)
    data['player_urls'] = [
        vurl.get_video_type().player_url() for vurl in video_urls
    ]

class VideoViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    serializer_class = VideoSerializer
    queryset = Video.objects.all()
    paginate_by = 20

    lookup_field = 'video_id'
    lookup_value_regex = r'(\w|-)+'
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ('title', 'created')

    def get_serializer_context(self):
        return {
            'request': self.request,
            'user': self.request.user,
        }

    def get_queryset(self):
        query_params = self.request.query_params
        if 'team' not in query_params and 'video_url' not in query_params:
            return Video.objects.public().order_by('-id')[:20]
        if 'team' not in query_params:
            qs = self.get_videos_for_user()
        else:
            qs = self.get_videos_for_team(query_params)
        if isinstance(qs, EmptyQuerySet):
            # If the method returned Videos.none(), then stop now rather than
            # call for_url() (#3049)
            return qs
        if 'video_url' in query_params:
            vt = video_type_registrar.video_type_for_url(query_params['video_url'])
            if vt:
                qs = qs.for_url(vt.convert_to_video_url())
            else:
                qs = qs.for_url(query_params['video_url'])
        return qs

    def get_videos_for_user(self):
        query = Q(is_public=True)
        if self.request.user.is_authenticated():
            teams = list(self.request.user.teams.all())
            query = query | Q(teamvideo__team__in=teams)
        return Video.objects.filter(query)

    def get_videos_for_team(self, query_params):
        if query_params['team'] == 'null':
            return Video.objects.filter(teamvideo__team__isnull=True)
        try:
            team = Team.objects.get(slug=query_params['team'])
        except Team.DoesNotExist:
            return Video.objects.none()
        if not team.user_can_view_video_listing(self.request.user):
            return Video.objects.none()

        if 'project' in query_params:
            if query_params['project'] != 'null':
                project_slug = query_params['project']
            else:
                project_slug = "_root"
            try:
                project = team.project_set.get(slug=project_slug)
            except Project.DoesNotExist:
                return Video.objects.none()
            return Video.objects.filter(teamvideo__project=project)
        else:
            return Video.objects.filter(teamvideo__team=team)

    def get_object(self):
        try:
            video = (Video.objects
                     .select_related('teamvideo')
                     .get(video_id=self.kwargs['video_id']))
        except Video.DoesNotExist:
            if self.request.user.is_staff:
                raise http.Http404
            else:
                raise PermissionDenied()
        workflow = video.get_workflow()
        if not workflow.user_can_view_video(self.request.user):
            raise http.Http404
        SubtitleLanguage.bulk_has_public_version(
            video.all_subtitle_languages())
        return video

    def delete(self, request, *args, **kwargs):
        video = self.get_object()
        team_video = video.get_team_video()
        if team_video is not None and \
           team_perms.can_delete_video(team_video,
                                        self.request.user):
            video.delete(user=self.request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        raise PermissionDenied()

    def check_save_permissions(self, serializer):
        team = serializer.validated_data.get('team')
        project = serializer.validated_data.get('project')
        if serializer.will_add_video_to_team():
            if not team_perms.can_add_video(team, self.request.user, project):
                raise PermissionDenied()
        if serializer.instance:
            self.check_update_permissions(serializer)

    def check_update_permissions(self, serializer):
        video = serializer.instance
        team_video = video.get_team_video()
        workflow = video.get_workflow()
        if not workflow.user_can_edit_video(self.request.user):
            raise PermissionDenied()
        if serializer.will_remove_video_from_team():
            if not team_perms.can_remove_video(team_video, self.request.user):
                raise PermissionDenied()

    def perform_create(self, serializer):
        self.check_save_permissions(serializer)
        return serializer.save()

    def perform_update(self, serializer):
        self.check_save_permissions(serializer)
        video = serializer.save()
        videos.tasks.video_changed_tasks.delay(video.pk)
        return video

class VideoURLSerializer(serializers.Serializer):
    created = TimezoneAwareDateTimeField(read_only=True)
    url = serializers.URLField(max_length=URL_MAX_LENGTH)
    primary = serializers.BooleanField(required=False)
    original = serializers.BooleanField(required=False)
    id = serializers.IntegerField(read_only=True)
    resource_uri = serializers.SerializerMethodField()
    videoid = serializers.CharField(read_only=True)
    type = serializers.SerializerMethodField(read_only=True)

    def get_resource_uri(self, video_url):
        return reverse('api:video-url-detail', kwargs={
            'video_id': self.context['video'].video_id,
            'pk': video_url.id,
        }, request=self.context['request'])

    def get_type(self, video_url):
        vt = video_type_registrar[video_url.type]
        return vt.name

    def create(self, validated_data):
        try:
            new_url = self.context['video'].add_url(validated_data['url'], self.context['user'])
        except Video.DuplicateUrlError as e:
            raise serializers.ValidationError("DuplicateUrlError for url: {}".format(e.video_url))

        if validated_data.get('primary'):
            new_url.make_primary(self.context['user'])

        if ('original' in validated_data and
            validated_data['original'] != new_url.original):
            new_url.original = validated_data['original']
            new_url.save()

        return new_url

    def update(self, video_url, validated_data):
        if ('original' in validated_data and
            validated_data['original'] != video_url.original):
            video_url.original = validated_data['original']
            video_url.save()

        if validated_data.get('primary'):
            video_url.make_primary(self.context['user'])

        return video_url

class VideoURLUpdateSerializer(VideoURLSerializer):
    url = serializers.CharField(read_only=True)

class VideoDurationView(views.APIView):
    def get(self, request, video_id, *args, **kwargs):
        video = Video.objects.get(video_id=video_id)
        workflow = video.get_workflow()
        if not workflow.user_can_view_video(request.user):
            return Response("Not authorized", status=status.HTTP_401_UNAUTHORIZED)
        return Response({'duration': video.duration}, status=status.HTTP_200_OK)

    def put(self, request, video_id, *args, **kwargs):
        video = Video.objects.get(video_id=video_id)
        workflow = video.get_workflow()
        if not workflow.user_can_view_video(request.user):
            return Response("Not authorized", status=status.HTTP_401_UNAUTHORIZED)
        if not video.duration:
            new_duration = request.data.get('duration', None)
            if new_duration is not None:
                video.duration = new_duration
                video.save()
                return Response({'duration': video.duration}, status=status.HTTP_200_OK)
            else:
                return Response("Duration is missing", status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response("Duration already set", status=status.HTTP_304_NOT_MODIFIED)

class VideoFollowerView(views.APIView):
    def get(self, request, video_id, *args, **kwargs):
        video = Video.objects.get(video_id=video_id)
        return Response({'follow': video.user_is_follower(request.user)}, status=status.HTTP_200_OK)

    def post(self, request, video_id, *args, **kwargs):
        video = Video.objects.get(video_id=video_id)
        follow = True if request.data.get('follow', "off") == "on" else False
        if follow == video.user_is_follower(request.user):
            return Response("Not modified", status=status.HTTP_304_NOT_MODIFIED)
        else:
            if follow:
                video.followers.add(request.user)
            else:
                video.followers.remove(request.user)
            return Response({'follow': follow}, status=status.HTTP_200_OK)

class VideoURLViewSet(viewsets.ModelViewSet):
    serializer_class = VideoURLSerializer
    update_serializer_class = VideoURLUpdateSerializer

    def get_serializer_class(self):
        if 'pk' in self.kwargs:
            return self.update_serializer_class
        else:
            return self.serializer_class

    @property
    def video(self):
        if not hasattr(self, '_video'):
            self._video = Video.objects.get(video_id=self.kwargs['video_id'])
        return self._video

    def get_queryset(self):
        return self.video.videourl_set.all().select_related('video')

    def check_view_permissions(self):
        workflow = self.video.get_workflow()
        if not workflow.user_can_view_video(self.request.user):
            raise PermissionDenied()

    def check_edit_permissions(self):
        workflow = self.video.get_workflow()
        if not workflow.user_can_edit_video(self.request.user):
            raise PermissionDenied()

    def perform_create(self, serializer):
        self.check_edit_permissions()
        return serializer.save()

    def perform_update(self, serializer):
        self.check_edit_permissions()
        return serializer.save()

    def perform_destroy(self, instance):
        self.check_edit_permissions()
        if instance.primary:
            raise serializers.ValidationError("Can't delete the primary URL")
        instance.remove(self.request.user)

    def get_serializer_context(self):
        return {
            'video': self.video,
            'user': self.request.user,
            'request': self.request,
        }
