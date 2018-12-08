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
"""
Subtitles
---------

Subtitle Language Resource
**************************

Container for subtitles in one language for a video.  Subtitle languages are
typically created when the first editing session is started.

To see all possible languages see :ref:`languages`.

Listing languages for a video
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/videos/(video-id)/languages/

    Get a list of subtitle languages for a video

    List results are paginated.

    :>json bcp-47 language_code: Subtitle language
    :>json string name: Human-readable name for this language
    :>json boolean is_primary_audio_language: Is this language the primary
        language spoken in the video?
    :>json boolean is_rtl: Is this language RTL?
    :>json uri resource_uri: Subtitle Language Resource
    :>json iso-8601 created: when the language was created
    :>json string title: Video title, translated into this language
    :>json string description: Video description, translated into this language
    :>json dict metadata: Video metadata, translated into this language
    :>json boolean subtitles_complete: Are the subtitles complete for this
        language?
    :>json integer subtitle_count: Number of subtitles for this language
    :>json string reviewer: Username of the reviewer for task-based teams
    :>json string approver: Username of the approver for task-based teams
    :>json boolean is_translation: Is this language translated from other
        languages? **(deprecated)**
    :>json boolean published: Are the subtitles publicly viewable?
    :>json string original_language_code: Source translation language
        **(deprecated)**
    :>json integer num_versions: Number of subtitle versions, the length of the
       versions array should be used instead of this **(deprecated)**
    :>json integer id: Internal ID for the language **(deprecated)**
    :>json boolean is_original: alias for is_primary_audio_language
        **(deprecated)**
    :>json list versions: List of subtitle version data.  See below for details.

    Subtitle version data:

    :>json user-data author: Subtitle author (see :ref:`user_fields`)
    :>json integer version_no: number of the version
    :>json boolean published: is this version publicly viewable?

    .. note::
        `original_language_code` and `is_translation` fields are remnants from
        the old subtitle system.  With the new editor, users can use multiple
        languages as a translation source.  These fields are should not be
        relied on.

Getting details on a specific language
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/videos/(video-id)/languages/(language-code)/

    The response data is the same as the listing

Creating subtitle languages
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:post:: /api/videos/(video-id)/languages/

    :<json string language_code: bcp-47 code for the language
    :<json boolean is_primary_audio_language: Is this the primary spoken
        language of the video? *(optional)*.
    :<json boolean subtitles_complete: Are the subtitles for this
       language complete? *(optional)*.
    :<json boolean is_original: Alias for is_primary_audio_language
        **(deprecated)**
    :<json boolean is_complete: Alias for subtitles_complete  **(deprecated)**
    :<json integer soft_limit_lines: Controls the max number of lines per
        subtitle.  A warning is shown in the editor if this limit is exceeded.
    :<json integer soft_limit_min_duration: Controls min duration of subtitles
        in milliseconds.  A warning is shown in the editor if this limit is
        exceeded.
    :<json integer soft_limit_max_duration: Controls max duration of subtitles
        in milliseconds.  This controls the message in the guidelines dialog.
    :<json integer soft_limit_cpl: Controls the max characters per line for
        subtitles.  A warning is shown in the editor if this limit is exceeded.
    :<json integer soft_limit_cps: Controls the max characters per second for
        subtitles.  A warning is shown in the editor if this limit is exceeded.

Updating subtitle languages
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:put:: /api/videos/(video-id)/languages/(language-code)/

    The request data is the same as when creating languages, except
    ``language_code`` is not allowed.

.. _subtitles_resource:

Subtitles Resource
******************

Subtitle data in one language for a video.

Fetching subtitles for a given language
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. http:get:: /api/videos/(video-id)/languages/(language-code)/subtitles/

    :queryparam sub_format: The format to return the subtitles in.  This can
        be any format that amara supports including dfxp, srt, vtt, and sbv.
        The default is json, which returns subtitle data encoded list of json
        dicts.
    :queryparam version_number: version number to fetch.  Versions are listed
        in the VideoLanguageResouce request.  If none is specified, the latest
        public version will be returned.  If you want the latest private
        version (and have access to it) use "last".
    :queryparam version: Alias for version_number **(deprecated)**

    :>json integer version_number: version number for the subtitles
    :>json object subtitles: Subtitle data.  The format depends on the
        sub_format param
    :>json user-data author: Subtitle author (see :ref:`user_fields`)
    :>json string sub_format: Format of the subtitles
    :>json object language: Language data
    :>json string title: Video title, translated into the subtitle's language
    :>json string description: Video description, translated into the subtitle's
        language
    :>json string metadata: Video metadata, translated into the subtitle's language
    :>json string video_title: Video title, translated into the video's language
    :>json string video_description: Video description, translated into the video's
        language
    :>json uri notes_uri: Subtitle notes resource
    :>json uri actions_uri: Subtitle actions resource
    :>json uri resource_uri: Subtitles resource
    :>json url site_uri: URL to view the subtitles on site
    :>json string video: Copy of video_title **(deprecated)**
    :>json integer version_no: Copy of version_number **(deprecated)**

    **Language data:**

    :>json bcp-47 code: Language of the subtitles
    :>json string name: Human-readable name for the language
    :>json string dir: Language direction ("ltr" or "rtl")

Getting subtitle data only
^^^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes you want just subtitles data without the rest of the data.  This
is possible using a special Accept header or the `format` query
parameter.  This can be used to download a DFXP, SRT, or any other
subtitle format that Amara supports.  If one of these is used, then the
sub_format param will be ignored.

==================== ======================= ===================
Format                Accept header           format query param
==================== ======================= ===================
DFXP                  application/ttml+xml    dfxp
SBV                   text/sbv                sbv
SRT                   text/srt                srt
SSA                   text/ssa                ssa
WEBVTT                text/vtt                vtt
==================== ======================= ===================

**Examples:**

.. sourcecode:: http

    GET /api/videos/(video-id)/languages/(language-code)/subtitles/?format=dfxp

.. sourcecode:: http

    GET /api/videos/(video-id)/languages/(language-code)/subtitles/
    Accept: application/ttml+xml

Creating new subtitles
^^^^^^^^^^^^^^^^^^^^^^

.. http:post:: /api/videos/(video-id)/languages/(language-code)/subtitles/

    :<json object subtitles: The subtitles to submit, as a string. The
        format depends on the sub_format param.
    :<json object subtitles_url: Alternatively, subtitles can be given
        as a text file URL.  The format depends on the sub_format param.
    :<json string sub_format: The format used to parse the subs. The same
        formats as for fetching subtitles are accepted. Optional - defaults to
        "dfxp".
    :<json string title: Give a title to the new revision
    :<json string description: Give a description to the new revision
    :<json string action: Name of the action to perform - optional, but
        recommended.  If given, the is_complete param will be ignored.  For
        more details, see the subtitles action documentation by following the
        `actions_uri` field.
    :<json boolean is_complete: Boolean indicating if the complete subtitling
        set is available for this language - optional, defaults to false.
        **(deprecated, use action instead)**

Deleting subtitles
^^^^^^^^^^^^^^^^^^

.. http:delete:: /api/videos/(video-id)/languages/(language-code)/subtitles/

   This will delete all subtitle versions for a language.  It's only allowed
   if the video is part of a team and the API user is an admin for that team.

.. _subtitle_actions_resource:

Subtitle Actions Resource
*************************

Subtitle actions are operations on subtitles.  Actions correspond to the
buttons in the upper-right hand corner of the subtitle editor (save, save
a draft, approve, reject, etc).  This resource is used to list and perform
actions on the subtitle set.

**Note:** You can also perform an action together with adding new subtitles
using the action field of the subtitles resource.

Listing actions
^^^^^^^^^^^^^^^

.. http:get:: /api/videos/(video-id)/languages/(language-code)/subtitles/actions/

    Get a list of possible actions for a subtitle set.

    :>json string action: Action name
    :>json string label: Human-friendly string for the action
    :>json boolean complete: Does this action complete the subtitles?  If true,
        then when the action is performed, we will mark the subtitles
        complete.  If false, we will mark them incomplete.  If null, then we
        will not change the subtitles_complete flag.

Performing actions
^^^^^^^^^^^^^^^^^^

.. http:post:: /api/videos/(video-id)/languages/(language-code)/subtitles/actions/

    Perform an action on a subtitle set.  This is like opening the subtitles
    in the editor, not changing anything, and clicking an action button
    (Publish, Save Draft, etc.)

    :<json string action: name of the action to perform

Subtitle Notes Resource
***********************

Subtitle notes saved in the editor.

.. note:: Subtitle notes are currently only supported for team videos

Fetching notes
^^^^^^^^^^^^^^

.. http:get:: /api/videos/(video-id)/languages/(language-code)/subtitles/notes

    :>json username user: Username of the note author
    :>json iso-8601 datetime: when the note was created
    :>json string body: text of the note.

Adding notes
^^^^^^^^^^^^

.. http:post:: /api/videos/(video-id)/languages/(language-code)/subtitles/notes/

    :<json string body: note body
"""

