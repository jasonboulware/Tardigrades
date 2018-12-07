# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
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

"""utils.factories.py -- Factoryboy factories for testing
"""

from __future__ import absolute_import

import datetime
import hashlib
import os

from django.contrib.auth.hashers import make_password
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.defaultfilters import slugify
import factory
from factory import Factory
from factory.django import DjangoModelFactory

import auth.models
import babelsubs.storage
import comments.models
import externalsites.models
import subtitles.models
import teams.models
import videos.models
from externalsites import google
from subtitles import pipeline
from utils import dates
from utils import translation

class VideoURLFactory(DjangoModelFactory):
    FACTORY_FOR = videos.models.VideoUrl

    url = factory.Sequence(
        lambda n: 'http://example.com/videos/video-{0}'.format(n))
    type = videos.models.VIDEO_TYPE_HTML5

class VideoFactory(DjangoModelFactory):
    FACTORY_FOR = videos.models.Video

    title = factory.Sequence(lambda n: 'Test Video {0}'.format(n))
    duration = 100
    allow_community_edits = False

    video_url = factory.RelatedFactory(VideoURLFactory, 'video', primary=True)

    @factory.post_generation
    def set_follower(video, create, extracted, **kwargs):
        if video.user:
            video.followers.add(video.user)

    @factory.post_generation
    def make_version(video, create, extracted, **attrs):
        if extracted:
            if extracted is True:
                languages = ['en']
            elif isinstance(extracted, (list, tuple)):
                languages = extracted
            else:
                languages = [extracted]
            for language in languages:
                make_version(video, language)

    @factory.post_generation
    def team(video, create, extracted, **attrs):
        if extracted:
            TeamVideoFactory(team=extracted, video=video,
                             added_by=video.user)

    @factory.post_generation
    def index(video, create, extracted, **attrs):
        if extracted:
            video.update_search_index()

    @factory.post_generation
    def with_many_visibility_combinations(video, create, extracted, **kwargs):
        """Make languages with many different combinations of
        visibility/visibility_override_choices

        This method creates languages with all possible combinations with 0,
        1, and 2 versions and some combinations using more versions.

        This method will also set the tips/public_tips attributes on the
        video.  They will map language ids to the version number of the
        correct tip for each language.
        """
        if not extracted:
            return
        now = datetime.datetime.now()
        language_codes = iter(translation.ALL_LANGUAGE_CODES)
        visibility_choices = ['public', 'private']
        visibility_override_choices = ['', 'public', 'private', 'deleted']
        combo_choices = [
            (v, vo)
            for v in visibility_choices
            for vo in visibility_override_choices
        ]
        all_versions = []
        video.public_tips = {}
        video.tips = {}
        def make_language(visibility_list):
            language = SubtitleLanguageFactory(
                video=video, language_code=language_codes.next(),
            )
            public_tip = tip = None
            for i, visibilities in enumerate(visibility_list):
                version = subtitles.models.SubtitleVersion(
                    video=video, subtitle_language=language,
                    language_code=language.language_code,
                    created=now, visibility=visibilities[0],
                    visibility_override=visibilities[1],
                    version_number=i+1)
                if version.is_public():
                    public_tip = version.version_number
                if not version.is_deleted():
                    tip = version.version_number
                all_versions.append(version)
            video.tips[language.id] = tip
            video.public_tips[language.id] = public_tip

        # make all combinations of 0, 1, and 2 versions
        make_language([])
        for choice in combo_choices:
            make_language([choice])
            for choice2 in combo_choices:
                make_language([choice, choice2])
        # make a copule languages with many public/private versions
        make_language([('public', '') for i in range(4)])
        make_language([('private', '') for i in range(4)])
        # language that had private verisons, then the last was published
        make_language([
            ('private', ''), ('private', ''), ('private', 'public'),
        ])
        # language that had got published, then had a post-edit
        make_language([
            ('private', ''), ('private', ''), ('private', ''),
            ('private', 'public'), ('public', ''),
        ])
        # language that had public verisons, but they were deleted
        make_language([
            ('public', 'deleted'), ('public', 'deleted'),
            ('public', 'deleted'), ('public', 'deleted'),
        ])
        subtitles.models.SubtitleVersion.objects.bulk_create(all_versions)

    @classmethod
    def _after_postgeneration(cls, video, create, results=None):
        # Need to call update_team(), but we can't do it in our
        # post-generation method, since that might run before the video URLs
        # are created
        team = video.get_team()
        if team:
            video.update_team(team)

