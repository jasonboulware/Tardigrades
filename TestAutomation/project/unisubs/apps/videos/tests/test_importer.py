# -*- coding: utf-8 -*-
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

import datetime

from django.test import TestCase
from nose.tools import *
import mock

from utils import test_utils
from utils.factories import *
from videos import signals
from videos.models import Video, VideoUrl, VideoFeed, ImportedVideo
from videos.feed_parser import importer
from videos.types import HtmlFiveVideoType

class VideoImporterTestCase(TestCase):
    @test_utils.patch_for_test('videos.feed_parser.importer.FeedParser')
    def setUp(self, mock_feedparser_class):
        TestCase.setUp(self)
        self.user = UserFactory()
        self.base_url = 'http://example.com/'
        self.mock_feedparser_class = mock_feedparser_class

    def feed_url(self):
        return self.url('feed.rss')

    def url(self, name):
        return self.base_url + name

    def entry(self, name):
        return {
            'link': self.url(name),
        }

    def video_type(self, name):
        return HtmlFiveVideoType(self.url(name))

    def setup_feed_items(self, item_info, links=None):
        """Setup the return vaule for FeedParser.

        :param item_info: list of (name, extra_info dict) tuples to
        return.
        """
        self.feed_parser = mock.Mock()
        self.feed_parser.feed.entries = [self.entry(name)
                                    for (name, extra) in item_info]
        self.feed_parser.feed.feed = {}
        self.feed_parser.items.return_value = [
            (self.video_type(name), info, self.entry(name))
            for (name, info) in item_info
        ]
        if links is not None:
            self.feed_parser.feed.feed = {
                'links': links
            }
        self.mock_feedparser_class.return_value = self.feed_parser

    def run_import_videos(self, import_next=False, team=None):
        import_obj = importer.VideoImporter(self.feed_url(), self.user, team)
        self.import_videos_rv = import_obj.import_videos(import_next)

    def check_videos(self, *feed_item_names):
        all_videos = list(Video.objects.all())
        self.assertEquals(len(all_videos), len(feed_item_names))
        self.assertEquals(set(v.get_video_url() for v in all_videos),
                          set(self.url(name) for name in feed_item_names))
        self.assertEquals(len(self.import_videos_rv), len(feed_item_names))
        self.assertEquals(set(v.id for v in self.import_videos_rv),
                          set(v.id for v in all_videos))

    def test_import(self):
        # test a simple import
        self.setup_feed_items([
            ('item-1', {}),
            ('item-2', {}),
            ('item-3', {}),
        ])
        self.run_import_videos()
        self.feed_parser.items.assert_called_with(
            ignore_error=True,
        )
        self.check_videos('item-1', 'item-2', 'item-3')

    def test_import_extra_values(self):
        # test feedparser returning extra values to set on our items.
        self.setup_feed_items([
            ('item-1', {'title': 'foo'}),
            ('item-2', {'title': 'bar'}),
            ('item-3', {}),
        ])
        self.run_import_videos()
        self.check_videos('item-1', 'item-2', 'item-3')
        video1 = VideoUrl.objects.get(url=self.url('item-1')).video
        video2 = VideoUrl.objects.get(url=self.url('item-2')).video
        self.assertEquals(video1.title, 'foo')
        self.assertEquals(video2.title, 'bar')

    def test_import_with_team(self):
        # test a simple import
        self.setup_feed_items([
            ('item-1', {}),
            ('item-2', {}),
            ('item-3', {}),
        ])
        team = TeamFactory()
        self.run_import_videos(team=team)
        for v in self.import_videos_rv:
            assert_not_equal(v.get_team_video(), None)
            assert_equal(v.get_team_video().team, team)

    def test_import_new_items(self):
        # Test that we import videos when some already have been created

        # try updating a feed when 1 video is already in the DB
        VideoFactory(video_url__url=self.url('item-1'))
        self.setup_feed_items([
            ('item-1', {}),
            ('item-2', {}),
            ('item-3', {}),
        ])
        self.run_import_videos()
        # all 3 videos should now be created
        self.assertEquals(Video.objects.count(), 3)
        # import_videos should only return the 2 new videos
        self.assertEquals(self.import_videos_rv, [
            VideoUrl.objects.get(url=self.url('item-2')).video,
            VideoUrl.objects.get(url=self.url('item-3')).video,
        ])
        # check running import videos again, with a mix of old and new items
        self.setup_feed_items([
            ('item-0', {}), # new
            ('item-1', {}), # old
            ('item-2', {}), # old
            ('item-4', {}), # new
        ])
        self.run_import_videos()
        # all 4 videos should be created
        self.assertEquals(Video.objects.count(), 5)
        # import_videos should only return the 2 new videos
        self.assertEquals(self.import_videos_rv, [
            VideoUrl.objects.get(url=self.url('item-0')).video,
            VideoUrl.objects.get(url=self.url('item-4')).video,
        ])

    def test_import_extra_links_from_youtube(self):
        # test importing extra items from youtube.
        #
        # For youtube, we import extra videos based on the links for the feed.
        # The way it works is that each time we parse a feed, we look for a
        # link with rel=next.  If the link is present, then we parse that link
        # and check again for a link with rel=next.
        self.base_url = 'http://youtube.com/'
        links = [
            [
                { 'href': self.url('feed.rss?p=1'), 'rel': 'next', },
                { 'href': self.url('other-thing.html')},
            ],
            [
                { 'href': self.url('feed.rss?p=2'), 'rel': 'next', },
                { 'href': self.url('license.html'), 'rel': 'license'},
            ],
            [
                { 'href': self.url('license.html'), 'rel': 'license'},
            ],
        ]
        links_iter = iter(links)
        urls_parsed = []
        def make_feed_parser(url):
            urls_parsed.append(url)
            self.setup_feed_items([], links_iter.next())
            return self.feed_parser
        self.mock_feedparser_class.side_effect = make_feed_parser

        self.run_import_videos(import_next=True)
        self.assertEquals(urls_parsed, [
            self.feed_url(),
            self.url('feed.rss?p=1'),
            self.url('feed.rss?p=2'),
        ])
        # if import_next is false, we should skip the logic
        urls_parsed = []
        links_iter = iter(links)
        self.run_import_videos(import_next=False)
        self.assertEquals(urls_parsed, [self.feed_url()])