from __future__ import absolute_import

import json
import logging

from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics
from rest_framework import mixins
from rest_framework import renderers
from rest_framework import serializers
from rest_framework import status
from rest_framework import views
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .videos import VideoMetadataSerializer
from api import extra
from api.fields import (LanguageCodeField, TimezoneAwareDateTimeField,
                        UserField)
from api.views.apiswitcher import APISwitcherMixin
from videos.models import Video
from subtitles import compat
from subtitles import pipeline
from subtitles import workflows
from subtitles.models import (SubtitleLanguage, SubtitleVersion,
                              ORIGIN_UPLOAD, ORIGIN_WEB_EDITOR, ORIGIN_API)
from subtitles.exceptions import ActionError
from subtitles.permissions import user_can_access_subtitles_format
from subtitles.types import SubtitleFormatList
import babelsubs
from babelsubs.storage import SubtitleSet
from utils.http import data_from_url
from utils.subtitles import load_subtitles
import videos.tasks
import teams.permissions

logger = logging.getLogger(__name__)

class MiniSubtitleVersionSerializer(serializers.Serializer):
    """Serialize a subtitle version for SubtitleLanguageSerializer """
    author = UserField(read_only=True)
    published = serializers.BooleanField(source='is_public')
    version_no = serializers.IntegerField(source='version_number')