class KalturaVideoFactory(VideoFactory):
    FACTORY_HIDDEN_ARGS = ('name',)

    video_url__type = 'K'
    name = 'video'

    @factory.lazy_attribute
    def video_url__url(self):
        # generate a video with a kaltura-style URL
        entry_id = '1_' + hashlib.md5(self.name).hexdigest()[:8]
        return ('http://cdnbakmi.kaltura.com'
                '/p/1492321/sp/149232100/serveFlavor/entryId/'
                '%s/flavorId/1_dqgopb2z/name/%s.mp4') % (entry_id,
                                                         self.name)

class BrightcoveVideoFactory(VideoFactory):
    # generate a video with a brightcove-style URL
    FACTORY_HIDDEN_ARGS = ('brightcove_id', 'player_id')

    brightcove_id = 'abc'
    player_id = '1234'
    video_url__type = 'C'

    @factory.lazy_attribute
    def video_url__url(self):
        return 'http://bcove.me/services/link/bcpid%s/bctid%s' % (
            self.player_id, self.brightcove_id)

class YouTubeVideoFactory(VideoFactory):
    video_url__type = 'Y'
    video_url__videoid = factory.Sequence(lambda n: 'video{0}'.format(n))

    @factory.lazy_attribute
    def video_url__url(self):
        return ('https://www.youtube.com/watch?v=%s' %
                self.video_url__videoid)

    @classmethod
    def _generate(cls, create, attrs):
        """Override the default _generate() to handle the channel_id
        parameteter.
        """
        if 'channel_id' in attrs:
            attrs['video_url__owner_username'] = attrs.pop('channel_id')
        return super(YouTubeVideoFactory, cls)._generate(create, attrs)

class VideoFeedFactory(DjangoModelFactory):
    FACTORY_FOR = videos.models.VideoFeed

class UserFactory(DjangoModelFactory):
    FACTORY_FOR = auth.models.CustomUser

    username = factory.Sequence(lambda n: 'test_user_{0}'.format(n))
    email = factory.LazyAttribute(lambda u: '%s@example.com' % u.username)
    first_name = 'TestUser'
    last_name = factory.Sequence(lambda n: 'Number {0}'.format(n))
    notify_by_email = True
    valid_email = True
    password = 'password'
    show_tutorial = False

    @classmethod
    def _generate(cls, create, attrs):
        """Override the default _generate() to disable the post-save signal."""
        if 'password' in attrs:
            attrs['password'] = make_password(attrs['password'])
        return super(UserFactory, cls)._generate(create, attrs)

    @factory.post_generation
    def languages(self, create, extracted, **kwargs):
        if extracted:
            assert create
            for language_code in extracted:
                auth.models.UserLanguage.objects.create(
                    user=self, language=language_code)

    @factory.post_generation
    def team(self, create, extracted, **kwargs):
        if extracted:
            role = kwargs.get('role', teams.models.TeamMember.ROLE_ADMIN)
            TeamMemberFactory(user=self, team=extracted, role=role)

class TeamFactory(DjangoModelFactory):
    FACTORY_FOR = teams.models.Team

    name = factory.Sequence(lambda n: 'Team %s' % n)
    slug = factory.LazyAttribute(lambda t: slugify(t.name))
    membership_policy = teams.models.Team.INVITATION_BY_ADMIN
    workflow_type = 'O'

    @classmethod
    def _generate(cls, create, attrs):
        team = super(TeamFactory, cls)._generate(create, attrs)
        if create:
            # this forces the default project to be created
            team.default_project
        return team

    @factory.post_generation
    def owner(self, create, extracted, **kwargs):
        if extracted:
            assert create
            TeamMemberFactory.create(
                user=extracted, team=self,
                role=teams.models.TeamMember.ROLE_OWNER,
            )

    @factory.post_generation
    def admin(self, create, extracted, **kwargs):
        if extracted:
            assert create
            TeamMemberFactory.create(
                user=extracted, team=self,
                role=teams.models.TeamMember.ROLE_ADMIN,
            )

    @factory.post_generation
    def manager(self, create, extracted, **kwargs):
        if extracted:
            assert create
            TeamMemberFactory.create(
                user=extracted, team=self,
                role=teams.models.TeamMember.ROLE_MANAGER,
            )

    @factory.post_generation
    def member(self, create, extracted, **kwargs):
        if extracted:
            assert create
            TeamMemberFactory.create(
                user=extracted, team=self,
                role=teams.models.TeamMember.ROLE_CONTRIBUTOR,
            )