class VideoFeedTest(TestCase):
    @test_utils.patch_for_test('videos.models.VideoImporter')
    def setUp(self, MockVideoImporter):
        self.MockVideoImporter = MockVideoImporter
        self.mock_video_importer = mock.Mock()
        self.mock_video_importer.last_link = None
        MockVideoImporter.return_value = self.mock_video_importer

    def test_video_feed(self):
        mock_feed_imported_handler = mock.Mock()
        signals.feed_imported.connect(mock_feed_imported_handler, weak=False)
        self.addCleanup(signals.feed_imported.disconnect,
                        mock_feed_imported_handler)
        user = UserFactory()

        url = 'http://example.com/feed.rss'
        feed = VideoFeed.objects.create(url=url, user=user)

        feed_videos = list(VideoFactory() for i in xrange(3))

        self.mock_video_importer.import_videos.return_value = feed_videos
        rv = feed.update()
        self.MockVideoImporter.assert_called_with(url, user, None)
        self.mock_video_importer.import_videos.assert_called_with(import_next=True)
        self.assertEquals(rv, feed_videos)
        mock_feed_imported_handler.assert_called_with(
            signal=signals.feed_imported, sender=feed, new_videos=feed_videos)
        # check doing another update, this time we should pass
        # import_next=False
        self.mock_video_importer.import_videos.return_value = []
        rv = feed.update()
        self.MockVideoImporter.assert_called_with(url, user, None)
        self.mock_video_importer.import_videos.assert_called_with(import_next=False)
        self.assertEquals(rv, [])
        mock_feed_imported_handler.assert_called_with(
            signal=signals.feed_imported, sender=feed, new_videos=[])

    def make_video(self, number):
        video_url = 'http://example.com/video-{0}.mp4'.format(number)
        return VideoFactory.create(video_url__url=video_url)

    @test_utils.patch_for_test('videos.models.VideoFeed.now')
    def test_update_logging(self, mock_now):
        feed = VideoFeed.objects.create(url='http://example.com/feed.rss')
        # run update().  Check that we update last_imported and that
        # ImportedVideo objects get created.  ImportedVideo objects should be
        # ordered last to first
        now = datetime.datetime(2000, 1, 1)
        mock_now.return_value = now
        videos = [VideoFactory() for i in xrange(5)]
        self.mock_video_importer.import_videos.return_value = videos
        feed.update()
        self.assertEquals(feed.last_update, now)
        self.assertEquals([iv.video for iv in feed.importedvideo_set.all()],
                          videos)
        # run VideoFeed.update() again.  new videos should be added at the
        # start of the list
        videos2 = [VideoFactory() for i in xrange(5)]
        self.mock_video_importer.import_videos.return_value = videos2
        now += datetime.timedelta(days=1)
        mock_now.return_value = now
        feed.update()
        self.assertEquals(feed.last_update, now)
        self.assertEquals([iv.video for iv in feed.importedvideo_set.all()],
                          videos2 + videos)
        # run VideoFeed.update() one more time, with no new videos.
        # last_update should still be upated
        # start of the list
        self.mock_video_importer.import_videos.return_value = []
        now += datetime.timedelta(days=1)
        mock_now.return_value = now
        feed.update()
        self.assertEquals(feed.last_update, now)
        self.assertEquals([iv.video for iv in feed.importedvideo_set.all()],
                          videos2 + videos)
