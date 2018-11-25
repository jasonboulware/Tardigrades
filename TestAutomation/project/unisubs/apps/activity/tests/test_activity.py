# Amara, universalsubtitles.org
#
# Copyright (C) 2016 Participatory Culture Foundation
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

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from activity.models import ActivityRecord
from comments.models import Comment
from subtitles import pipeline
from teams.models import TeamVisibility, VideoVisibility
from teams.permissions_const import *
from utils import dates
from utils.factories import *
from utils.test_utils import *
import teams.signals
import videos.signals

def clear_activity():
    ActivityRecord.objects.all().delete()

class ActivityCreationTest(TestCase):
    def check_save_doesnt_create_new_record(self, instance):
        pre_count = ActivityRecord.objects.count()
        instance.save()
        assert_equal(ActivityRecord.objects.count(), pre_count)

    def test_video_added(self):
        video = VideoFactory()
        clear_activity()
        videos.signals.video_added.send(
            sender=video,
            video_url=video.get_primary_videourl_obj())
        record = ActivityRecord.objects.get(type='video-added')
        assert_equals(record.video, video)
        assert_equals(record.user, video.user)
        assert_equals(record.created, video.created)

    def test_comment_added(self):
        video = VideoFactory()
        user = UserFactory()
        comment = Comment.objects.create(content_object=video, user=user,
                                         content='Foo')
        record = ActivityRecord.objects.get(type='comment-added')
        assert_equals(record.video, video)
        assert_equals(record.user, user)
        assert_equals(record.created, comment.submit_date)
        assert_equals(record.get_related_obj(), comment)
        assert_equals(record.language_code, '')

    def test_comment_added_to_subtitles(self):
        version = pipeline.add_subtitles(VideoFactory(), 'en',
                                         SubtitleSetFactory())
        language = version.subtitle_language
        user = UserFactory()
        comment = Comment.objects.create(content_object=language, user=user,
                                         content='Foo')
        record = ActivityRecord.objects.get(type='comment-added')
        assert_equals(record.video, language.video)
        assert_equals(record.user, user)
        assert_equals(record.created, comment.submit_date)
        assert_equals(record.get_related_obj(), comment)
        assert_equals(record.language_code, 'en')

    def test_version_added(self):
        version = pipeline.add_subtitles(VideoFactory(), 'en',
                                         SubtitleSetFactory())
        record = ActivityRecord.objects.get(type='version-added')
        assert_equal(record.user, version.author)
        assert_equal(record.video, version.video)
        assert_equal(record.language_code, version.language_code)
        assert_equal(record.created, version.created)
        self.check_save_doesnt_create_new_record(version)

    def test_video_url_added(self):
        video = VideoFactory()
        video_url = VideoURLFactory(video=video)
        clear_activity()
        videos.signals.video_url_added.send(sender=video_url, video=video,
                                            new_video=False)
        record = ActivityRecord.objects.get(type='video-url-added')
        assert_equal(record.user, video_url.added_by)
        assert_equal(record.video, video)
        assert_equal(record.language_code, '')
        assert_equal(record.created, video_url.created)
        # We don't currently use it, but we store the new URL in the related
        # object
        url_edit = record.get_related_obj()
        assert_equal(url_edit.new_url, video_url.url)

    def test_video_url_added_with_new_video(self):
        # In this case, we shouldn't create an video-url-added record, since
        # we already created the video-added record
        video = VideoFactory()
        video_url = VideoURLFactory(video=video)
        clear_activity()
        videos.signals.video_url_added.send(sender=video_url, video=video,
                                            new_video=True)
        assert_false(
            ActivityRecord.objects.filter(type='video-url-added').exists())

    def test_video_title_edited(self):
        video = VideoFactory()
        user = UserFactory()
        clear_activity()
        video.title = 'new_title'
        video.save()
        videos.signals.video_title_edited.send(sender=video, user=user, old_title='old_title')
        record = ActivityRecord.objects.get(type='video-title-changed')
        assert_equal(record.user, user)
        assert_equal(record.video, video)
        assert_equal(record.language_code, '')
        assert_equal(record.created, dates.now.last_returned)

    def test_member_joined(self):
        member = TeamMemberFactory(role=ROLE_MANAGER)
        record = ActivityRecord.objects.get(type='member-joined')
        assert_equal(record.user, member.user)
        assert_equal(record.video, None)
        assert_equal(record.team, member.team)
        assert_equal(record.language_code, '')
        assert_equal(record.created, member.created)
        assert_equal(record.get_related_obj(), ROLE_MANAGER)
        # After deleting the team member, get_related_obj() should still work
        member.delete()
        assert_equal(reload_obj(record).get_related_obj(), ROLE_MANAGER)

    def test_member_left(self):
        member = TeamMemberFactory()
        now = dates.now.current
        teams.signals.member_leave.send(sender=member)
        record = ActivityRecord.objects.get(type='member-left')
        assert_equal(record.user, member.user)
        assert_equal(record.video, None)
        assert_equal(record.team, member.team)
        assert_equal(record.language_code, '')
        assert_equal(record.created, now)

    def test_video_deleted(self):
        title = 'test-title'
        url = 'http://example.com/test.mp4'
        video = VideoFactory(title=title, video_url__url=url)
        user = UserFactory()
        now = dates.now.current
        videos.signals.video_deleted.send(sender=video, user=user)
        record = ActivityRecord.objects.get(type='video-deleted')
        assert_equal(record.user, user)
        # video should be none since the video is going to be deleted, so
        # having a foreign key pointing to it is no good
        assert_equal(record.video, None)
        assert_equal(record.language_code, '')
        assert_equal(record.created, now)
        video_deletion = record.get_related_obj()
        assert_equal(video_deletion.title, title)
        assert_equal(video_deletion.url, url)

    def test_make_url_primary(self):
        url1 = 'http://example.com/test1.mp4'
        url2 = 'http://example.com/test2.mp4'
        video = VideoFactory(video_url__url=url1)
        video_url = video.get_primary_videourl_obj()
        video_url2 = VideoURLFactory(video=video, url=url2)
        user = UserFactory()
        now = dates.now.current
        videos.signals.video_url_made_primary.send(
            sender=video_url2, old_url=video_url, user=user)
        record = ActivityRecord.objects.get(type='video-url-edited')
        assert_equal(record.user, user)
        assert_equal(record.video, video)
        assert_equal(record.language_code, '')
        assert_equal(record.created, now)
        url_edit = record.get_related_obj()
        assert_equal(url_edit.old_url, url1)
        assert_equal(url_edit.new_url, url2)

    def test_make_url_delete(self):
        url1 = 'http://example.com/test1.mp4'
        url2 = 'http://example.com/test2.mp4'
        video = VideoFactory(video_url__url=url1)
        video_url = video.get_primary_videourl_obj()
        video_url2 = VideoURLFactory(video=video, url=url2)
        user = UserFactory()
        now = dates.now.current
        videos.signals.video_url_deleted.send(sender=video_url2, user=user)
        record = ActivityRecord.objects.get(type='video-url-deleted')
        assert_equal(record.user, user)
        assert_equal(record.video, video)
        assert_equal(record.language_code, '')
        assert_equal(record.created, now)
        url_edit = record.get_related_obj()
        assert_equal(url_edit.old_url, url2)
        assert_equal(url_edit.new_url, '')