class WorkflowFactory(DjangoModelFactory):
    FACTORY_FOR = teams.models.Workflow
    review_allowed = 30 # admin must review
    approve_allowed = 20 # admin must approve

class TeamMemberFactory(DjangoModelFactory):
    FACTORY_FOR = teams.models.TeamMember

    role = teams.models.TeamMember.ROLE_OWNER
    user = factory.SubFactory(UserFactory)
    team = factory.SubFactory(TeamFactory)

class TeamContributorMemberFactory(DjangoModelFactory):
    FACTORY_FOR = teams.models.TeamMember

    role = teams.models.TeamMember.ROLE_CONTRIBUTOR
    user = factory.SubFactory(UserFactory)
    team = factory.SubFactory(TeamFactory)


class TeamVideoFactory(DjangoModelFactory):
    FACTORY_FOR = teams.models.TeamVideo

    team = factory.SubFactory(TeamFactory)
    video = factory.SubFactory(VideoFactory)

    @classmethod
    def _generate(cls, create, attrs):
        tv = super(TeamVideoFactory, cls)._generate(create, attrs)
        tv.video.user = tv.added_by
        tv.video.clear_team_video_cache()
        return tv

    @factory.lazy_attribute
    def added_by(tv):
        member = TeamMemberFactory.create(team=tv.team)
        return member.user

class ProjectFactory(DjangoModelFactory):
    FACTORY_FOR = teams.models.Project

    team = factory.SubFactory(TeamFactory)
    name = factory.Sequence(lambda n: 'Project %s' % n)


class TaskFactory(DjangoModelFactory):
    FACTORY_FOR = teams.models.Task
    type = teams.models.Task.TYPE_IDS['Subtitle']

    @classmethod
    def create_review(cls, team_video, language_code, subtitler, **kwargs):
        """Create a task, then move it to the review stage

        assumptions:
            - there are no Tasks or SubtitleVersions for this video+language
            - review is enabled for the team
        """
        try:
            sub_data = kwargs.pop('sub_data')
        except KeyError:
            sub_data = SubtitleSetFactory()
        if 'type' in kwargs and isinstance(kwargs['type'], basestring):
            kwargs['type'] = teams.models.Task.TYPE_IDS[kwargs['type']]
        team = team_video.team
        task = cls.create(team=team, team_video=team_video,
                          assignee=subtitler, language=language_code, **kwargs)
        pipeline.add_subtitles(team_video.video, language_code, sub_data,
                               author=subtitler, action='save-draft')
        return task.complete()

    @classmethod
    def create_approve(cls, team_video, language_code, reviewer,
                       subtitler=None, **kwargs):
        """Create a task, then move it to the approval stage

        assumptions:
            - there are no Tasks or SubtitleVersions for this video+language
            - approve is enabled for the team
        """
        if subtitler is None:
            subtitler = reviewer
        task = cls.create_review(team_video, language_code, subtitler, **kwargs)
        if task.type == teams.models.Task.TYPE_IDS['Approve']:
            # review isn't enabled, but approve is.  Just return the task
            # early
            return task

        task.assignee = reviewer
        task.approved = teams.models.Task.APPROVED_IDS['Approved']
        return task.complete()

class SubtitleLanguageFactory(DjangoModelFactory):
    FACTORY_FOR = subtitles.models.SubtitleLanguage

class OldSubtitleLanguageFactory(DjangoModelFactory):
    FACTORY_FOR = videos.models.SubtitleLanguage

    is_original = True
    language = 'en'
    created = datetime.datetime(2000, 1, 1)