class MiniSubtitleVersionsField(serializers.ListField):
    """Serialize the list of versions for SubtitleLanguageSerializer """
    child = MiniSubtitleVersionSerializer()

    def get_attribute(self, language):
        versions = self.context['versions'][language.id]
        if self.context['show_private_versions'](language.language_code):
            return versions
        else:
            return [v for v in versions if v.is_public()]

def _fetch_versions(languages, context):
    """Fetch all SubtitleVersion objects that we need to display.

    This method optimizes a bunch of things to avoid extra queries in the
    list/detail views.

    Args:
        languages: list of languages
        context: serializer context.  We will store a dict mapping language
            ids to versions using the "versions" key

    """
    context['versions'] = SubtitleVersion.objects.fetch_for_languages(
        languages, video=context['video'],
        order_by='-version_number',
        select_related=('author',),
        prefetch_related=('metadata',))

class SubtitleLanguageListSerializer(serializers.ListSerializer):
    def to_representation(self, qs):
        languages = list(qs)
        _fetch_versions(languages, self.context)
        super_class = super(SubtitleLanguageListSerializer, self)
        return super_class.to_representation(languages)

class SubtitleLanguageSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    created = TimezoneAwareDateTimeField(read_only=True)
    language_code = LanguageCodeField()
    is_primary_audio_language = serializers.BooleanField(required=False)
    is_rtl = serializers.BooleanField(read_only=True)
    is_translation = serializers.SerializerMethodField()
    soft_limit_lines = serializers.IntegerField(
        required=False, min_value=1, allow_null=True)
    soft_limit_min_duration = serializers.IntegerField(
        required=False, min_value=1, allow_null=True)
    soft_limit_max_duration = serializers.IntegerField(
        required=False, min_value=1, allow_null=True)
    soft_limit_cps = serializers.IntegerField(
        required=False, min_value=1, allow_null=True)
    soft_limit_cpl = serializers.IntegerField(
        required=False, min_value=1, allow_null=True)
    published = serializers.BooleanField(read_only=True,
                                         source='has_public_version')
    original_language_code = serializers.SerializerMethodField()
    name = serializers.CharField(source='get_language_code_display',
                                 read_only=True)
    title = serializers.CharField(source='get_title', read_only=True)
    description = serializers.CharField(source='get_description',
                                        read_only=True)
    metadata = VideoMetadataSerializer(required=False, read_only=True)
    subtitle_count = serializers.IntegerField(read_only=True,
                                              source='get_subtitle_count')
    subtitles_complete = serializers.BooleanField(required=False)
    versions = MiniSubtitleVersionsField(read_only=True)
    subtitles_uri = serializers.SerializerMethodField()
    resource_uri = serializers.SerializerMethodField()

    default_error_messages = {
        'language-exists': 'Language already created: {language_code}',
    }

    class Meta:
        list_serializer_class = SubtitleLanguageListSerializer

    def __init__(self, *args, **kwargs):
        super(SubtitleLanguageSerializer, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['language_code'].read_only = True

    def get_is_translation(self, language):
        return compat.subtitlelanguage_is_translation(language)

    def get_original_language_code(self, language):
        return compat.subtitlelanguage_original_language_code(language)

    def get_subtitles_uri(self, language):
        kwargs = {
            'video_id': language.video.video_id,
            'language_code': language.language_code,
        }
        return reverse('api:subtitles', kwargs=kwargs,
                       request=self.context['request'])

    def get_resource_uri(self, language):
        kwargs = {
            'video_id': language.video.video_id,
            'language_code': language.language_code,
        }
        return reverse('api:subtitle-language-detail', kwargs=kwargs,
                       request=self.context['request'])

    def to_representation(self, language):
        if 'versions' not in self.context:
            # For the list view, the SubtitleLanguageListSerializer generates
            # versions, for the detail view we need to generate versions
            # ourselves
            _fetch_versions([language], self.context)
        data = super(SubtitleLanguageSerializer, self).to_representation(
            language)
        data['num_versions'] = len(data['versions'])
        data['is_original'] = data['is_primary_audio_language']
        self.add_reviewer_and_approver(data, language)
        if self.context['allow_extra']:
            extra.video_language.add_data(self.context['request'], data,
                                          video=self.context['video'],
                                          language=language)
        return data

    def add_reviewer_and_approver(self, data, language):
        """Add the reviewer/approver fields."""
        for version in self.context['versions'][language.id]:
            reviewer = version.get_reviewed_by()
            approver = version.get_approved_by()
            if reviewer:
                data['reviewer'] = reviewer.username
            if approver:
                data['approver'] = approver.username

    def validate_language_code(self, language_code):
        if (SubtitleLanguage.objects
            .filter(video=self.context['video'],
                    language_code=language_code)
            .exists()):
            raise serializers.ValidationError("Language already exists")
        return language_code

    def create(self, validated_data):
        language = SubtitleLanguage.objects.create(
            video=self.context['video'],
            language_code=validated_data['language_code'])
        try:
            return self.update(language, validated_data)
        except IntegrityError:
            self.fail('language-exists',
                      language_code=language.language_code)

    def update(self, language, validated_data):
        subtitles_complete = validated_data.get(
            'subtitles_complete',
            self.initial_data.get('is_complete', None))
        primary_audio_language = validated_data.get(
            'is_primary_audio_language',
            self.initial_data.get('is_original', None))

        video = self.context['video']
        if subtitles_complete is not None:
            language.subtitles_complete = subtitles_complete
        language.soft_limit_lines = validated_data.get('soft_limit_lines')
        language.soft_limit_min_duration = validated_data.get(
            'soft_limit_min_duration')
        language.soft_limit_max_duration = validated_data.get(
            'soft_limit_max_duration')
        language.soft_limit_cpl = validated_data.get('soft_limit_cpl')
        language.soft_limit_cps = validated_data.get('soft_limit_cps')

        language.save()
        if primary_audio_language is not None:
            video.primary_audio_language_code = language.language_code
            video.save()
        videos.tasks.video_changed_tasks.delay(video.pk)
        return language

class SubtitleLanguageViewSet(mixins.CreateModelMixin,
                              mixins.RetrieveModelMixin,
                              mixins.UpdateModelMixin,
                              mixins.ListModelMixin,
                              viewsets.GenericViewSet):
    serializer_class = SubtitleLanguageSerializer
    paginate_by = 20

    lookup_field = 'language_code'
    lookup_value_regex = r'[\w-]+'

    @property
    def video(self):
        if not hasattr(self, '_video'):
            qs = Video.objects.select_related("teamvideo")
            self._video = get_object_or_404(qs,
                                            video_id=self.kwargs['video_id'])
        return self._video

    def get_queryset(self):
        workflow = self.video.get_workflow()
        if not workflow.user_can_view_video(self.request.user):
            raise PermissionDenied()
        return self.video.newsubtitlelanguage_set.all()

    def show_private_versions(self, language_code):
        workflow = self.video.get_workflow()
        return workflow.user_can_view_private_subtitles(self.request.user,
                                                        language_code)

    def perform_create(self, serializer):
        self.check_soft_limit_permissions(serializer)
        return serializer.save()

    def perform_update(self, serializer):
        self.check_soft_limit_permissions(serializer)
        return serializer.save()

    def check_soft_limit_permissions(self, serializer):
        if not any(key.startswith('soft_limit')
                   for key in serializer.validated_data):
            return
        team = self.video.get_team()
        if team and not teams.permissions.can_set_soft_limits(
                team, self.request.user, self.video,
                self.kwargs['language_code']):
            raise PermissionDenied()

    def get_serializer_context(self):
        return {
            'allow_extra': self.action == 'retrieve',
            'request': self.request,
            'video': self.video,
            'show_private_versions': self.show_private_versions,
        }

class SubtitleRenderer(renderers.BaseRenderer):
    """Render SubtitleSets using babelsubs."""
    def render(self, data, media_type=None, renderer_context=None):
        if isinstance(data, SubtitleSet):
            return babelsubs.to(data, self.format)
        else:
            # Fall back to JSON renderer for other responses.  This handles
            # things like permissions errors and 404 errors
            return renderers.JSONRenderer().render(data)

class DFXPRenderer(SubtitleRenderer):
    media_type = 'application/ttml+xml'
    format = 'dfxp'

class SBVRenderer(SubtitleRenderer):
    media_type = 'text/sbv'
    format = 'sbv'

class SRTRenderer(SubtitleRenderer):
    media_type = 'text/srt'
    format = 'srt'

class SSARenderer(SubtitleRenderer):
    media_type = 'text/ssa'
    format = 'ssa'

class VTTRenderer(SubtitleRenderer):
    media_type = 'text/vtt'
    format = 'vtt'

class TextRenderer(SubtitleRenderer):
    media_type = 'text/plain'
    format = 'txt'

class SubtitlesField(serializers.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update(style={
            'base_template': 'textarea.html',
            'rows': 10,
        })
        super(SubtitlesField, self).__init__(*args, **kwargs)

    def get_attribute(self, version):
        return babelsubs.to(version.get_subtitles(),
                            self.context['sub_format'])

    def to_representation(self, value):
        if self.context['sub_format'] == 'json':
            # special case the json format.  We want to return actual JSON
            # data rather than the string encoding of that data.
            return json.loads(value)
        else:
            return value

    def to_internal_value(self, value):
        if not isinstance(value, basestring):
            raise serializers.ValidationError("Invalid subtitle data")
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        try:
            return load_subtitles(
                self.context['language_code'], value,
                self.context['sub_format'])
        except babelsubs.SubtitleParserError, e:
            logger.warn("Error parsing subtitles ({}/{})".format(
                self.context['video'].video_id,
                self.context['language_code']), exc_info=True)
            raise serializers.ValidationError("Invalid subtitle data")

class SubFormatField(serializers.ChoiceField):
    def __init__(self, **kwargs):
        kwargs['choices'] = babelsubs.get_available_formats()
        super(SubFormatField, self).__init__(**kwargs)

    def get_attribute(self, version):
        return self.context['sub_format']

class LanguageForSubtitlesSerializer(serializers.Serializer):
    code = serializers.CharField(source='language_code')
    name = serializers.CharField(source='get_language_code_display')
    dir = serializers.CharField()

class SubtitlesSerializer(serializers.Serializer):
    ORIGIN_CHOICES = [
        ('api', _('API')),
        ('editor', _('Subtitle editor')),
        ('upload', _('Upload')),
    ]
    version_number = serializers.IntegerField(read_only=True)
    sub_format = SubFormatField(required=False, default='dfxp', initial='dfxp')
    subtitles = SubtitlesField(required=False)
    subtitles_url = serializers.URLField(max_length=512, required=False, write_only=True)
    author = UserField(read_only=True)
    action = serializers.CharField(required=False, write_only=True,
                                   allow_blank=True)
    is_complete = serializers.NullBooleanField(required=False,
                                               write_only=True)
    origin = serializers.ChoiceField(
        required=False, write_only=True,
        default='api', choices=ORIGIN_CHOICES)
    language = LanguageForSubtitlesSerializer(source='*', read_only=True)
    title = serializers.CharField(required=False, allow_blank=True)
    duration = serializers.IntegerField(required=False, write_only=True)
    description = serializers.CharField(required=False, allow_blank=True)
    metadata = VideoMetadataSerializer(required=False)
    video_title = serializers.CharField(source='video.title_display',
                                        read_only=True)
    video_description = serializers.CharField(source='video.description',
                                              read_only=True)
    actions_uri = serializers.SerializerMethodField()
    notes_uri = serializers.SerializerMethodField()
    resource_uri = serializers.SerializerMethodField()
    site_uri = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super(SubtitlesSerializer, self).__init__(*args, **kwargs)
        if 'sub_format' in self.fields:
            for format in self.fields['sub_format'].choices:
                if not user_can_access_subtitles_format(self.context['user'], format):
                    self.fields['sub_format'].choices.pop(format)

    def get_actions_uri(self, version):
        kwargs = {
            'video_id': version.video.video_id,
            'language_code': version.language_code,
        }
        return reverse('api:subtitle-actions', kwargs=kwargs,
                      request=self.context['request'])

    def get_notes_uri(self, version):
        kwargs = {
            'video_id': version.video.video_id,
            'language_code': version.language_code,
        }
        return reverse('api:subtitle-notes', kwargs=kwargs,
                      request=self.context['request'])

    def get_resource_uri(self, version):
        kwargs = {
            'video_id': version.video.video_id,
            'language_code': version.language_code,
        }
        uri = reverse('api:subtitles', kwargs=kwargs,
                      request=self.context['request'])
        if self.context['version_number']:
            uri += '?version_number={}'.format(self.context['version_number'])
        return uri

    def get_site_uri(self, version):
        kwargs = {
            'video_id': version.video.video_id,
            'lang': version.language_code,
            'lang_id': version.subtitle_language_id,
            'version_id': version.id,
        }
        return reverse('videos:subtitleversion_detail', kwargs=kwargs,
                       request=self.context['request'])

    def validate(self, data):
        """
        Check that subtitles are provided, either via a string
        or a URL.
        """
        if ('subtitles' in data) == ('subtitles_url' in data):
            raise serializers.ValidationError("Subtitles must be provided either via a string or a URL")
        return data

    def validate_origin(self, value):
        if not value or value == 'api':
            return ORIGIN_API
        elif value == 'editor':
            return ORIGIN_WEB_EDITOR
        elif value == 'upload':
            return ORIGIN_UPLOAD
        else:
            raise ValidationError('invalid origin value: {}'.format(value))

    def to_representation(self, version):
        data = super(SubtitlesSerializer, self).to_representation(version)
        # copy a fields to deprecated names
        data['video'] = data['video_title']
        data['version_no'] = data['version_number']
        if self.context['allow_language_extra']:
            extra.video_language.add_data(self.context['request'], data,
                                          video=self.context['video'],
                                          language=version.subtitle_language)
        return data

    def to_internal_value(self, data):
        # set sub_format from the inputted data.  We need this to properly
        # parse the subtitles param
        if data.get('sub_format'):
            self.context['sub_format'] = data['sub_format']
        else:
            self.context['sub_format'] = 'dfxp'
        return super(SubtitlesSerializer, self).to_internal_value(data)

    def _process_subtitles_url(self, subtitles_url):
        value = data_from_url(subtitles_url)
        if not isinstance(value, basestring):
            raise serializers.ValidationError("Invalid subtitle data")
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        try:
            return load_subtitles(
                self.context['language_code'], value,
                self.context['sub_format'])
        except babelsubs.SubtitleParserError, e:
            logger.warn("Error parsing subtitles ({}/{})".format(
                self.context['video'].video_id,
                self.context['language_code']), exc_info=True)
            raise serializers.ValidationError("Invalid subtitle data")

    def create(self, validated_data):
        action = complete = None
        if 'action' in validated_data:
            action = validated_data.get("action")
        elif 'is_complete' in validated_data:
            complete = validated_data['is_complete']
        if 'subtitles' in validated_data:
            subtitles = validated_data['subtitles']
        else:
            subtitles = self._process_subtitles_url(validated_data['subtitles_url'])
        return pipeline.add_subtitles(
            self.context['video'], self.context['language_code'],
            subtitles,
            action=action, complete=complete,
            title=validated_data.get('title'),
            description=validated_data.get('description'),
            duration=validated_data.get('duration'),
            metadata=validated_data.get('metadata'),
            author=self.context['user'],
            committer=self.context['user'],
            origin=validated_data.get('origin'))

class SubtitlesView(generics.CreateAPIView):
    # Note that even though we only inherit from CreateAPIView, we support
    # more methods than just POST.  However for those methods we don't use
    # the generic django-rest-framework implementation.
    serializer_class = SubtitlesSerializer
    renderer_classes = views.APIView.renderer_classes + [
        DFXPRenderer, SBVRenderer, SSARenderer, SRTRenderer, VTTRenderer,
        TextRenderer,
    ]
    permission_classes = (IsAuthenticatedOrReadOnly,)
    def set_renderer_classes(self, user):
        self.renderer_classes = views.APIView.renderer_classes + [
            DFXPRenderer, SBVRenderer, SSARenderer, SRTRenderer, VTTRenderer,
            TextRenderer,
        ]
        for f in SubtitleFormatList.for_staff():
            if user_can_access_subtitles_format(user, f):
                renderer = type(f, (SubtitleRenderer,), {
                    'media_type': ('application/' + f),
                    'format': f
                })
                self.renderer_classes.append(renderer)

    def get_video(self):
        if not hasattr(self, '_video'):
            try:
                self._video = Video.objects.get(
                    video_id=self.kwargs['video_id'])
            except Video.DoesNotExist:
                raise Http404
        return self._video

    def get_serializer_context(self):
        return {
            'video': self.get_video(),
            'language_code': self.kwargs['language_code'].lower(),
            'user': self.request.user,
            'request': self.request,
            'sub_format': self.request.query_params.get('sub_format', 'json'),
            'version_number': None,
            # Allow users to use the extra params from the language endpoint,
            # but only if they're requesting the current public version.
            'allow_language_extra': (
                'version' not in self.request.query_params and
                'version_number' not in self.request.query_params),
        }

    def get(self, request, *args, **kwargs):
        version = self.get_object()
        # If we're rendering the subtitles directly, then we skip creating a
        # serializer and return the subtitles instead
        if isinstance(request.accepted_renderer, SubtitleRenderer):
            if user_can_access_subtitles_format(request.user, request.accepted_renderer.format):
                return Response(version.get_subtitles())
            else:
                raise PermissionDenied()
        serializer = self.get_serializer(version)
        if user_can_access_subtitles_format(request.user, serializer.context['sub_format']):
            return Response(serializer.data)
        else:
            raise PermissionDenied()

    def get_object(self):
        video = self.get_video()
        workflow = workflows.get_workflow(video)
        language_code = self.kwargs['language_code']
        if not workflow.user_can_view_video(self.request.user):
            raise PermissionDenied()
        language = video.subtitle_language(language_code)
        if language is None:
            raise Http404
        version_number = self.request.query_params.get('version_number')
        if version_number is None:
            version_number = self.request.query_params.get('version')
        if version_number is not None:
            version = self.get_object_from_version_number(language,
                                                          version_number)
        else:
            version = language.get_public_tip()
        if version is None or version.is_deleted():
            raise Http404
        if (not version.is_public() and
            not workflow.user_can_view_private_subtitles(self.request.user,
                                                         language_code)):
            raise PermissionDenied()
        return version

    def get_object_from_version_number(self, language, version_number):
        if version_number == 'last':
            return language.get_tip()
        try:
            version_number = int(version_number)
        except ValueError:
            raise ValidationError('invalid version number')
        return get_object_or_404(language.subtitleversion_set.extant(),
                                 version_number=version_number)

    def initial(self, request, *args, **kwargs):
        self.set_renderer_classes(request.user)
        super(SubtitlesView, self).initial(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        video = self.get_video()
        workflow = workflows.get_workflow(video)
        if not workflow.user_can_edit_subtitles(self.request.user, self.kwargs['language_code']) or \
           not user_can_access_subtitles_format(self.request.user, self.request.data.get('sub_format', None)):
            raise PermissionDenied()
        if not workflow.user_can_set_video_duration(self.request.user):
            request.data.pop('duration', None)
        try:
            version = super(SubtitlesView, self).create(request, *args,
                                                        **kwargs)
        except (ActionError, LookupError), e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        videos.tasks.video_changed_tasks.delay(video.pk)
        return version

    def delete(self, request, *args, **kwargs):
        language_code = kwargs['language_code']
        video = self.get_video()
        workflow = workflows.get_workflow(video)
        if not workflow.user_can_delete_subtitles(
                self.request.user, language_code):
            raise PermissionDenied()
            request.data.pop('duration', None)
        subtitle_language = video.subtitle_language(language_code)
        subtitle_language.nuke_language()
        videos.tasks.video_changed_tasks.delay(video.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

class LanguageFollowerView(views.APIView):
    def get(self, request, video_id, language_code, *args, **kwargs):
        subtitle_language = Video.objects.get(video_id=video_id).subtitle_language(language_code)
        return Response({'follow': subtitle_language.user_is_follower(request.user)}, status=status.HTTP_200_OK)

    def post(self, request, video_id, language_code, *args, **kwargs):
        subtitle_language = Video.objects.get(video_id=video_id).subtitle_language(language_code)
        follow = True if request.data.get('follow', "off") == "on" else False
        if follow == subtitle_language.user_is_follower(request.user):
            return Response("Not modified", status=status.HTTP_304_NOT_MODIFIED)
        else:
            if follow:
                subtitle_language.followers.add(request.user)
            else:
                subtitle_language.followers.remove(request.user)
            return Response({'follow': follow}, status=status.HTTP_200_OK)

class ActionsSerializer(serializers.Serializer):
    action = serializers.CharField(source='name')
    label = serializers.CharField(read_only=True)
    complete = serializers.BooleanField(read_only=True)

class Actions(views.APIView):
    def get_serializer(self, **kwargs):
        return ActionsSerializer(**kwargs)

    def get(self, request, video_id, language_code, format=None):
        video = get_object_or_404(Video, video_id=video_id)
        workflow = workflows.get_workflow(video)
        if not workflow.user_can_edit_subtitles(request.user, language_code):
            raise PermissionDenied()
        action_list = workflow.get_actions(request.user, language_code)
        serializer = ActionsSerializer(action_list, many=True)
        return Response(serializer.data)

    def post(self, request, video_id, language_code, format=None):
        try:
            action = request.data['action']
        except KeyError:
            return Response('no action', status=status.HTTP_400_BAD_REQUEST)
        video = get_object_or_404(Video, video_id=video_id)
        workflow = workflows.get_workflow(video)
        if not workflow.user_can_edit_subtitles(request.user, language_code):
            raise PermissionDenied()
        language = video.subtitle_language(language_code)
        if (language is None or 
            (language.get_tip() is None
             and workflow.action_requires_subtitle_language_tip(request.user, language_code, action))):
            return Response('No subtitles',
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            workflow.perform_action(request.user, language_code, action)
        except (ActionError, LookupError), e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        return Response('')

class NotesSerializer(serializers.Serializer):
    user = UserField(read_only=True)
    created = TimezoneAwareDateTimeField(read_only=True)
    body = serializers.CharField()

    def create(self, validated_data):
        if self.context['editor_notes'] is None:
            raise PermissionDenied()
        return self.context['editor_notes'].post(
            self.context['user'], validated_data['body'])

class NotesList(generics.ListCreateAPIView):
    serializer_class = NotesSerializer

    @csrf_exempt
    def dispatch(self, request, **kwargs):
        self.editor_notes = self.get_editor_notes(request.user, **kwargs)
        return generics.ListCreateAPIView.dispatch(self, request, **kwargs)

    def get_editor_notes(self, user, **kwargs):
        video = get_object_or_404(Video, video_id=kwargs['video_id'])
        workflow = workflows.get_workflow(video)
        return workflow.get_editor_notes(user, kwargs['language_code'])

    def get_queryset(self):
        return self.editor_notes.notes

    def get_serializer_context(self):
        return {
            'editor_notes': self.editor_notes,
            'user': self.request.user,
            'request': self.request,
        }