class ActivityVideoLanguageTest(TestCase):
    def test_initial_video_language(self):
        video = VideoFactory(primary_audio_language_code='en')
        record = ActivityRecord.objects.create_for_video_added(video)
        assert_equal(record.video_language_code, 'en')

    def test_video_language_changed(self):
        video = VideoFactory(primary_audio_language_code='en')
        record = ActivityRecord.objects.create_for_video_added(video)
        video.primary_audio_language_code = 'fr'
        videos.signals.language_changed.send(
            sender=video, old_primary_audio_language_code='en')
        assert_equal(reload_obj(record).video_language_code, 'fr')

class TeamVideoActivityTest(TestCase):
    # These tests test video activity and teams.  Our general system for
    # handling this is:
    #  - When a video moves to a team, we make a copy of it for the team it
    #  left.
    #  - We set the team field on the original record to the new team
    #  - The copy on the old team the copied_from field set
    def check_copies(self, record, current_team, old_teams):
        assert_equal(reload_obj(record).team, current_team)
        qs = ActivityRecord.objects.filter(copied_from=record)
        assert_items_equal([a.team for a in qs], old_teams)
        for copied in qs:
            assert_equal(copied.created, record.created)

    def test_team_video_activity(self):
        # Test activity on a team video
        team = TeamFactory()
        video = TeamVideoFactory(team=team).video
        clear_activity()
        record = ActivityRecord.objects.create_for_video_added(video)
        self.check_copies(record, team, [])

    def test_add_to_team(self):
        # Test adding a non-team video to a team
        video = VideoFactory()
        clear_activity()
        record = ActivityRecord.objects.create_for_video_added(video)
        team = TeamFactory()
        TeamVideoFactory(team=team, video=video)
        self.check_copies(record, team, [])

    def test_move_to_team(self):
        # same thing if we move from 1 team to another
        video = VideoFactory()
        team_video = TeamVideoFactory(video=video)
        first_team = team_video.team
        clear_activity()
        record = ActivityRecord.objects.create_for_video_added(video)
        second_team = TeamFactory()
        team_video.move_to(second_team)
        self.check_copies(record, second_team, [first_team])

    def test_move_back(self):
        # Test moving a video back to a team it was already in before
        video = VideoFactory()
        team_video = TeamVideoFactory(video=video)
        first_team = team_video.team
        clear_activity()
        record = ActivityRecord.objects.create_for_video_added(video)
        second_team = TeamFactory()
        team_video.move_to(second_team)
        team_video.move_to(first_team)
        self.check_copies(record, first_team, [second_team])

    def test_move_back_to_public(self):
        # Test a team video being deleted, putting the video back in the
        # public area
        video = VideoFactory()
        team_video = TeamVideoFactory(video=video)
        first_team = team_video.team
        clear_activity()
        record = ActivityRecord.objects.create_for_video_added(video)
        team_video.remove(UserFactory())
        self.check_copies(record, None, [first_team])

    def test_private_to_team_disables_copies(self):
        video = VideoFactory()
        team_video = TeamVideoFactory(video=video)
        clear_activity()
        record = ActivityRecord.objects.create_for_video_added(video)
        record.private_to_team = True
        record.save()
        team_video.move_to(TeamFactory())
        assert_false(
            ActivityRecord.objects.filter(copied_from=record).exists()
        )

    def test_private_to_team_with_for_video(self):
        # If private_to_team is True, we should not make any copies
        video = VideoFactory()
        team = TeamFactory()
        team_video = TeamVideoFactory(video=video, team=team)
        clear_activity()
        record = ActivityRecord.objects.create_for_video_added(video)
        record.private_to_team = True
        record.save()
        # By default, we don't include records with private_to_team set.
        assert_equal(list(ActivityRecord.objects.for_video(video)), [])
        # If we pass in the team parameter, we do though
        assert_equal(list(ActivityRecord.objects.for_video(video, team)),
                     [record])
        # Check passing in a different team parameter
        different_team = TeamFactory()
        assert_equal(
            list(ActivityRecord.objects.for_video(video, different_team)),
            [])

    def test_video_moved_from_team_to_public(self):
        video = VideoFactory()
        team = TeamFactory()
        team_video = TeamVideoFactory(video=video, team=team)
        clear_activity()
        team_video.remove(None)
        records_to = ActivityRecord.objects.filter(type='video-moved-to-team')
        assert_equal(len(list(records_to)), 0)
        record_from = ActivityRecord.objects.get(type='video-moved-from-team')
        assert_equal(record_from.video, video)
        assert_equal(record_from.team, team)
        assert_equal(record_from.get_related_obj(), None)

    def test_video_moved_from_public_to_team(self):
        video = VideoFactory()
        team = TeamFactory()
        clear_activity()
        team_video = TeamVideoFactory(video=video, team=team)
        records_from = ActivityRecord.objects.filter(type='video-moved-from-team')
        assert_equal(len(list(records_from)), 0)
        record_to = ActivityRecord.objects.get(type='video-moved-to-team')
        assert_equal(record_to.video, video)
        assert_equal(record_to.team, team)
        assert_equal(record_to.get_related_obj(), None)

    def test_video_moved_from_team_to_team(self):
        video = VideoFactory()
        team_1 = TeamFactory()
        team_2 = TeamFactory()
        team_video = TeamVideoFactory(video=video, team=team_1)
        clear_activity()
        team_video.move_to(team_2)
        record_from = ActivityRecord.objects.get(type='video-moved-from-team')
        assert_equal(record_from.video, video)
        assert_equal(record_from.team, team_1)
        assert_equal(record_from.get_related_obj(), team_2)
        record_to = ActivityRecord.objects.get(type='video-moved-to-team')
        assert_equal(record_to.video, video)
        assert_equal(record_to.team, team_2)
        assert_equal(record_to.get_related_obj(), team_1)

    def test_team_settings_changed(self):
        user = UserFactory()
        team = TeamFactory(admin=user)
        teams.signals.team_settings_changed.send(
            sender=team, user=user, changed_settings={
                'setting': 'new-value',
            }, old_settings={
                'setting': 'old-value',
            })
        record = ActivityRecord.objects.get(type='team-settings-changed')
        assert_equal(record.user, user)
        assert_equal(record.get_related_obj().get_changes(),
                     {'setting': 'new-value'})