class OldSubtitleVersionFactory(DjangoModelFactory):
    FACTORY_FOR = videos.models.SubtitleVersion

    title = 'Title'
    description = 'Description'
    datetime_started = datetime.datetime(2000, 1, 1)

class BrightcoveCMSAccountFactory(DjangoModelFactory):
    FACTORY_FOR = externalsites.models.BrightcoveCMSAccount

    publisher_id = 'publisher'
    client_id = 'client_id'
    client_secret = 'client_secret'

class KalturaAccountFactory(DjangoModelFactory):
    FACTORY_FOR = externalsites.models.KalturaAccount

    partner_id = 'test-partner-id'
    secret = 'test-secret'

class YouTubeAccountFactory(DjangoModelFactory):
    FACTORY_FOR = externalsites.models.YouTubeAccount

    username = factory.Sequence(lambda n: 'youtube-user-%s' % n)
    channel_id = factory.Sequence(lambda n: 'channel-id-%s' % n)
    oauth_refresh_token = 'refresh-token'

class VimeoSyncAccountFactory(DjangoModelFactory):
    FACTORY_FOR = externalsites.models.VimeoSyncAccount
    username = factory.Sequence(lambda n: 'vimeo-user-%s' % n)

class CommentFactory(DjangoModelFactory):
    FACTORY_FOR = comments.models.Comment
    user = factory.SubFactory(UserFactory)
    content = "test-content"
    submit_date = datetime.datetime(2000, 1, 1)

class YouTubeVideoInfoFactory(Factory):
    FACTORY_FOR = google.VideoInfo

    channel_id = 'test-channel-id'
    title = 'test title'
    description = 'test description'
    duration = 100
    thumbnail_url = 'http://example.com/thumbnail.png'

class SubtitleSetFactory(Factory):
    FACTORY_FOR = babelsubs.storage.SubtitleSet

    language_code = 'en'

    @factory.post_generation
    def num_subs(self, create, extracted, **kwargs):
        if extracted is None:
            extracted = 10
        for i in xrange(extracted):
            self.append_subtitle(i*1000, i*1000 + 999, "Sub %s" % i)

class UploadedFileFactory(SimpleUploadedFile):
    def __init__(self):
        p = os.path.join(settings.PROJECT_ROOT,
                         'media/images/video-no-thumbnail-wide.png')
        content = open(p).read()
        super(UploadedFileFactory, self).__init__('thumb.png', content)

def bulk_subs(sub_data):
    """Create a bunch of videos/languages/versions

    sub_data is a dict of dicts containing the data to create the objects
    with:

    * sub_data maps video titles to language data
    * language data map language codes to a list of version data
    * version data is a dict containing kwargs to pass to
    pipeline.create_subtitles().

    returns a tuple of dicts:
    * a dict that maps video titles to videos
    * a dict that maps (title, language_code) to languages
    * a dict that maps (title, language_code, version_number) to versions
    """
    videos = {}
    langs = {}
    versions = {}
    for video_title, language_data in sub_data.items():
        video = VideoFactory(title=video_title)
        videos[video_title] = video
        for language_code, version_data in language_data.items():
            lang = SubtitleLanguageFactory(video=video,
                                           language_code=language_code)
            langs[video_title, language_code] = lang
            for kwargs in version_data:
                v = pipeline.add_subtitles(video, language_code, None,
                                           **kwargs)
                versions[video_title, language_code, v.version_number] = v
    return videos, langs, versions

def make_version(video, language_code, subtitle_set=None,
                 subtitles_complete=True,
                 **kwargs):
    """Make a version without going through the workflow logic."""
    language, _ = subtitles.models.SubtitleLanguage.objects.get_or_create(
        video=video, language_code=language_code)
    if subtitles_complete != language.subtitles_complete:
        language.subtitles_complete = subtitles_complete
        language.save()
    if subtitle_set is None:
        subtitle_set = SubtitleSetFactory()
    return language.add_version(subtitles=subtitle_set, **kwargs)

__all__ = ['bulk_subs', 'make_version']
__all__.extend(name for name in globals() if 'Factory' in name)