class TestViewableByUser(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.video = VideoFactory()
        self.public_team_video = VideoFactory(
            team=TeamFactory(team_visibility=TeamVisibility.PUBLIC))
        self.private_team_video = VideoFactory(
            team=TeamFactory(team_visibility=TeamVisibility.PRIVATE))
        self.my_team_video = VideoFactory(
            team=TeamFactory(member=self.user,
                             team_visibility=TeamVisibility.PRIVATE))
        self.team_video = VideoFactory()
        ActivityRecord.objects.create_for_video_added(self.video)
        ActivityRecord.objects.create_for_video_added(self.public_team_video)
        ActivityRecord.objects.create_for_video_added(self.private_team_video)
        ActivityRecord.objects.create_for_video_added(self.my_team_video)

    def check_viewable_by_user(self, videos):
        qs = (ActivityRecord.objects
              .filter(type='video-added').viewable_by_user(self.user))
        assert_items_equal([a.video for a in qs], videos)

    def test_viewable_by_user(self):
        self.check_viewable_by_user([
            self.video,
            self.public_team_video,
            self.my_team_video,
        ])

    def test_superusers_see_all(self):
        self.user.is_superuser = True
        self.check_viewable_by_user([
            self.video,
            self.public_team_video,
            self.private_team_video,
            self.my_team_video,
        ])

    def test_anonymous_user(self):
        self.user = AnonymousUser()
        self.check_viewable_by_user([
            self.video,
            self.public_team_video,
        ])
