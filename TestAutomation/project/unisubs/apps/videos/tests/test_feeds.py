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

import feedparser
from StringIO import StringIO

from django.urls import reverse
from django.test import TestCase
import mock

from utils import test_utils
from utils.factories import *
from videos.feed_parser import FeedParser
from videos.models import Video, VideoFeed
from videos.types.vimeo import VimeoVideoType
from videos.types.dailymotion import DailymotionVideoType
from videos.types.youtube import YoutubeVideoType

class FeedImportTest(TestCase):
    def setUp(self):
        self.open_resource_mock = mock.Mock()
        self.set_feed_data(EXAMPLE_FEED_XML)
        self.open_resource_patcher = mock.patch(
            'feedparser._open_resource',
            self.open_resource_mock)
        self.open_resource_patcher.start()

    def tearDown(self):
        self.open_resource_patcher.stop()
        TestCase.tearDown(self)

    def set_feed_data(self, feed_data):
        self.open_resource_mock.side_effect = \
                lambda *args: StringIO(feed_data)

    def opened_url(self):
        return self.open_resource_mock.call_args[0][0]

class TestFeedParser(FeedImportTest):
    # TODO: add test for MediaFeedEntryParser. I just can't find RSS link for it
    # RSS should look like this http://www.dailymotion.com/rss/ru/featured/channel/tech/1
    # but not from supported site

    def check_video_types(self, feed_url, correct_video_type_class):
        feed_parser = FeedParser(feed_url)
        for vt, info, entry in feed_parser.items():
            self.assertEquals(vt.abbreviation,
                              correct_video_type_class.abbreviation)

    def test_vimeo_feed_parsing(self):
        self.set_feed_data(VIMEO_FEED_XML)
        self.check_video_types('http://vimeo.com/blakewhitman/videos/rss',
                               VimeoVideoType)

    def test_youtube_feed_parsing(self):
        self.set_feed_data(YOUTUBE_USER_FEED_XML)
        feed_url = ('https://gdata.youtube.com'
                    '/feeds/api/users/amaratestuser/uploads')
        self.check_video_types(feed_url, YoutubeVideoType)

    def test_dailymotion_feed_parsing(self):
        self.set_feed_data(DAILY_MOTION_XML)
        feed_url = 'http://www.dailymotion.com/rss/ru/featured/channel/tech/1'
        self.check_video_types(feed_url, DailymotionVideoType)

class EntryDataTest(FeedImportTest):
    def setUp(self):
        FeedImportTest.setUp(self)
        self.feed = VideoFeed.objects.create(url="http://example.com/feed")

    def test_rss_attributes(self):
        self.set_feed_data("""\
<?xml version="1.0" encoding="ISO-8859-1" ?>
<rss version="2.0">
<channel>
  <title>Test Feed</title>
  <link>http://example.com/feed</link>
  <description>Test Feed</description>
  <item>
    <title>Feed Title</title>
    <description>Feed Description</description>
    <link>http://www.youtube.com/watch?v=e4MSN6IImpI</link>
  </item>
</channel>
</rss>""")
        self.feed.update()
        video = Video.objects.get()
        self.assertEquals(video.title, 'Feed Title')
        self.assertEquals(video.description, 'Feed Description')

    def test_media_enclosure(self):
        self.set_feed_data("""\
<?xml version="1.0" encoding="ISO-8859-1" ?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss">
<channel>
  <title>Test Feed</title>
  <link>http://example.com/feed</link>
  <description>Test Feed</description>
  <item>
    <link>http://www.youtube.com/watch?v=e4MSN6IImpI</link>
    <media:content url="http://www.youtube.com/watch?v=e4MSN6IImpI">
        <media:title>Media Enclosure Title</media:title>
        <media:description>Media Enclosure Description</media:description>
        <media:thumbnail url="http://example.com/media-enclosure-thumb.jpg" />
    </media:content>
  </item>
</channel>
</rss>""")
        self.feed.update()
        video = Video.objects.get()
        self.assertEquals(video.title, 'Media Enclosure Title')
        self.assertEquals(video.description, 'Media Enclosure Description')
        self.assertEquals(video.thumbnail,
                          'http://example.com/media-enclosure-thumb.jpg')

    def test_itunes_attributes(self):
        self.set_feed_data("""\
<?xml version="1.0" encoding="ISO-8859-1" ?>
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:itunesu="http://www.itunesu.com/feed" version="2.0" >
<channel>
  <title>Test Feed</title>
  <link>http://example.com/feed</link>
  <description>Test Feed</description>
  <item>
    <title>Entry Title</title>
    <link>http://qa.pculture.org/amara_tests/1_q5cygpn1</link>
    <enclosure url="http://cdnbakmi.kaltura.com/p/1492321/sp/149232100/serveFlavor/entryId/1_q5cygpn1/flavorId/1_u65nz1sh/name/a.mp4" type="video/mp4"></enclosure>
    <itunes:author>dean@pculture.org</itunes:author>
    <itunes:summary>Itunes Description</itunes:summary>
    <itunes:image href="http://example.com/itunes-thumb.jpg"></itunes:image>
  </item>
</channel>
</rss>""")
        self.feed.update()
        video = Video.objects.get()
        self.assertEquals(video.title, 'Entry Title')
        self.assertEquals(video.description, 'Itunes Description')
        self.assertEquals(video.thumbnail,
                          'http://example.com/itunes-thumb.jpg')


# feed data for the tests
EXAMPLE_FEED_XML = """\
<?xml version="1.0" encoding="ISO-8859-1" ?>
<rss version="2.0">

<channel>
  <title>Feed Title</title>
  <description>Feed Description</description>
  <link>http://example.com/</link>
  <item>
    <title>Item 1</title>
    <link href="http://example.com/video1.mp4" rel="alternate" type="text/html"/>
    <description>Great Video</description>
  </item>
  <item>
    <title>Item 2</title>
    <link href="http://example.com/video2.mp4" rel="alternate" type="text/html"/>
    <description>Great Video</description>
  </item>
</channel>
</rss>"""

EMPTY_FEED_XML = """\
<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom' xmlns:openSearch='http://a9.com/-/spec/opensearchrss/1.0/'>
    <id>http://gdata.youtube.com/feeds/api/users/test/uploads</id>
    <updated>2011-07-05T09:17:40.888Z</updated>
    <category scheme='http://schemas.google.com/g/2005#kind' term='http://gdata.youtube.com/schemas/2007#video'/>
    <title type='text'>Uploads by test</title>
    <logo>http://www.youtube.com/img/pic_youtubelogo_123x63.gif</logo>
    <link rel='related' type='application/atom+xml' href='https://gdata.youtube.com/feeds/api/users/test'/>
    <link rel='alternate' type='text/html' href='https://www.youtube.com/profile_videos?user=test'/>
    <link rel='http://schemas.google.com/g/2005#feed' type='application/atom+xml' href='https://gdata.youtube.com/feeds/api/users/test/uploads'/>
    <link rel='http://schemas.google.com/g/2005#batch' type='application/atom+xml' href='https://gdata.youtube.com/feeds/api/users/test/uploads/batch'/>
    <link rel='self' type='application/atom+xml' href='https://gdata.youtube.com/feeds/api/users/test/uploads?start-index=1&amp;max-results=25'/>
    <author><name>test</name><uri>https://gdata.youtube.com/feeds/api/users/test</uri></author>
    <generator version='2.0' uri='http://gdata.youtube.com/'>YouTube data API</generator>
    <openSearch:totalResults>0</openSearch:totalResults><openSearch:startIndex>1</openSearch:startIndex>
    <openSearch:itemsPerPage>25</openSearch:itemsPerPage>
</feed>"""

DAILY_MOTION_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:media="http://search.yahoo.com/mrss" xmlns:dm="http://www.dailymotion.com/dmrss">
   <channel>
   <title>Dailymotion - Geek Out</title>
   <link>http://www.dailymotion.com/ru/featured/channel/tech/1</link>
   <description><![CDATA[Geek Out]]></description>
    <itunes:subtitle>Dailymotion - Geek Out</itunes:subtitle>
    <itunes:summary>Geek Out</itunes:summary>
   <itunes:owner>
      <itunes:name>Dailymotion</itunes:name>
      <itunes:email>rss@dailymotion.com</itunes:email>
   </itunes:owner>
   <itunes:author>Dailymotion</itunes:author>
   <itunes:image href="http://www.dailymotion.com/images/dailymotion_itunes.jpg"/>
   <itunes:explicit>no</itunes:explicit>
   <itunes:category text="TV &amp; Film" />
   <language>en-US</language>
   <lastBuildDate>Wed, 07 Aug 2013 18:41:35 +0200</lastBuildDate>
      <image>
          <url>http://www.dailymotion.com/images/dailymotion.jpg</url>
          <title>Dailymotion - Geek Out</title>
          <link>http://www.dailymotion.com/ru/featured/channel/tech/1</link>
          <width>400</width>
          <height>144</height>
      </image>
        <dm:link rel="uql" href="http://www.dailymotion.com/rss/ru/featured/channel/tech/1" type="application/rss+xml"/>
        <dm:link rel="sort_by_all" title="All videos" href="http://www.dailymotion.com/rss/ru/channel/tech/1" type="application/rss+xml"/>
        <dm:link rel="sort_by_buzz" title="Hot Right Now" href="http://www.dailymotion.com/rss/ru/buzz/channel/tech/1" type="application/rss+xml"/>
        <dm:link rel="sort_by_hd" title="HD content" href="http://www.dailymotion.com/rss/hd/channel/tech/1" type="application/rss+xml"/>
        <dm:link rel="sort_by_official" title="Official Content" href="http://www.dailymotion.com/rss/ru/official/channel/tech/1" type="application/rss+xml"/>
        <dm:link rel="sort_by_creative" title="Motionmaker content" href="http://www.dailymotion.com/rss/ru/creative/channel/tech/1" type="application/rss+xml"/>
        <dm:link rel="sort_by_visited-week" title="Most Viewed" href="http://www.dailymotion.com/rss/ru/visited-week/featured/channel/tech/1" type="application/rss+xml"/>
        <dm:link rel="sort_by_rated-week" title="Best Rated" href="http://www.dailymotion.com/rss/ru/rated-week/featured/channel/tech/1" type="application/rss+xml"/>
        <dm:link rel="up" href="http://www.dailymotion.com/rss/channels" type="application/rss+xml"/>
        <dm:link rel="next" href="http://www.dailymotion.com/rss/ru/featured/channel/tech/2" type="application/rss+xml"/>
        <dm:link rel="nextUql" href="http://www.dailymotion.com/rss/ru/featured/channel/tech/2" type="application/rss+xml"/>
        <item>
            <title>ÐÐ½ÑÐµÑÐ²ÑÑ Ñ Ð³ÐµÐ½Ð´Ð¸ÑÐ¾Ð¼ Nokia Ð Ð¾ÑÑÐ¸Ñ</title>
            <link>http://www.dailymotion.com/video/x9y40a_%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D0%B2%D1%8C%D1%8E-%D1%81-%D0%B3%D0%B5%D0%BD%D0%B4%D0%B8%D1%80%D0%BE%D0%BC-nokia-%D1%80%D0%BE%D1%81%D1%81%D0%B8%D1%8F_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x9y40a_%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D0%B2%D1%8C%D1%8E-%D1%81-%D0%B3%D0%B5%D0%BD%D0%B4%D0%B8%D1%80%D0%BE%D0%BC-nokia-%D1%80%D0%BE%D1%81%D1%81%D0%B8%D1%8F_tech"><img align="right" width="120" height="90" src="http://s2.dmcdn.net/Aa4Sl/160x90-GQg.jpg" style="border: 2px solid #B9D3FE;"></a><p>ÐÐµÑÐ²Ð¾Ðµ ÑÐºÑÐºÐ»ÑÐ·Ð¸Ð²Ð½Ð¾Ðµ Ð¸Ð½ÑÐµÑÐ²ÑÑ Ñ ÐÐ¸Ð»ÑÑÐ¾Ð¼ ÐÐ¸Ð»ÑÑÐµÐ½Ð¾Ð¼, Ð³ÐµÐ½ÐµÑÐ°Ð»ÑÐ½ÑÐ¼ Ð´Ð¸ÑÐµÐºÑÐ¾ÑÐ¾Ð¼ Nokia Ð Ð¾ÑÑÐ¸Ñ.</p><p>Author: <a href="http://www.dailymotion.com/NOMOBILE"><img src="http://static2.dmcdn.net/static/user/498/895/29598894:avatar_medium.jpg?20091029125433" width="80" height="80" alt="avatar"/>NOMOBILE</a><br />Tags: <a href="http://www.dailymotion.com/tag/Ð¸Ð½ÑÐµÑÐ²ÑÑ">Ð¸Ð½ÑÐµÑÐ²ÑÑ</a> <a href="http://www.dailymotion.com/tag/Nokia">Nokia</a> <a href="http://www.dailymotion.com/tag/N97">N97</a> <a href="http://www.dailymotion.com/tag/ÐÐ¸Ð»ÑÑ">ÐÐ¸Ð»ÑÑ</a> <a href="http://www.dailymotion.com/tag/ÐÐ¸Ð»ÑÑÐµÐ½">ÐÐ¸Ð»ÑÑÐµÐ½</a> <a href="http://www.dailymotion.com/tag/ÑÐºÑÐºÐ»ÑÐ·Ð¸Ð²">ÑÐºÑÐºÐ»ÑÐ·Ð¸Ð²</a> <a href="http://www.dailymotion.com/tag/city:">city:</a> <a href="http://www.dailymotion.com/tag/country:">country:</a> <a href="http://www.dailymotion.com/tag/state:">state:</a> <br />Posted: 23 July 2009<br />Rating: 5.0<br />Votes: 2<br /></p>]]></description>
            <author>rss@dailymotion.com (NOMOBILE)</author>
            <itunes:author>NOMOBILE</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>ÐÐµÑÐ²Ð¾Ðµ ÑÐºÑÐºÐ»ÑÐ·Ð¸Ð²Ð½Ð¾Ðµ Ð¸Ð½ÑÐµÑÐ²ÑÑ Ñ ÐÐ¸Ð»ÑÑÐ¾Ð¼ ÐÐ¸Ð»ÑÑÐµÐ½Ð¾Ð¼, Ð³ÐµÐ½ÐµÑÐ°Ð»ÑÐ½ÑÐ¼ Ð´Ð¸ÑÐµÐºÑÐ¾ÑÐ¾Ð¼ Nokia Ð Ð¾ÑÑÐ¸Ñ.</itunes:summary>
            <itunes:subtitle>ÐÐµÑÐ²Ð¾Ðµ ÑÐºÑÐºÐ»ÑÐ·Ð¸Ð²Ð½Ð¾Ðµ Ð¸Ð½ÑÐµÑÐ²ÑÑ Ñ ÐÐ¸Ð»ÑÑÐ¾Ð¼ ÐÐ¸Ð»ÑÑÐµÐ½Ð¾Ð¼, Ð³ÐµÐ½ÐµÑÐ°Ð»ÑÐ½ÑÐ¼ Ð´Ð¸ÑÐµÐºÑÐ¾ÑÐ¾Ð¼ Nokia Ð Ð¾ÑÑÐ¸Ñ.</itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>2</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x9y40a_%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D0%B2%D1%8C%D1%8E-%D1%81-%D0%B3%D0%B5%D0%BD%D0%B4%D0%B8%D1%80%D0%BE%D0%BC-nokia-%D1%80%D0%BE%D1%81%D1%81%D0%B8%D1%8F_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/NOMOBILE" type="application/rss+xml"/>
            <dm:views>1579</dm:views>
            <dm:comments>1</dm:comments>
            <dm:favorites>1</dm:favorites>
            <dm:id>x9y40a</dm:id>
            <dm:author>NOMOBILE</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x9y40a?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=3hlek870l01f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=64c409cd0d8967927b39845e38f32e03</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/498/895/29598894:avatar_medium.jpg?20091029125433</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Thu, 23 Jul 2009 15:07:06 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x9y40a_%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D0%B2%D1%8C%D1%8E-%D1%81-%D0%B3%D0%B5%D0%BD%D0%B4%D0%B8%D1%80%D0%BE%D0%BC-nokia-%D1%80%D0%BE%D1%81%D1%81%D0%B8%D1%8F_tech</guid>
            <media:title>ÐÐ½ÑÐµÑÐ²ÑÑ Ñ Ð³ÐµÐ½Ð´Ð¸ÑÐ¾Ð¼ Nokia Ð Ð¾ÑÑÐ¸Ñ</media:title>
            <media:credit>NOMOBILE</media:credit>
            <media:thumbnail url="http://s2.dmcdn.net/Aa4Sl/x240-Awn.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x9y40a_%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D0%B2%D1%8C%D1%8E-%D1%81-%D0%B3%D0%B5%D0%BD%D0%B4%D0%B8%D1%80%D0%BE%D0%BC-nokia-%D1%80%D0%BE%D1%81%D1%81%D0%B8%D1%8F_tech" height="360" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x9y40a"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x9y40a" type="text/html" duration="529" width="480" height="360"/>
                <media:content url="http://www.dailymotion.com/swf/video/x9y40a" type="application/x-shockwave-flash" duration="529" width="480" height="360"/>
            </media:group>
            <itunes:keywords>Ð¸Ð½ÑÐµÑÐ²ÑÑ, Nokia, N97, ÐÐ¸Ð»ÑÑ, ÐÐ¸Ð»ÑÑÐµÐ½, ÑÐºÑÐºÐ»ÑÐ·Ð¸Ð², city:, country:, state:</itunes:keywords>
            <media:category label="Ð¸Ð½ÑÐµÑÐ²ÑÑ">Ð¸Ð½ÑÐµÑÐ²ÑÑ</media:category>
            <media:category label="Nokia">Nokia</media:category>
            <media:category label="N97">N97</media:category>
            <media:category label="ÐÐ¸Ð»ÑÑ">ÐÐ¸Ð»ÑÑ</media:category>
            <media:category label="ÐÐ¸Ð»ÑÑÐµÐ½">ÐÐ¸Ð»ÑÑÐµÐ½</media:category>
            <media:category label="ÑÐºÑÐºÐ»ÑÐ·Ð¸Ð²">ÑÐºÑÐºÐ»ÑÐ·Ð¸Ð²</media:category>
            <media:category label="city:">city:</media:category>
            <media:category label="country:">country:</media:category>
            <media:category label="state:">state:</media:category>
        </item>
        <item>
            <title>Ð¯Ð¿Ð¾Ð½ÑÐºÐ¸Ð¹ Ð¼Ð°Ð»ÑÑÐ¸Ðº-ÑÐ¾Ð±Ð¾Ñ Murata Boy</title>
            <link>http://www.dailymotion.com/video/x9rq1q_%D1%8F%D0%BF%D0%BE%D0%BD%D1%81%D0%BA%D0%B8%D0%B9-%D0%BC%D0%B0%D0%BB%D1%8C%D1%87%D0%B8%D0%BA-%D1%80%D0%BE%D0%B1%D0%BE%D1%82-murata-boy_auto</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x9rq1q_%D1%8F%D0%BF%D0%BE%D0%BD%D1%81%D0%BA%D0%B8%D0%B9-%D0%BC%D0%B0%D0%BB%D1%8C%D1%87%D0%B8%D0%BA-%D1%80%D0%BE%D0%B1%D0%BE%D1%82-murata-boy_auto"><img align="right" width="120" height="90" src="http://s1.dmcdn.net/AOGZn/160x90-S11.jpg" style="border: 2px solid #B9D3FE;"></a><p>  Ð Ð¾Ð±Ð¾Ñ-Ð²ÐµÐ»Ð¾ÑÐ¸Ð¿ÐµÐ´Ð¸ÑÑ Murata Boy, ÐºÐ¾ÑÐ¾ÑÑÐ¹ "ÑÐ¾Ð´Ð¸Ð»ÑÑ"Ð² Ð¾ÐºÑÑÐ±ÑÐµ 2005 Ð³Ð¾Ð´Ð°.  </p><p>Author: <a href="http://www.dailymotion.com/Autocentre"><img src="http://static2.dmcdn.net/static/user/988/990/28099889:avatar_medium.jpg?20090701113635" width="80" height="80" alt="avatar"/>Autocentre</a><br />Tags: <a href="http://www.dailymotion.com/tag/Ð°Ð²ÑÐ¾Ð¼Ð¾Ð±ÑÐ»ÑÐ½Ð¸Ð¹">Ð°Ð²ÑÐ¾Ð¼Ð¾Ð±ÑÐ»ÑÐ½Ð¸Ð¹</a> <a href="http://www.dailymotion.com/tag/cars">cars</a> <a href="http://www.dailymotion.com/tag/ÐÐµÑÑÐ¸Ð¹">ÐÐµÑÑÐ¸Ð¹</a> <a href="http://www.dailymotion.com/tag/ÑÐ¾Ð±Ð¾ÑÑ">ÑÐ¾Ð±Ð¾ÑÑ</a> <a href="http://www.dailymotion.com/tag/ÐÐ²ÑÐ¾ÑÐµÐ½ÑÑ">ÐÐ²ÑÐ¾ÑÐµÐ½ÑÑ</a> <a href="http://www.dailymotion.com/tag/Ð°Ð²ÑÐ¾">Ð°Ð²ÑÐ¾</a> <a href="http://www.dailymotion.com/tag/auto">auto</a> <br />Posted: 04 July 2009<br />Rating: 5.0<br />Votes: 4<br /></p>]]></description>
            <author>rss@dailymotion.com (Autocentre)</author>
            <itunes:author>Autocentre</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>  Ð Ð¾Ð±Ð¾Ñ-Ð²ÐµÐ»Ð¾ÑÐ¸Ð¿ÐµÐ´Ð¸ÑÑ Murata Boy, ÐºÐ¾ÑÐ¾ÑÑÐ¹ &quot;ÑÐ¾Ð´Ð¸Ð»ÑÑ&quot;Ð² Ð¾ÐºÑÑÐ±ÑÐµ 2005 Ð³Ð¾Ð´Ð°.  </itunes:summary>
            <itunes:subtitle>  Ð Ð¾Ð±Ð¾Ñ-Ð²ÐµÐ»Ð¾ÑÐ¸Ð¿ÐµÐ´Ð¸ÑÑ Murata Boy, ÐºÐ¾ÑÐ¾ÑÑÐ¹ &quot;ÑÐ¾Ð´Ð¸Ð»ÑÑ&quot;Ð² Ð¾ÐºÑÑÐ±ÑÐµ 2005 Ð³Ð¾Ð´Ð°.  </itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>4</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x9rq1q_%D1%8F%D0%BF%D0%BE%D0%BD%D1%81%D0%BA%D0%B8%D0%B9-%D0%BC%D0%B0%D0%BB%D1%8C%D1%87%D0%B8%D0%BA-%D1%80%D0%BE%D0%B1%D0%BE%D1%82-murata-boy_auto" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/Autocentre" type="application/rss+xml"/>
            <dm:views>1816</dm:views>
            <dm:comments>1</dm:comments>
            <dm:favorites>1</dm:favorites>
            <dm:id>x9rq1q</dm:id>
            <dm:author>Autocentre</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x9rq1q?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=9ovxgvy2db1f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=33e19ec974dc993ae344bfed7bacf597</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/988/990/28099889:avatar_medium.jpg?20090701113635</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>auto</dm:channels>
            <pubDate>Sat, 04 Jul 2009 18:06:14 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x9rq1q_%D1%8F%D0%BF%D0%BE%D0%BD%D1%81%D0%BA%D0%B8%D0%B9-%D0%BC%D0%B0%D0%BB%D1%8C%D1%87%D0%B8%D0%BA-%D1%80%D0%BE%D0%B1%D0%BE%D1%82-murata-boy_auto</guid>
            <media:title>Ð¯Ð¿Ð¾Ð½ÑÐºÐ¸Ð¹ Ð¼Ð°Ð»ÑÑÐ¸Ðº-ÑÐ¾Ð±Ð¾Ñ Murata Boy</media:title>
            <media:credit>Autocentre</media:credit>
            <media:thumbnail url="http://s1.dmcdn.net/AOGZn/x240-GFP.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x9rq1q_%D1%8F%D0%BF%D0%BE%D0%BD%D1%81%D0%BA%D0%B8%D0%B9-%D0%BC%D0%B0%D0%BB%D1%8C%D1%87%D0%B8%D0%BA-%D1%80%D0%BE%D0%B1%D0%BE%D1%82-murata-boy_auto" height="360" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x9rq1q"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x9rq1q" type="text/html" duration="54" width="480" height="360"/>
                <media:content url="http://www.dailymotion.com/swf/video/x9rq1q" type="application/x-shockwave-flash" duration="54" width="480" height="360"/>
            </media:group>
            <itunes:keywords>Ð°Ð²ÑÐ¾Ð¼Ð¾Ð±ÑÐ»ÑÐ½Ð¸Ð¹, cars, ÐÐµÑÑÐ¸Ð¹, ÑÐ¾Ð±Ð¾ÑÑ, ÐÐ²ÑÐ¾ÑÐµÐ½ÑÑ, Ð°Ð²ÑÐ¾, auto</itunes:keywords>
            <media:category label="Ð°Ð²ÑÐ¾Ð¼Ð¾Ð±ÑÐ»ÑÐ½Ð¸Ð¹">Ð°Ð²ÑÐ¾Ð¼Ð¾Ð±ÑÐ»ÑÐ½Ð¸Ð¹</media:category>
            <media:category label="cars">cars</media:category>
            <media:category label="ÐÐµÑÑÐ¸Ð¹">ÐÐµÑÑÐ¸Ð¹</media:category>
            <media:category label="ÑÐ¾Ð±Ð¾ÑÑ">ÑÐ¾Ð±Ð¾ÑÑ</media:category>
            <media:category label="ÐÐ²ÑÐ¾ÑÐµÐ½ÑÑ">ÐÐ²ÑÐ¾ÑÐµÐ½ÑÑ</media:category>
            <media:category label="Ð°Ð²ÑÐ¾">Ð°Ð²ÑÐ¾</media:category>
            <media:category label="auto">auto</media:category>
        </item>
        <item>
            <title>BI-ÑÐ¸ÑÑÐµÐ¼Ð° ÐºÐ¾Ð¼Ð¿Ð°Ð½Ð¸Ð¸ &quot;ÐÐ½ÑÐµÐ³ÑÐ°&quot;</title>
            <link>http://www.dailymotion.com/video/x9ntui_bi-%D1%81%D0%B8%D1%81%D1%82%D0%B5%D0%BC%D0%B0-%D0%BA%D0%BE%D0%BC%D0%BF%D0%B0%D0%BD%D0%B8%D0%B8-%D0%B8%D0%BD%D1%82%D0%B5%D0%B3%D1%80%D0%B0_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x9ntui_bi-%D1%81%D0%B8%D1%81%D1%82%D0%B5%D0%BC%D0%B0-%D0%BA%D0%BE%D0%BC%D0%BF%D0%B0%D0%BD%D0%B8%D0%B8-%D0%B8%D0%BD%D1%82%D0%B5%D0%B3%D1%80%D0%B0_tech"><img align="right" width="120" height="90" src="http://s1.dmcdn.net/gIuJ/160x90-yqY.jpg" style="border: 2px solid #B9D3FE;"></a><p></p><p>Author: <a href="http://www.dailymotion.com/cnews"><img src="http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338" width="80" height="80" alt="avatar"/>cnews</a><br />Tags: <a href="http://www.dailymotion.com/tag/BI-ÑÐ¸ÑÑÐµÐ¼Ð°">BI-ÑÐ¸ÑÑÐµÐ¼Ð°</a> <a href="http://www.dailymotion.com/tag/ÑÐ¸ÑÑÐµÐ¼Ð½Ð°Ñ">ÑÐ¸ÑÑÐµÐ¼Ð½Ð°Ñ</a> <a href="http://www.dailymotion.com/tag/Ð¸Ð½ÑÐµÐ³ÑÐ°ÑÐ¸Ñ">Ð¸Ð½ÑÐµÐ³ÑÐ°ÑÐ¸Ñ</a> <a href="http://www.dailymotion.com/tag/Oracle">Oracle</a> <a href="http://www.dailymotion.com/tag/ÐºÑÐ¾Ðº">ÐºÑÐ¾Ðº</a> <br />Posted: 23 June 2009<br />Rating: 0.0<br />Votes: 0<br /></p>]]></description>
            <author>rss@dailymotion.com (cnews)</author>
            <itunes:author>cnews</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary></itunes:summary>
            <itunes:subtitle></itunes:subtitle>
            <dm:videorating>0.0</dm:videorating>
            <dm:videovotes>0</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x9ntui_bi-%D1%81%D0%B8%D1%81%D1%82%D0%B5%D0%BC%D0%B0-%D0%BA%D0%BE%D0%BC%D0%BF%D0%B0%D0%BD%D0%B8%D0%B8-%D0%B8%D0%BD%D1%82%D0%B5%D0%B3%D1%80%D0%B0_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/cnews" type="application/rss+xml"/>
            <dm:views>918</dm:views>
            <dm:comments>0</dm:comments>
            <dm:favorites>0</dm:favorites>
            <dm:id>x9ntui</dm:id>
            <dm:author>cnews</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x9ntui?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=68lnfcujwh1f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=7e92335aa915fd6b6f3a5610babfaf53</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Tue, 23 Jun 2009 10:25:31 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x9ntui_bi-%D1%81%D0%B8%D1%81%D1%82%D0%B5%D0%BC%D0%B0-%D0%BA%D0%BE%D0%BC%D0%BF%D0%B0%D0%BD%D0%B8%D0%B8-%D0%B8%D0%BD%D1%82%D0%B5%D0%B3%D1%80%D0%B0_tech</guid>
            <media:title>BI-ÑÐ¸ÑÑÐµÐ¼Ð° ÐºÐ¾Ð¼Ð¿Ð°Ð½Ð¸Ð¸ &quot;ÐÐ½ÑÐµÐ³ÑÐ°&quot;</media:title>
            <media:credit>cnews</media:credit>
            <media:thumbnail url="http://s1.dmcdn.net/gIuJ/x240-HX9.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x9ntui_bi-%D1%81%D0%B8%D1%81%D1%82%D0%B5%D0%BC%D0%B0-%D0%BA%D0%BE%D0%BC%D0%BF%D0%B0%D0%BD%D0%B8%D0%B8-%D0%B8%D0%BD%D1%82%D0%B5%D0%B3%D1%80%D0%B0_tech" height="276" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x9ntui"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x9ntui" type="text/html" duration="797" width="480" height="276"/>
                <media:content url="http://www.dailymotion.com/swf/video/x9ntui" type="application/x-shockwave-flash" duration="797" width="480" height="276"/>
            </media:group>
            <itunes:keywords>BI-ÑÐ¸ÑÑÐµÐ¼Ð°, ÑÐ¸ÑÑÐµÐ¼Ð½Ð°Ñ, Ð¸Ð½ÑÐµÐ³ÑÐ°ÑÐ¸Ñ, Oracle, ÐºÑÐ¾Ðº</itunes:keywords>
            <media:category label="BI-ÑÐ¸ÑÑÐµÐ¼Ð°">BI-ÑÐ¸ÑÑÐµÐ¼Ð°</media:category>
            <media:category label="ÑÐ¸ÑÑÐµÐ¼Ð½Ð°Ñ">ÑÐ¸ÑÑÐµÐ¼Ð½Ð°Ñ</media:category>
            <media:category label="Ð¸Ð½ÑÐµÐ³ÑÐ°ÑÐ¸Ñ">Ð¸Ð½ÑÐµÐ³ÑÐ°ÑÐ¸Ñ</media:category>
            <media:category label="Oracle">Oracle</media:category>
            <media:category label="ÐºÑÐ¾Ðº">ÐºÑÐ¾Ðº</media:category>
        </item>
        <item>
            <title>RoboFest_900</title>
            <link>http://www.dailymotion.com/video/x9e0te_robofest-900_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x9e0te_robofest-900_tech"><img align="right" width="120" height="90" src="http://s2.dmcdn.net/g3h6/160x90-IfC.jpg" style="border: 2px solid #B9D3FE;"></a><p></p><p>Author: <a href="http://www.dailymotion.com/cnews"><img src="http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338" width="80" height="80" alt="avatar"/>cnews</a><br />Tags: <a href="http://www.dailymotion.com/tag/ÑÐ¾Ð±Ð¾Ñ">ÑÐ¾Ð±Ð¾Ñ</a> <a href="http://www.dailymotion.com/tag/Ð¼ÑÑÑÐ¸">Ð¼ÑÑÑÐ¸</a> <a href="http://www.dailymotion.com/tag/ÑÐ¾ÑÐµÐ²Ð½Ð¾Ð²Ð°Ð½Ð¸Ðµ">ÑÐ¾ÑÐµÐ²Ð½Ð¾Ð²Ð°Ð½Ð¸Ðµ</a> <a href="http://www.dailymotion.com/tag/ÑÐµÑÐ¼Ð¸Ð½Ð°ÑÐ¾Ñ">ÑÐµÑÐ¼Ð¸Ð½Ð°ÑÐ¾Ñ</a> <br />Posted: 25 May 2009<br />Rating: 5.0<br />Votes: 1<br /></p>]]></description>
            <author>rss@dailymotion.com (cnews)</author>
            <itunes:author>cnews</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary></itunes:summary>
            <itunes:subtitle></itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>1</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x9e0te_robofest-900_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/cnews" type="application/rss+xml"/>
            <dm:views>424</dm:views>
            <dm:comments>0</dm:comments>
            <dm:favorites>1</dm:favorites>
            <dm:id>x9e0te</dm:id>
            <dm:author>cnews</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x9e0te?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=bzslljqav31f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=b0fcfecc1b512df79084de63d5eec9bb</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Mon, 25 May 2009 09:37:23 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x9e0te_robofest-900_tech</guid>
            <media:title>RoboFest_900</media:title>
            <media:credit>cnews</media:credit>
            <media:thumbnail url="http://s2.dmcdn.net/g3h6/x240-zK4.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x9e0te_robofest-900_tech" height="276" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x9e0te"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x9e0te" type="text/html" duration="150" width="480" height="276"/>
                <media:content url="http://www.dailymotion.com/swf/video/x9e0te" type="application/x-shockwave-flash" duration="150" width="480" height="276"/>
            </media:group>
            <itunes:keywords>ÑÐ¾Ð±Ð¾Ñ, Ð¼ÑÑÑÐ¸, ÑÐ¾ÑÐµÐ²Ð½Ð¾Ð²Ð°Ð½Ð¸Ðµ, ÑÐµÑÐ¼Ð¸Ð½Ð°ÑÐ¾Ñ</itunes:keywords>
            <media:category label="ÑÐ¾Ð±Ð¾Ñ">ÑÐ¾Ð±Ð¾Ñ</media:category>
            <media:category label="Ð¼ÑÑÑÐ¸">Ð¼ÑÑÑÐ¸</media:category>
            <media:category label="ÑÐ¾ÑÐµÐ²Ð½Ð¾Ð²Ð°Ð½Ð¸Ðµ">ÑÐ¾ÑÐµÐ²Ð½Ð¾Ð²Ð°Ð½Ð¸Ðµ</media:category>
            <media:category label="ÑÐµÑÐ¼Ð¸Ð½Ð°ÑÐ¾Ñ">ÑÐµÑÐ¼Ð¸Ð½Ð°ÑÐ¾Ñ</media:category>
        </item>
        <item>
            <title>ÐÐ±Ð·Ð¾Ñ: ÑÐµÐ»ÐµÑÐ¾Ð½ LG Arena Ñ ÑÑÐµÑÐ¼ÐµÑÐ½ÑÐ¼ Ð¸Ð½ÑÐµÑÑÐµÐ¹ÑÐ¾Ð¼ S-Class</title>
            <link>http://www.dailymotion.com/video/x9e2yl_%D0%BE%D0%B1%D0%B7%D0%BE%D1%80-%D1%82%D0%B5%D0%BB%D0%B5%D1%84%D0%BE%D0%BD-lg-arena-%D1%81-%D1%82%D1%80%D0%B5%D1%85%D0%BC%D0%B5%D1%80%D0%BD%D1%8B%D0%BC_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x9e2yl_%D0%BE%D0%B1%D0%B7%D0%BE%D1%80-%D1%82%D0%B5%D0%BB%D0%B5%D1%84%D0%BE%D0%BD-lg-arena-%D1%81-%D1%82%D1%80%D0%B5%D1%85%D0%BC%D0%B5%D1%80%D0%BD%D1%8B%D0%BC_tech"><img align="right" width="120" height="90" src="http://s1.dmcdn.net/AtW0K/160x90-Vlf.jpg" style="border: 2px solid #B9D3FE;"></a><p>ÐÐ»ÑÑÐµÐ²Ð¾Ð¹ Ð¾ÑÐ¾Ð±ÐµÐ½Ð½Ð¾ÑÑÑÑ ÑÐµÐ»ÐµÑÐ¾Ð½Ð° LG Arena ÑÐ²Ð»ÑÐµÑÑÑ Ð¸Ð½Ð½Ð¾Ð²Ð°ÑÐ¸Ð¾Ð½Ð½ÑÐ¹ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»ÑÑÐºÐ¸Ð¹ 3D-Ð¸Ð½ÑÐµÑÑÐµÐ¹Ñ S-Class, Ð½Ðµ Ð¸Ð¼ÐµÑÑÐ¸Ð¹ Ð°Ð½Ð°Ð»Ð¾Ð³Ð¾Ð²</p><p>Author: <a href="http://www.dailymotion.com/cnews"><img src="http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338" width="80" height="80" alt="avatar"/>cnews</a><br />Tags: <a href="http://www.dailymotion.com/tag/Arena">Arena</a> <a href="http://www.dailymotion.com/tag/ÑÐµÐ»ÐµÑÐ¾Ð½">ÑÐµÐ»ÐµÑÐ¾Ð½</a> <a href="http://www.dailymotion.com/tag/Ð¼Ð¾Ð±Ð¸Ð»ÑÐ½ÑÐ¹">Ð¼Ð¾Ð±Ð¸Ð»ÑÐ½ÑÐ¹</a> <a href="http://www.dailymotion.com/tag/ÑÐµÐ½ÑÐ¾ÑÐ½ÑÐ¹">ÑÐµÐ½ÑÐ¾ÑÐ½ÑÐ¹</a> <a href="http://www.dailymotion.com/tag/ÑÐºÑÐ°Ð½">ÑÐºÑÐ°Ð½</a> <br />Posted: 25 May 2009<br />Rating: 5.0<br />Votes: 1<br /></p>]]></description>
            <author>rss@dailymotion.com (cnews)</author>
            <itunes:author>cnews</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>ÐÐ»ÑÑÐµÐ²Ð¾Ð¹ Ð¾ÑÐ¾Ð±ÐµÐ½Ð½Ð¾ÑÑÑÑ ÑÐµÐ»ÐµÑÐ¾Ð½Ð° LG Arena ÑÐ²Ð»ÑÐµÑÑÑ Ð¸Ð½Ð½Ð¾Ð²Ð°ÑÐ¸Ð¾Ð½Ð½ÑÐ¹ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»ÑÑÐºÐ¸Ð¹ 3D-Ð¸Ð½ÑÐµÑÑÐµÐ¹Ñ S-Class, Ð½Ðµ Ð¸Ð¼ÐµÑÑÐ¸Ð¹ Ð°Ð½Ð°Ð»Ð¾Ð³Ð¾Ð²</itunes:summary>
            <itunes:subtitle>ÐÐ»ÑÑÐµÐ²Ð¾Ð¹ Ð¾ÑÐ¾Ð±ÐµÐ½Ð½Ð¾ÑÑÑÑ ÑÐµÐ»ÐµÑÐ¾Ð½Ð° LG Arena ÑÐ²Ð»ÑÐµÑÑÑ Ð¸Ð½Ð½Ð¾Ð²Ð°ÑÐ¸Ð¾Ð½Ð½ÑÐ¹ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»ÑÑÐºÐ¸Ð¹ 3D-Ð¸Ð½ÑÐµÑÑÐµÐ¹Ñ S-Class, Ð½Ðµ Ð¸Ð¼ÐµÑÑÐ¸Ð¹ Ð°Ð½Ð°Ð»Ð¾Ð³Ð¾Ð²</itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>1</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x9e2yl_%D0%BE%D0%B1%D0%B7%D0%BE%D1%80-%D1%82%D0%B5%D0%BB%D0%B5%D1%84%D0%BE%D0%BD-lg-arena-%D1%81-%D1%82%D1%80%D0%B5%D1%85%D0%BC%D0%B5%D1%80%D0%BD%D1%8B%D0%BC_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/cnews" type="application/rss+xml"/>
            <dm:views>3755</dm:views>
            <dm:comments>1</dm:comments>
            <dm:favorites>0</dm:favorites>
            <dm:id>x9e2yl</dm:id>
            <dm:author>cnews</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x9e2yl?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=422ab2relt1f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=6702920ee530f83cac56c4dc1fa5c00c</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Mon, 25 May 2009 13:36:42 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x9e2yl_%D0%BE%D0%B1%D0%B7%D0%BE%D1%80-%D1%82%D0%B5%D0%BB%D0%B5%D1%84%D0%BE%D0%BD-lg-arena-%D1%81-%D1%82%D1%80%D0%B5%D1%85%D0%BC%D0%B5%D1%80%D0%BD%D1%8B%D0%BC_tech</guid>
            <media:title>ÐÐ±Ð·Ð¾Ñ: ÑÐµÐ»ÐµÑÐ¾Ð½ LG Arena Ñ ÑÑÐµÑÐ¼ÐµÑÐ½ÑÐ¼ Ð¸Ð½ÑÐµÑÑÐµÐ¹ÑÐ¾Ð¼ S-Class</media:title>
            <media:credit>cnews</media:credit>
            <media:thumbnail url="http://s1.dmcdn.net/AtW0K/x240-A1s.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x9e2yl_%D0%BE%D0%B1%D0%B7%D0%BE%D1%80-%D1%82%D0%B5%D0%BB%D0%B5%D1%84%D0%BE%D0%BD-lg-arena-%D1%81-%D1%82%D1%80%D0%B5%D1%85%D0%BC%D0%B5%D1%80%D0%BD%D1%8B%D0%BC_tech" height="276" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x9e2yl"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x9e2yl" type="text/html" duration="154" width="480" height="276"/>
                <media:content url="http://www.dailymotion.com/swf/video/x9e2yl" type="application/x-shockwave-flash" duration="154" width="480" height="276"/>
            </media:group>
            <itunes:keywords>Arena, ÑÐµÐ»ÐµÑÐ¾Ð½, Ð¼Ð¾Ð±Ð¸Ð»ÑÐ½ÑÐ¹, ÑÐµÐ½ÑÐ¾ÑÐ½ÑÐ¹, ÑÐºÑÐ°Ð½</itunes:keywords>
            <media:category label="Arena">Arena</media:category>
            <media:category label="ÑÐµÐ»ÐµÑÐ¾Ð½">ÑÐµÐ»ÐµÑÐ¾Ð½</media:category>
            <media:category label="Ð¼Ð¾Ð±Ð¸Ð»ÑÐ½ÑÐ¹">Ð¼Ð¾Ð±Ð¸Ð»ÑÐ½ÑÐ¹</media:category>
            <media:category label="ÑÐµÐ½ÑÐ¾ÑÐ½ÑÐ¹">ÑÐµÐ½ÑÐ¾ÑÐ½ÑÐ¹</media:category>
            <media:category label="ÑÐºÑÐ°Ð½">ÑÐºÑÐ°Ð½</media:category>
        </item>
        <item>
            <title>Ð Ð¾Ð±Ð¾Ñ, ÑÐ¿ÑÐ°Ð²Ð»ÑÐµÐ¼ÑÐ¹ ÑÐ¸Ð»Ð¾Ð¹ Ð¼ÑÑÐ»Ð¸</title>
            <link>http://www.dailymotion.com/video/x8v23s_%D1%80%D0%BE%D0%B1%D0%BE%D1%82-%D1%83%D0%BF%D1%80%D0%B0%D0%B2%D0%BB%D1%8F%D0%B5%D0%BC%D1%8B%D0%B9-%D1%81%D0%B8%D0%BB%D0%BE%D0%B9-%D0%BC%D1%8B%D1%81%D0%BB%D0%B8_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x8v23s_%D1%80%D0%BE%D0%B1%D0%BE%D1%82-%D1%83%D0%BF%D1%80%D0%B0%D0%B2%D0%BB%D1%8F%D0%B5%D0%BC%D1%8B%D0%B9-%D1%81%D0%B8%D0%BB%D0%BE%D0%B9-%D0%BC%D1%8B%D1%81%D0%BB%D0%B8_tech"><img align="right" width="120" height="90" src="http://s2.dmcdn.net/MpOi/160x90-H_o.jpg" style="border: 2px solid #B9D3FE;"></a><p>Ð¯Ð¿Ð¾Ð½ÑÐºÐ¸Ð¹ Ð¿ÑÐ¾Ð¸Ð·Ð²Ð¾Ð´Ð¸ÑÐµÐ»Ñ Ð°Ð²ÑÐ¾Ð¼Ð¾Ð±Ð¸Ð»ÐµÐ¹ ÐºÐ¾Ð¼Ð¿Ð°Ð½Ð¸Ñ Ð¥Ð¾Ð½Ð´Ð° ÑÐ°Ð·ÑÐ°Ð±Ð¾ÑÐ°Ð»Ð° ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ñ ÑÐ¿ÑÐ°Ð²Ð»ÐµÐ½Ð¸Ñ Ð´Ð²Ð¸Ð¶ÐµÐ½Ð¸ÑÐ¼Ð¸ ÑÐ¾Ð±Ð¾ÑÐ° Ð¿ÑÐ¸ Ð¿Ð¾Ð¼Ð¾ÑÐ¸ ÑÐ¸Ð³Ð½Ð°Ð»Ð¾Ð² ÑÐµÐ»Ð¾Ð²ÐµÑÐµÑÐºÐ¾Ð³Ð¾ Ð¼Ð¾Ð·Ð³Ð°.</p><p>Author: <a href="http://www.dailymotion.com/RussianNTD"><img src="http://static2.dmcdn.net/static/user/473/499/23994374:avatar_medium.jpg?20110513130152" width="80" height="80" alt="avatar"/>RussianNTD</a><br />Tags: <a href="http://www.dailymotion.com/tag/NTD">NTD</a> <a href="http://www.dailymotion.com/tag/NTDTV">NTDTV</a> <a href="http://www.dailymotion.com/tag/New">New</a> <a href="http://www.dailymotion.com/tag/Tang">Tang</a> <a href="http://www.dailymotion.com/tag/Dynasty">Dynasty</a> <a href="http://www.dailymotion.com/tag/Ð¯Ð¿Ð¾Ð½Ð¸Ñ">Ð¯Ð¿Ð¾Ð½Ð¸Ñ</a> <a href="http://www.dailymotion.com/tag/ÑÐ¾Ð±Ð¾Ñ">ÑÐ¾Ð±Ð¾Ñ</a> <a href="http://www.dailymotion.com/tag/Ð¼ÑÑÐ»Ñ">Ð¼ÑÑÐ»Ñ</a> <br />Posted: 03 April 2009<br />Rating: 5.0<br />Votes: 1<br /></p>]]></description>
            <author>rss@dailymotion.com (RussianNTD)</author>
            <itunes:author>RussianNTD</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>Ð¯Ð¿Ð¾Ð½ÑÐºÐ¸Ð¹ Ð¿ÑÐ¾Ð¸Ð·Ð²Ð¾Ð´Ð¸ÑÐµÐ»Ñ Ð°Ð²ÑÐ¾Ð¼Ð¾Ð±Ð¸Ð»ÐµÐ¹ ÐºÐ¾Ð¼Ð¿Ð°Ð½Ð¸Ñ Ð¥Ð¾Ð½Ð´Ð° ÑÐ°Ð·ÑÐ°Ð±Ð¾ÑÐ°Ð»Ð° ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ñ ÑÐ¿ÑÐ°Ð²Ð»ÐµÐ½Ð¸Ñ Ð´Ð²Ð¸Ð¶ÐµÐ½Ð¸ÑÐ¼Ð¸ ÑÐ¾Ð±Ð¾ÑÐ° Ð¿ÑÐ¸ Ð¿Ð¾Ð¼Ð¾ÑÐ¸ ÑÐ¸Ð³Ð½Ð°Ð»Ð¾Ð² ÑÐµÐ»Ð¾Ð²ÐµÑÐµÑÐºÐ¾Ð³Ð¾ Ð¼Ð¾Ð·Ð³Ð°.</itunes:summary>
            <itunes:subtitle>Ð¯Ð¿Ð¾Ð½ÑÐºÐ¸Ð¹ Ð¿ÑÐ¾Ð¸Ð·Ð²Ð¾Ð´Ð¸ÑÐµÐ»Ñ Ð°Ð²ÑÐ¾Ð¼Ð¾Ð±Ð¸Ð»ÐµÐ¹ ÐºÐ¾Ð¼Ð¿Ð°Ð½Ð¸Ñ Ð¥Ð¾Ð½Ð´Ð° ÑÐ°Ð·ÑÐ°Ð±Ð¾ÑÐ°Ð»Ð° ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ñ ÑÐ¿ÑÐ°Ð²Ð»ÐµÐ½Ð¸Ñ Ð´Ð²Ð¸Ð¶ÐµÐ½Ð¸ÑÐ¼Ð¸ ÑÐ¾Ð±Ð¾ÑÐ° Ð¿ÑÐ¸ Ð¿Ð¾Ð¼Ð¾ÑÐ¸ ÑÐ¸Ð³Ð½Ð°Ð»Ð¾Ð² ÑÐµÐ»Ð¾Ð²ÐµÑÐµÑÐºÐ¾Ð³Ð¾ Ð¼Ð¾Ð·Ð³Ð°.</itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>1</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x8v23s_%D1%80%D0%BE%D0%B1%D0%BE%D1%82-%D1%83%D0%BF%D1%80%D0%B0%D0%B2%D0%BB%D1%8F%D0%B5%D0%BC%D1%8B%D0%B9-%D1%81%D0%B8%D0%BB%D0%BE%D0%B9-%D0%BC%D1%8B%D1%81%D0%BB%D0%B8_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/RussianNTD" type="application/rss+xml"/>
            <dm:views>810</dm:views>
            <dm:comments>1</dm:comments>
            <dm:favorites>1</dm:favorites>
            <dm:id>x8v23s</dm:id>
            <dm:author>RussianNTD</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x8v23s?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=ed91vml6yt1f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=9f7579426657bb991283e5c433cff647</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/473/499/23994374:avatar_medium.jpg?20110513130152</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Fri, 03 Apr 2009 10:14:01 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x8v23s_%D1%80%D0%BE%D0%B1%D0%BE%D1%82-%D1%83%D0%BF%D1%80%D0%B0%D0%B2%D0%BB%D1%8F%D0%B5%D0%BC%D1%8B%D0%B9-%D1%81%D0%B8%D0%BB%D0%BE%D0%B9-%D0%BC%D1%8B%D1%81%D0%BB%D0%B8_tech</guid>
            <media:title>Ð Ð¾Ð±Ð¾Ñ, ÑÐ¿ÑÐ°Ð²Ð»ÑÐµÐ¼ÑÐ¹ ÑÐ¸Ð»Ð¾Ð¹ Ð¼ÑÑÐ»Ð¸</media:title>
            <media:credit>RussianNTD</media:credit>
            <media:thumbnail url="http://s2.dmcdn.net/MpOi/x240-D3D.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x8v23s_%D1%80%D0%BE%D0%B1%D0%BE%D1%82-%D1%83%D0%BF%D1%80%D0%B0%D0%B2%D0%BB%D1%8F%D0%B5%D0%BC%D1%8B%D0%B9-%D1%81%D0%B8%D0%BB%D0%BE%D0%B9-%D0%BC%D1%8B%D1%81%D0%BB%D0%B8_tech" height="360" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x8v23s"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x8v23s" type="text/html" duration="75" width="480" height="360"/>
                <media:content url="http://www.dailymotion.com/swf/video/x8v23s" type="application/x-shockwave-flash" duration="75" width="480" height="360"/>
            </media:group>
            <itunes:keywords>NTD, NTDTV, New, Tang, Dynasty, Ð¯Ð¿Ð¾Ð½Ð¸Ñ, ÑÐ¾Ð±Ð¾Ñ, Ð¼ÑÑÐ»Ñ</itunes:keywords>
            <media:category label="NTD">NTD</media:category>
            <media:category label="NTDTV">NTDTV</media:category>
            <media:category label="New">New</media:category>
            <media:category label="Tang">Tang</media:category>
            <media:category label="Dynasty">Dynasty</media:category>
            <media:category label="Ð¯Ð¿Ð¾Ð½Ð¸Ñ">Ð¯Ð¿Ð¾Ð½Ð¸Ñ</media:category>
            <media:category label="ÑÐ¾Ð±Ð¾Ñ">ÑÐ¾Ð±Ð¾Ñ</media:category>
            <media:category label="Ð¼ÑÑÐ»Ñ">Ð¼ÑÑÐ»Ñ</media:category>
        </item>
        <item>
            <title>Windows 7 ÑÐ¼Ð¾Ð¶ÐµÑ ÑÐ°Ð±Ð¾ÑÐ°ÑÑ Ð´Ð°Ð¶Ðµ Ð½Ð° Ð½ÐµÑÐ±ÑÐºÐ°Ñ</title>
            <link>http://www.dailymotion.com/video/x8ffyu_windows-7-%D1%81%D0%BC%D0%BE%D0%B6%D0%B5%D1%82-%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D1%82%D1%8C-%D0%B4%D0%B0%D0%B6%D0%B5-%D0%BD%D0%B0-%D0%BD_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x8ffyu_windows-7-%D1%81%D0%BC%D0%BE%D0%B6%D0%B5%D1%82-%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D1%82%D1%8C-%D0%B4%D0%B0%D0%B6%D0%B5-%D0%BD%D0%B0-%D0%BD_tech"><img align="right" width="120" height="90" src="http://s2.dmcdn.net/ptkP/160x90-VCT.jpg" style="border: 2px solid #B9D3FE;"></a><p>ÐÐµÑÐºÐ»ÑÐ¶Ð°Ñ Vista Ð¿Ð¾Ð´Ð¼Ð¾ÑÐ¸Ð»Ð° ÑÐµÐ¿ÑÑÐ°ÑÐ¸Ñ ÑÐ¾ÑÑÐ²ÐµÑÐ½Ð¾Ð³Ð¾ Ð³Ð¸Ð³Ð°Ð½ÑÐ°. Ð§ÑÐ¾Ð±Ñ ÑÐµÐ°Ð±Ð¸Ð»Ð¸ÑÐ¸ÑÐ¾Ð²Ð°ÑÑÑÑ Ð¿ÐµÑÐµÐ´ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»ÑÐ¼Ð¸ Microsoft Ð³Ð¾ÑÐ¾Ð²Ð¸Ñ Ðº Ð²ÑÐ¿ÑÑÐºÑ Ð½Ð¾Ð²ÑÑ Ð¾Ð¿ÐµÑÐ°ÑÐ¸Ð¾Ð½Ð½ÑÑ ÑÐ¸ÑÑÐµÐ¼Ñ  Windows 7. ÐÐ¾ ÑÑÑÐ¸, ÑÑÐ¾ Ð±ÑÐ»Ð° ÑÐ°Ð±Ð¾ÑÐ° Ð½Ð°Ð´ Ð¾ÑÐ¸Ð±ÐºÐ°Ð¼Ð¸. Ð¡Ð¾Ð·Ð´Ð°ÑÐµÐ»Ð¸ Ð¸ÑÐ¿ÑÐ°Ð²Ð¸Ð»Ð¸ Ð±Ð¾Ð»ÑÑÐ¸Ð½ÑÑÐ²Ð¾ Ð½ÐµÐ´Ð¾ÑÐµÑÐ¾Ð² Ð¿ÑÐµÐ´ÑÐ´ÑÑÐµÐ¹ ÐÐ¡, Ð²Ð½ÐµÐ´ÑÐ¸Ð»Ð¸ Ð¿ÑÐµÐ¸Ð¼ÑÑÐµÑÑÐ²Ð° XP  Ð¸ Ð´Ð¾Ð±Ð°Ð²Ð¸Ð»Ð¸ Ð¿Ð¾Ð¿ÑÐ»ÑÑÐ½ÑÑ ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ñ ÑÐµÐ½ÑÐ¾ÑÐ½Ð¾Ð³Ð¾ ÑÐ¿ÑÐ°Ð²Ð»ÐµÐ½Ð¸Ñ.  <br>ÐÐ»Ð°ÑÑÐ¾ÑÐ¼Ð° nVidia Ion Ð¿Ð¾Ð·Ð²Ð¾Ð»Ð¸Ñ Ð½Ð¾Ð²Ð¾Ð¹ ÐÐ¡ Ð·Ð°Ð¿ÑÑÐºÐ°ÑÑÑÑ Ð½Ð° Ð¼Ð°Ð»Ð¾Ð¼Ð¾ÑÐ½ÑÑ Ð¼Ð¾Ð±Ð¸Ð»ÑÐ½ÑÑ ÐÐ. <br>Ð ÐµÐ¿Ð¾ÑÑÐ°Ð¶ Ñ http://tv.cnews.ru</p><p>Author: <a href="http://www.dailymotion.com/cnews"><img src="http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338" width="80" height="80" alt="avatar"/>cnews</a><br />Tags: <a href="http://www.dailymotion.com/tag/Windows">Windows</a> <a href="http://www.dailymotion.com/tag/Ð½ÐµÑÐ±ÑÐº">Ð½ÐµÑÐ±ÑÐº</a> <a href="http://www.dailymotion.com/tag/Vista">Vista</a> <a href="http://www.dailymotion.com/tag/ÐÐ¡">ÐÐ¡</a> <a href="http://www.dailymotion.com/tag/Microsoft">Microsoft</a> <a href="http://www.dailymotion.com/tag/nVidia">nVidia</a> <a href="http://www.dailymotion.com/tag/Ion">Ion</a> <a href="http://www.dailymotion.com/tag/ÐÐ">ÐÐ</a> <a href="http://www.dailymotion.com/tag/CNewsTV">CNewsTV</a> <a href="http://www.dailymotion.com/tag/high-tech">high-tech</a> <a href="http://www.dailymotion.com/tag/hi-tech">hi-tech</a> <a href="http://www.dailymotion.com/tag/technology">technology</a> <a href="http://www.dailymotion.com/tag/Ð²ÑÑÐ¾ÐºÐ¸Ðµ">Ð²ÑÑÐ¾ÐºÐ¸Ðµ</a> <a href="http://www.dailymotion.com/tag/ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸">ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸</a> <a href="http://www.dailymotion.com/tag/ÐÐ¢">ÐÐ¢</a> <a href="http://www.dailymotion.com/tag/Ð±Ð¸Ð·Ð½ÐµÑ">Ð±Ð¸Ð·Ð½ÐµÑ</a> <br />Posted: 19 February 2009<br />Rating: 0.0<br />Votes: 0<br /></p>]]></description>
            <author>rss@dailymotion.com (cnews)</author>
            <itunes:author>cnews</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>ÐÐµÑÐºÐ»ÑÐ¶Ð°Ñ Vista Ð¿Ð¾Ð´Ð¼Ð¾ÑÐ¸Ð»Ð° ÑÐµÐ¿ÑÑÐ°ÑÐ¸Ñ ÑÐ¾ÑÑÐ²ÐµÑÐ½Ð¾Ð³Ð¾ Ð³Ð¸Ð³Ð°Ð½ÑÐ°. Ð§ÑÐ¾Ð±Ñ ÑÐµÐ°Ð±Ð¸Ð»Ð¸ÑÐ¸ÑÐ¾Ð²Ð°ÑÑÑÑ Ð¿ÐµÑÐµÐ´ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»ÑÐ¼Ð¸ Microsoft Ð³Ð¾ÑÐ¾Ð²Ð¸Ñ Ðº Ð²ÑÐ¿ÑÑÐºÑ Ð½Ð¾Ð²ÑÑ Ð¾Ð¿ÐµÑÐ°ÑÐ¸Ð¾Ð½Ð½ÑÑ ÑÐ¸ÑÑÐµÐ¼Ñ  Windows 7. ÐÐ¾ ÑÑÑÐ¸, ÑÑÐ¾ Ð±ÑÐ»Ð° ÑÐ°Ð±Ð¾ÑÐ° Ð½Ð°Ð´ Ð¾ÑÐ¸Ð±ÐºÐ°Ð¼Ð¸. Ð¡Ð¾Ð·Ð´Ð°ÑÐµÐ»Ð¸ Ð¸ÑÐ¿ÑÐ°Ð²Ð¸Ð»Ð¸ Ð±Ð¾Ð»ÑÑÐ¸Ð½ÑÑÐ²Ð¾ Ð½ÐµÐ´Ð¾ÑÐµÑÐ¾Ð²...</itunes:summary>
            <itunes:subtitle>ÐÐµÑÐºÐ»ÑÐ¶Ð°Ñ Vista Ð¿Ð¾Ð´Ð¼Ð¾ÑÐ¸Ð»Ð° ÑÐµÐ¿ÑÑÐ°ÑÐ¸Ñ ÑÐ¾ÑÑÐ²ÐµÑÐ½Ð¾Ð³Ð¾ Ð³Ð¸Ð³Ð°Ð½ÑÐ°. Ð§ÑÐ¾Ð±Ñ ÑÐµÐ°Ð±Ð¸Ð»Ð¸ÑÐ¸ÑÐ¾Ð²Ð°ÑÑÑÑ Ð¿ÐµÑÐµÐ´ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»ÑÐ¼Ð¸ Microsoft Ð³Ð¾ÑÐ¾Ð²Ð¸Ñ Ðº Ð²ÑÐ¿ÑÑÐºÑ Ð½Ð¾Ð²ÑÑ Ð¾Ð¿ÐµÑÐ°ÑÐ¸Ð¾Ð½Ð½ÑÑ ÑÐ¸ÑÑÐµÐ¼Ñ  Windows 7. ÐÐ¾ ÑÑÑÐ¸, ÑÑÐ¾ Ð±ÑÐ»Ð° ÑÐ°Ð±Ð¾ÑÐ° Ð½Ð°Ð´ Ð¾ÑÐ¸Ð±ÐºÐ°Ð¼Ð¸. Ð¡Ð¾Ð·Ð´Ð°ÑÐµÐ»Ð¸ Ð¸ÑÐ¿ÑÐ°Ð²Ð¸Ð»Ð¸ Ð±Ð¾Ð»ÑÑÐ¸Ð½ÑÑÐ²Ð¾ Ð½ÐµÐ´Ð¾ÑÐµÑÐ¾Ð²...</itunes:subtitle>
            <dm:videorating>0.0</dm:videorating>
            <dm:videovotes>0</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x8ffyu_windows-7-%D1%81%D0%BC%D0%BE%D0%B6%D0%B5%D1%82-%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D1%82%D1%8C-%D0%B4%D0%B0%D0%B6%D0%B5-%D0%BD%D0%B0-%D0%BD_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/cnews" type="application/rss+xml"/>
            <dm:views>1771</dm:views>
            <dm:comments>1</dm:comments>
            <dm:favorites>0</dm:favorites>
            <dm:id>x8ffyu</dm:id>
            <dm:author>cnews</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x8ffyu?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=eivxghr6ff1f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=37357f24a96e41f496b72d76531c1f7d</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Thu, 19 Feb 2009 20:06:21 +0100</pubDate>
            <guid>http://www.dailymotion.com/video/x8ffyu_windows-7-%D1%81%D0%BC%D0%BE%D0%B6%D0%B5%D1%82-%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D1%82%D1%8C-%D0%B4%D0%B0%D0%B6%D0%B5-%D0%BD%D0%B0-%D0%BD_tech</guid>
            <media:title>Windows 7 ÑÐ¼Ð¾Ð¶ÐµÑ ÑÐ°Ð±Ð¾ÑÐ°ÑÑ Ð´Ð°Ð¶Ðµ Ð½Ð° Ð½ÐµÑÐ±ÑÐºÐ°Ñ</media:title>
            <media:credit>cnews</media:credit>
            <media:thumbnail url="http://s2.dmcdn.net/ptkP/x240-zZV.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x8ffyu_windows-7-%D1%81%D0%BC%D0%BE%D0%B6%D0%B5%D1%82-%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D1%82%D1%8C-%D0%B4%D0%B0%D0%B6%D0%B5-%D0%BD%D0%B0-%D0%BD_tech" height="276" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x8ffyu"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x8ffyu" type="text/html" duration="157" width="480" height="276"/>
                <media:content url="http://www.dailymotion.com/swf/video/x8ffyu" type="application/x-shockwave-flash" duration="157" width="480" height="276"/>
            </media:group>
            <itunes:keywords>Windows, Ð½ÐµÑÐ±ÑÐº, Vista, ÐÐ¡, Microsoft, nVidia, Ion, ÐÐ, CNewsTV, high-tech, hi-tech, technology, Ð²ÑÑÐ¾ÐºÐ¸Ðµ, ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸, ÐÐ¢, Ð±Ð¸Ð·Ð½ÐµÑ</itunes:keywords>
            <media:category label="Windows">Windows</media:category>
            <media:category label="Ð½ÐµÑÐ±ÑÐº">Ð½ÐµÑÐ±ÑÐº</media:category>
            <media:category label="Vista">Vista</media:category>
            <media:category label="ÐÐ¡">ÐÐ¡</media:category>
            <media:category label="Microsoft">Microsoft</media:category>
            <media:category label="nVidia">nVidia</media:category>
            <media:category label="Ion">Ion</media:category>
            <media:category label="ÐÐ">ÐÐ</media:category>
            <media:category label="CNewsTV">CNewsTV</media:category>
            <media:category label="high-tech">high-tech</media:category>
            <media:category label="hi-tech">hi-tech</media:category>
            <media:category label="technology">technology</media:category>
            <media:category label="Ð²ÑÑÐ¾ÐºÐ¸Ðµ">Ð²ÑÑÐ¾ÐºÐ¸Ðµ</media:category>
            <media:category label="ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸">ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸</media:category>
            <media:category label="ÐÐ¢">ÐÐ¢</media:category>
            <media:category label="Ð±Ð¸Ð·Ð½ÐµÑ">Ð±Ð¸Ð·Ð½ÐµÑ</media:category>
        </item>
        <item>
            <title>Ð­Ð»ÐµÐºÑÑÐ¾ÑÑÐ°Ð½ÑÐ¸Ñ- Ð³Ð¸Ð³Ð°Ð½Ñ Ð²Ð¾Ð·Ð²ÐµÐ´ÐµÐ½Ð° Ð² ÐÐ½Ð´Ð¸Ð¸</title>
            <link>http://www.dailymotion.com/video/x9cblc_%D1%8D%D0%BB%D0%B5%D0%BA%D1%82%D1%80%D0%BE%D1%81%D1%82%D0%B0%D0%BD%D1%86%D0%B8%D1%8F-%D0%B3%D0%B8%D0%B3%D0%B0%D0%BD%D1%82-%D0%B2%D0%BE%D0%B7%D0%B2%D0%B5%D0%B4%D0%B5%D0%BD%D0%B0-%D0%B2-%D0%B8_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x9cblc_%D1%8D%D0%BB%D0%B5%D0%BA%D1%82%D1%80%D0%BE%D1%81%D1%82%D0%B0%D0%BD%D1%86%D0%B8%D1%8F-%D0%B3%D0%B8%D0%B3%D0%B0%D0%BD%D1%82-%D0%B2%D0%BE%D0%B7%D0%B2%D0%B5%D0%B4%D0%B5%D0%BD%D0%B0-%D0%B2-%D0%B8_tech"><img align="right" width="120" height="90" src="http://s1.dmcdn.net/AciOY/160x90-3pz.jpg" style="border: 2px solid #B9D3FE;"></a><p>Ð­Ð»ÐµÐºÑÑÐ¾ÑÑÐ°Ð½ÑÐ¸Ñ-Ð³Ð¸Ð³Ð°Ð½ Ñ ÑÐ¶Ðµ Ð¿Ð¾ÑÑÑÐ¾ÐµÐ½Ð° Ð¸ Ð³Ð¾ÑÐ¾Ð²Ð° Ðº ÑÐºÑÐ¿Ð»ÑÐ°ÑÐ°ÑÐ¸Ð¸ Ð² Ð¸Ð½Ð´Ð¸Ð¹ÑÐºÐ¾Ð¼ ÑÑÐ°ÑÐµ ÐÐ°Ð¿Ð°Ð´Ð½ÑÐ¹ ÐÑÐ´Ð¶Ð°ÑÐ°Ñ. ÐÐ½Ð° ÑÑÐ°Ð½ÐµÑ ÑÐ°Ð¼ÑÐ¼ Ð±Ð¾Ð»ÑÑÐ¸Ð¼ Ð¸ÑÑÐ¾ÑÐ½Ð¸ÐºÐ¾Ð¼ ÑÐµÐ¿Ð»Ð¾Ð²Ð¾Ð¹ ÑÐ½ÐµÑÐ³Ð¸Ð¸ Ð² ÑÑÑÐ°Ð½Ðµ</p><p>Author: <a href="http://www.dailymotion.com/RussianNTD"><img src="http://static2.dmcdn.net/static/user/473/499/23994374:avatar_medium.jpg?20110513130152" width="80" height="80" alt="avatar"/>RussianNTD</a><br />Tags: <a href="http://www.dailymotion.com/tag/Ð¸ÑÑÐ¾ÑÐ½Ð¸Ðº">Ð¸ÑÑÐ¾ÑÐ½Ð¸Ðº</a> <a href="http://www.dailymotion.com/tag/Ð¸Ð½Ð´Ð¸Ñ">Ð¸Ð½Ð´Ð¸Ñ</a> <a href="http://www.dailymotion.com/tag/ntd">ntd</a> <a href="http://www.dailymotion.com/tag/new">new</a> <a href="http://www.dailymotion.com/tag/tang">tang</a> <a href="http://www.dailymotion.com/tag/dynasty">dynasty</a> <a href="http://www.dailymotion.com/tag/Ð·Ð°Ð¿Ð°Ð´Ð½ÑÐ¹">Ð·Ð°Ð¿Ð°Ð´Ð½ÑÐ¹</a> <a href="http://www.dailymotion.com/tag/Ð³ÑÐ´Ð¶Ð°ÑÐ°Ñ">Ð³ÑÐ´Ð¶Ð°ÑÐ°Ñ</a> <a href="http://www.dailymotion.com/tag/ÑÐµÐ¿Ð»Ð¾Ð²Ð°Ñ">ÑÐµÐ¿Ð»Ð¾Ð²Ð°Ñ</a> <a href="http://www.dailymotion.com/tag/ÑÐ½ÐµÑÐ³Ð¸Ñ">ÑÐ½ÐµÑÐ³Ð¸Ñ</a> <a href="http://www.dailymotion.com/tag/ÑÐ»ÐµÐºÑÑÐ¾ÑÑÐ°Ð½ÑÐ¸Ñ-Ð³Ð¸Ð³Ð°Ð½Ñ">ÑÐ»ÐµÐºÑÑÐ¾ÑÑÐ°Ð½ÑÐ¸Ñ-Ð³Ð¸Ð³Ð°Ð½Ñ</a> <a href="http://www.dailymotion.com/tag/ntdtv">ntdtv</a> <br />Posted: 20 May 2009<br />Rating: 5.0<br />Votes: 1<br /></p>]]></description>
            <author>rss@dailymotion.com (RussianNTD)</author>
            <itunes:author>RussianNTD</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>Ð­Ð»ÐµÐºÑÑÐ¾ÑÑÐ°Ð½ÑÐ¸Ñ-Ð³Ð¸Ð³Ð°Ð½ Ñ ÑÐ¶Ðµ Ð¿Ð¾ÑÑÑÐ¾ÐµÐ½Ð° Ð¸ Ð³Ð¾ÑÐ¾Ð²Ð° Ðº ÑÐºÑÐ¿Ð»ÑÐ°ÑÐ°ÑÐ¸Ð¸ Ð² Ð¸Ð½Ð´Ð¸Ð¹ÑÐºÐ¾Ð¼ ÑÑÐ°ÑÐµ ÐÐ°Ð¿Ð°Ð´Ð½ÑÐ¹ ÐÑÐ´Ð¶Ð°ÑÐ°Ñ. ÐÐ½Ð° ÑÑÐ°Ð½ÐµÑ ÑÐ°Ð¼ÑÐ¼ Ð±Ð¾Ð»ÑÑÐ¸Ð¼ Ð¸ÑÑÐ¾ÑÐ½Ð¸ÐºÐ¾Ð¼ ÑÐµÐ¿Ð»Ð¾Ð²Ð¾Ð¹ ÑÐ½ÐµÑÐ³Ð¸Ð¸ Ð² ÑÑÑÐ°Ð½Ðµ</itunes:summary>
            <itunes:subtitle>Ð­Ð»ÐµÐºÑÑÐ¾ÑÑÐ°Ð½ÑÐ¸Ñ-Ð³Ð¸Ð³Ð°Ð½ Ñ ÑÐ¶Ðµ Ð¿Ð¾ÑÑÑÐ¾ÐµÐ½Ð° Ð¸ Ð³Ð¾ÑÐ¾Ð²Ð° Ðº ÑÐºÑÐ¿Ð»ÑÐ°ÑÐ°ÑÐ¸Ð¸ Ð² Ð¸Ð½Ð´Ð¸Ð¹ÑÐºÐ¾Ð¼ ÑÑÐ°ÑÐµ ÐÐ°Ð¿Ð°Ð´Ð½ÑÐ¹ ÐÑÐ´Ð¶Ð°ÑÐ°Ñ. ÐÐ½Ð° ÑÑÐ°Ð½ÐµÑ ÑÐ°Ð¼ÑÐ¼ Ð±Ð¾Ð»ÑÑÐ¸Ð¼ Ð¸ÑÑÐ¾ÑÐ½Ð¸ÐºÐ¾Ð¼ ÑÐµÐ¿Ð»Ð¾Ð²Ð¾Ð¹ ÑÐ½ÐµÑÐ³Ð¸Ð¸ Ð² ÑÑÑÐ°Ð½Ðµ</itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>1</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x9cblc_%D1%8D%D0%BB%D0%B5%D0%BA%D1%82%D1%80%D0%BE%D1%81%D1%82%D0%B0%D0%BD%D1%86%D0%B8%D1%8F-%D0%B3%D0%B8%D0%B3%D0%B0%D0%BD%D1%82-%D0%B2%D0%BE%D0%B7%D0%B2%D0%B5%D0%B4%D0%B5%D0%BD%D0%B0-%D0%B2-%D0%B8_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/RussianNTD" type="application/rss+xml"/>
            <dm:views>675</dm:views>
            <dm:comments>1</dm:comments>
            <dm:favorites>0</dm:favorites>
            <dm:id>x9cblc</dm:id>
            <dm:author>RussianNTD</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x9cblc?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=cgra877o8t1f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=39c165059a93d49a56a5adbf65e313ce</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/473/499/23994374:avatar_medium.jpg?20110513130152</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Wed, 20 May 2009 10:53:29 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x9cblc_%D1%8D%D0%BB%D0%B5%D0%BA%D1%82%D1%80%D0%BE%D1%81%D1%82%D0%B0%D0%BD%D1%86%D0%B8%D1%8F-%D0%B3%D0%B8%D0%B3%D0%B0%D0%BD%D1%82-%D0%B2%D0%BE%D0%B7%D0%B2%D0%B5%D0%B4%D0%B5%D0%BD%D0%B0-%D0%B2-%D0%B8_tech</guid>
            <media:title>Ð­Ð»ÐµÐºÑÑÐ¾ÑÑÐ°Ð½ÑÐ¸Ñ- Ð³Ð¸Ð³Ð°Ð½Ñ Ð²Ð¾Ð·Ð²ÐµÐ´ÐµÐ½Ð° Ð² ÐÐ½Ð´Ð¸Ð¸</media:title>
            <media:credit>RussianNTD</media:credit>
            <media:thumbnail url="http://s1.dmcdn.net/AciOY/x240-bwv.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x9cblc_%D1%8D%D0%BB%D0%B5%D0%BA%D1%82%D1%80%D0%BE%D1%81%D1%82%D0%B0%D0%BD%D1%86%D0%B8%D1%8F-%D0%B3%D0%B8%D0%B3%D0%B0%D0%BD%D1%82-%D0%B2%D0%BE%D0%B7%D0%B2%D0%B5%D0%B4%D0%B5%D0%BD%D0%B0-%D0%B2-%D0%B8_tech" height="360" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x9cblc"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x9cblc" type="text/html" duration="35" width="480" height="360"/>
                <media:content url="http://www.dailymotion.com/swf/video/x9cblc" type="application/x-shockwave-flash" duration="35" width="480" height="360"/>
            </media:group>
            <itunes:keywords>Ð¸ÑÑÐ¾ÑÐ½Ð¸Ðº, Ð¸Ð½Ð´Ð¸Ñ, ntd, new, tang, dynasty, Ð·Ð°Ð¿Ð°Ð´Ð½ÑÐ¹, Ð³ÑÐ´Ð¶Ð°ÑÐ°Ñ, ÑÐµÐ¿Ð»Ð¾Ð²Ð°Ñ, ÑÐ½ÐµÑÐ³Ð¸Ñ, ÑÐ»ÐµÐºÑÑÐ¾ÑÑÐ°Ð½ÑÐ¸Ñ-Ð³Ð¸Ð³Ð°Ð½Ñ, ntdtv</itunes:keywords>
            <media:category label="Ð¸ÑÑÐ¾ÑÐ½Ð¸Ðº">Ð¸ÑÑÐ¾ÑÐ½Ð¸Ðº</media:category>
            <media:category label="Ð¸Ð½Ð´Ð¸Ñ">Ð¸Ð½Ð´Ð¸Ñ</media:category>
            <media:category label="ntd">ntd</media:category>
            <media:category label="new">new</media:category>
            <media:category label="tang">tang</media:category>
            <media:category label="dynasty">dynasty</media:category>
            <media:category label="Ð·Ð°Ð¿Ð°Ð´Ð½ÑÐ¹">Ð·Ð°Ð¿Ð°Ð´Ð½ÑÐ¹</media:category>
            <media:category label="Ð³ÑÐ´Ð¶Ð°ÑÐ°Ñ">Ð³ÑÐ´Ð¶Ð°ÑÐ°Ñ</media:category>
            <media:category label="ÑÐµÐ¿Ð»Ð¾Ð²Ð°Ñ">ÑÐµÐ¿Ð»Ð¾Ð²Ð°Ñ</media:category>
            <media:category label="ÑÐ½ÐµÑÐ³Ð¸Ñ">ÑÐ½ÐµÑÐ³Ð¸Ñ</media:category>
            <media:category label="ÑÐ»ÐµÐºÑÑÐ¾ÑÑÐ°Ð½ÑÐ¸Ñ-Ð³Ð¸Ð³Ð°Ð½Ñ">ÑÐ»ÐµÐºÑÑÐ¾ÑÑÐ°Ð½ÑÐ¸Ñ-Ð³Ð¸Ð³Ð°Ð½Ñ</media:category>
            <media:category label="ntdtv">ntdtv</media:category>
        </item>
        <item>
            <title>ÐÐµÑÐ±Ð¸Ð²Ð°ÐµÐ¼ÑÐ¹ Ð¼Ð¾Ð½Ð¸ÑÐ¾Ñ ASUS LS201</title>
            <link>http://www.dailymotion.com/video/x6cqtd_%D0%BD%D0%B5%D1%83%D0%B1%D0%B8%D0%B2%D0%B0%D0%B5%D0%BC%D1%8B%D0%B9-%D0%BC%D0%BE%D0%BD%D0%B8%D1%82%D0%BE%D1%80-asus-ls201_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x6cqtd_%D0%BD%D0%B5%D1%83%D0%B1%D0%B8%D0%B2%D0%B0%D0%B5%D0%BC%D1%8B%D0%B9-%D0%BC%D0%BE%D0%BD%D0%B8%D1%82%D0%BE%D1%80-asus-ls201_tech"><img align="right" width="120" height="90" src="http://s1.dmcdn.net/95uv/160x90-eZm.jpg" style="border: 2px solid #B9D3FE;"></a><p>ÐÑ ÐºÐ¾Ð³Ð´Ð°-Ð½Ð¸Ð±ÑÐ´Ñ Ð¿ÑÐ¾Ð±Ð¾Ð²Ð°Ð»Ð¸ Ð±Ð¸ÑÑ Ð¼Ð¾Ð»Ð¾ÑÐºÐ¾Ð¼ Ð¿Ð¾ ÑÑÐµÐºÐ»Ñ Ð¼Ð¾Ð½Ð¸ÑÐ¾ÑÐ°? Ð Ð¼Ñ Ð¿Ð¾Ð¿ÑÐ¾Ð±Ð¾Ð²Ð°Ð»Ð¸! Ð ÐµÐ·ÑÐ»ÑÑÐ°ÑÑ - Ð½Ð° Ð²Ð¸Ð´ÐµÐ¾.</p><p>Author: <a href="http://www.dailymotion.com/cnews"><img src="http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338" width="80" height="80" alt="avatar"/>cnews</a><br />Tags: <a href="http://www.dailymotion.com/tag/Ð¼Ð¾Ð½Ð¸ÑÐ¾Ñ">Ð¼Ð¾Ð½Ð¸ÑÐ¾Ñ</a> <a href="http://www.dailymotion.com/tag/asus">asus</a> <a href="http://www.dailymotion.com/tag/ÑÐµÑÑ">ÑÐµÑÑ</a> <a href="http://www.dailymotion.com/tag/zoom.cnews">zoom.cnews</a> <a href="http://www.dailymotion.com/tag/Ð¾Ð±Ð·Ð¾Ñ">Ð¾Ð±Ð·Ð¾Ñ</a> <a href="http://www.dailymotion.com/tag/ÑÐ»ÐµÐºÑÑÐ¾Ð½Ð¸ÐºÐ°">ÑÐ»ÐµÐºÑÑÐ¾Ð½Ð¸ÐºÐ°</a> <a href="http://www.dailymotion.com/tag/cnewstv">cnewstv</a> <a href="http://www.dailymotion.com/tag/high-tech">high-tech</a> <a href="http://www.dailymotion.com/tag/hi-tech">hi-tech</a> <a href="http://www.dailymotion.com/tag/technology">technology</a> <a href="http://www.dailymotion.com/tag/Ð²ÑÑÐ¾ÐºÐ¸Ðµ">Ð²ÑÑÐ¾ÐºÐ¸Ðµ</a> <a href="http://www.dailymotion.com/tag/ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸">ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸</a> <a href="http://www.dailymotion.com/tag/Ð¸Ñ">Ð¸Ñ</a> <br />Posted: 05 August 2008<br />Rating: 2.7<br />Votes: 3<br /></p>]]></description>
            <author>rss@dailymotion.com (cnews)</author>
            <itunes:author>cnews</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>ÐÑ ÐºÐ¾Ð³Ð´Ð°-Ð½Ð¸Ð±ÑÐ´Ñ Ð¿ÑÐ¾Ð±Ð¾Ð²Ð°Ð»Ð¸ Ð±Ð¸ÑÑ Ð¼Ð¾Ð»Ð¾ÑÐºÐ¾Ð¼ Ð¿Ð¾ ÑÑÐµÐºÐ»Ñ Ð¼Ð¾Ð½Ð¸ÑÐ¾ÑÐ°? Ð Ð¼Ñ Ð¿Ð¾Ð¿ÑÐ¾Ð±Ð¾Ð²Ð°Ð»Ð¸! Ð ÐµÐ·ÑÐ»ÑÑÐ°ÑÑ - Ð½Ð° Ð²Ð¸Ð´ÐµÐ¾.</itunes:summary>
            <itunes:subtitle>ÐÑ ÐºÐ¾Ð³Ð´Ð°-Ð½Ð¸Ð±ÑÐ´Ñ Ð¿ÑÐ¾Ð±Ð¾Ð²Ð°Ð»Ð¸ Ð±Ð¸ÑÑ Ð¼Ð¾Ð»Ð¾ÑÐºÐ¾Ð¼ Ð¿Ð¾ ÑÑÐµÐºÐ»Ñ Ð¼Ð¾Ð½Ð¸ÑÐ¾ÑÐ°? Ð Ð¼Ñ Ð¿Ð¾Ð¿ÑÐ¾Ð±Ð¾Ð²Ð°Ð»Ð¸! Ð ÐµÐ·ÑÐ»ÑÑÐ°ÑÑ - Ð½Ð° Ð²Ð¸Ð´ÐµÐ¾.</itunes:subtitle>
            <dm:videorating>2.7</dm:videorating>
            <dm:videovotes>3</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x6cqtd_%D0%BD%D0%B5%D1%83%D0%B1%D0%B8%D0%B2%D0%B0%D0%B5%D0%BC%D1%8B%D0%B9-%D0%BC%D0%BE%D0%BD%D0%B8%D1%82%D0%BE%D1%80-asus-ls201_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/cnews" type="application/rss+xml"/>
            <dm:views>1949</dm:views>
            <dm:comments>5</dm:comments>
            <dm:favorites>0</dm:favorites>
            <dm:id>x6cqtd</dm:id>
            <dm:author>cnews</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x6cqtd?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=3foktkp5qi1f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=857aca340cff4f1f381b0b79192c73e5</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338</dm:authorAvatar>
            <dm:relativeDate>posted 5 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Tue, 05 Aug 2008 20:38:16 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x6cqtd_%D0%BD%D0%B5%D1%83%D0%B1%D0%B8%D0%B2%D0%B0%D0%B5%D0%BC%D1%8B%D0%B9-%D0%BC%D0%BE%D0%BD%D0%B8%D1%82%D0%BE%D1%80-asus-ls201_tech</guid>
            <media:title>ÐÐµÑÐ±Ð¸Ð²Ð°ÐµÐ¼ÑÐ¹ Ð¼Ð¾Ð½Ð¸ÑÐ¾Ñ ASUS LS201</media:title>
            <media:credit>cnews</media:credit>
            <media:thumbnail url="http://s1.dmcdn.net/95uv/x240-nAT.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x6cqtd_%D0%BD%D0%B5%D1%83%D0%B1%D0%B8%D0%B2%D0%B0%D0%B5%D0%BC%D1%8B%D0%B9-%D0%BC%D0%BE%D0%BD%D0%B8%D1%82%D0%BE%D1%80-asus-ls201_tech" height="276" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x6cqtd"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x6cqtd" type="text/html" duration="71" width="480" height="276"/>
                <media:content url="http://www.dailymotion.com/swf/video/x6cqtd" type="application/x-shockwave-flash" duration="71" width="480" height="276"/>
            </media:group>
            <itunes:keywords>Ð¼Ð¾Ð½Ð¸ÑÐ¾Ñ, asus, ÑÐµÑÑ, zoom.cnews, Ð¾Ð±Ð·Ð¾Ñ, ÑÐ»ÐµÐºÑÑÐ¾Ð½Ð¸ÐºÐ°, cnewstv, high-tech, hi-tech, technology, Ð²ÑÑÐ¾ÐºÐ¸Ðµ, ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸, Ð¸Ñ</itunes:keywords>
            <media:category label="Ð¼Ð¾Ð½Ð¸ÑÐ¾Ñ">Ð¼Ð¾Ð½Ð¸ÑÐ¾Ñ</media:category>
            <media:category label="asus">asus</media:category>
            <media:category label="ÑÐµÑÑ">ÑÐµÑÑ</media:category>
            <media:category label="zoom.cnews">zoom.cnews</media:category>
            <media:category label="Ð¾Ð±Ð·Ð¾Ñ">Ð¾Ð±Ð·Ð¾Ñ</media:category>
            <media:category label="ÑÐ»ÐµÐºÑÑÐ¾Ð½Ð¸ÐºÐ°">ÑÐ»ÐµÐºÑÑÐ¾Ð½Ð¸ÐºÐ°</media:category>
            <media:category label="cnewstv">cnewstv</media:category>
            <media:category label="high-tech">high-tech</media:category>
            <media:category label="hi-tech">hi-tech</media:category>
            <media:category label="technology">technology</media:category>
            <media:category label="Ð²ÑÑÐ¾ÐºÐ¸Ðµ">Ð²ÑÑÐ¾ÐºÐ¸Ðµ</media:category>
            <media:category label="ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸">ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸</media:category>
            <media:category label="Ð¸Ñ">Ð¸Ñ</media:category>
        </item>
        <item>
            <title>Ð£ÐºÑÐ°Ð¸Ð½ÑÐºÐ¸Ð¹ IT-ÑÑÐ½Ð¾Ðº Ð¸Ð½ÑÐµÑÐµÑÐµÐ½ Ð´Ð»Ñ Ð¸Ð½Ð²ÐµÑÑÐ¾ÑÐ¾Ð²</title>
            <link>http://www.dailymotion.com/video/x97m46_%D1%83%D0%BA%D1%80%D0%B0%D0%B8%D0%BD%D1%81%D0%BA%D0%B8%D0%B9-it-%D1%80%D1%8B%D0%BD%D0%BE%D0%BA-%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D0%B5%D1%81%D0%B5%D0%BD-%D0%B4%D0%BB%D1%8F-%D0%B8_news</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x97m46_%D1%83%D0%BA%D1%80%D0%B0%D0%B8%D0%BD%D1%81%D0%BA%D0%B8%D0%B9-it-%D1%80%D1%8B%D0%BD%D0%BE%D0%BA-%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D0%B5%D1%81%D0%B5%D0%BD-%D0%B4%D0%BB%D1%8F-%D0%B8_news"><img align="right" width="120" height="90" src="http://s2.dmcdn.net/Arquv/160x90-UqI.jpg" style="border: 2px solid #B9D3FE;"></a><p>Ð Ð°Ð½Ð¾ Ð¸Ð»Ð¸ Ð¿Ð¾Ð·Ð´Ð½Ð¾ ÐÐ½ÑÐµÑÐ½ÐµÑÐ¾Ð¼ Ð±ÑÐ´ÑÑ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÑÑÑ Ð²ÑÐµ. ÐÑÐ¸Ð¼ÐµÑÐ½Ð¾ ÑÐ°Ðº Ð¶Ðµ, ÐºÐ°Ðº Ð¼Ð¾Ð±Ð¸Ð»ÑÐ½ÑÐ¼Ð¸.  <br>ÐÐ½Ð°ÑÐ¸Ñ, ÑÑÐ½Ð¾Ðº Ð²ÑÑÐ°ÑÑÐµÑ, Ð° ÑÐ°ÑÑÑÑÐ¸Ð¹ ÑÑÐ½Ð¾Ðº â ÑÑÐ¾ ÑÐ¾, ÑÑÐ¾ Ð¸Ð½ÑÐµÑÐµÑÑÐµÑ Ð»ÑÐ±Ð¾Ð³Ð¾ Ð²ÐµÐ½ÑÑÑÐ½Ð¾Ð³Ð¾ Ð¸Ð½Ð²ÐµÑÑÐ¾ÑÐ°. ÐÐ½ ÑÐ¾ÑÐµÑ ÑÐ°Ð±Ð¾ÑÐ°ÑÑ Ð½Ð° Ð·Ð°ÑÐ¾Ð¶Ð´Ð°ÑÑÐµÐ¼ÑÑ ÑÑÐ½ÐºÐµ, Ð²ÐµÐ´Ñ ÑÐ°ÐºÐ¸Ð¼ Ð¾Ð±ÑÐ°Ð·Ð¾Ð¼ Ð¼Ð¾Ð¶Ð½Ð¾ Ð¿ÑÐ¾Ð¸Ð½Ð²ÐµÑÑÐ¸ÑÐ¾Ð²Ð°ÑÑ ÐºÐ¾Ð¼Ð¿Ð°Ð½Ð¸Ñ, ÐºÐ¾ÑÐ¾ÑÐ°Ñ Ð¿Ð¾ÑÐ¾Ð¼ ÑÑÐ°Ð½ÐµÑ Ð¸Ð·Ð²ÐµÑÑÐ½Ð¾Ð¹ Ð½Ð° ÑÑÐ½ÐºÐµ, ÑÐ¶Ðµ ÑÑÐ¾ÑÐ¼Ð¸ÑÐ¾Ð²Ð°Ð½Ð½Ð¾Ð¼. ÐÐ°Ñ IT Ð¸ Ð¸Ð½ÑÐµÑÐ½ÐµÑ-ÑÑÐ½Ð¾Ðº Ð½Ð°ÑÐ¾Ð´ÑÑÑÑ Ð½Ð° ÑÐ°Ð½Ð½ÐµÐ¹ ÑÑÐ°Ð´Ð¸Ð¸ ÑÐ°Ð·Ð²Ð¸ÑÐ¸Ñ, Ð° Ð·Ð½Ð°ÑÐ¸Ñ, Ð¾Ð½Ð¸ Ð¸Ð½ÑÐµÑÐµÑÐ½Ñ Ð´Ð»Ñ Ð²ÐµÐ½ÑÑÑÐ½ÑÑ Ð¸Ð½Ð²ÐµÑÑÐ¾ÑÐ¾Ð², ÐºÐ¾ÑÐ¾ÑÑÐµ Ð²ÐºÐ»Ð°Ð´ÑÐ²Ð°ÑÑ "ÑÐ¼Ð½ÑÐµ" Ð´ÐµÐ½ÑÐ³Ð¸ Ð¸ ÑÐ°ÑÑÑÐ¸ÑÑÐ²Ð°ÑÑ Ð½Ð° ÑÐ¾ÑÑ Ð² Ð±Ð»Ð¸Ð¶Ð°Ð¹ÑÐ¸Ðµ 3-5 Ð»ÐµÑ.  <br></p><p>Author: <a href="http://www.dailymotion.com/Openbiz"><img src="http://static1.dmcdn.net/images/avatar/female/80x80.jpg.v69eb35393aa934cb9" width="80" height="80" alt="avatar"/>Openbiz</a><br />Tags: <a href="http://www.dailymotion.com/tag/ÑÐ²ÑÐ·Ñ">ÑÐ²ÑÐ·Ñ</a> <a href="http://www.dailymotion.com/tag/ÐÐ½ÑÐµÑÐ½ÐµÑ">ÐÐ½ÑÐµÑÐ½ÐµÑ</a> <a href="http://www.dailymotion.com/tag/Ð¸Ð½Ð²ÐµÑÑÐ¸ÑÐ¸Ð¸">Ð¸Ð½Ð²ÐµÑÑÐ¸ÑÐ¸Ð¸</a> <a href="http://www.dailymotion.com/tag/ÑÐºÑÐ°Ð¸Ð½Ð°">ÑÐºÑÐ°Ð¸Ð½Ð°</a> <a href="http://www.dailymotion.com/tag/Ð±Ð¸Ð·Ð½ÐµÑ">Ð±Ð¸Ð·Ð½ÐµÑ</a> <a href="http://www.dailymotion.com/tag/openbiz">openbiz</a> <a href="http://www.dailymotion.com/tag/openbizcomua">openbizcomua</a> <a href="http://www.dailymotion.com/tag/ukraine">ukraine</a> <br />Posted: 07 May 2009<br />Rating: 5.0<br />Votes: 1<br /></p>]]></description>
            <author>rss@dailymotion.com (Openbiz)</author>
            <itunes:author>Openbiz</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>Ð Ð°Ð½Ð¾ Ð¸Ð»Ð¸ Ð¿Ð¾Ð·Ð´Ð½Ð¾ ÐÐ½ÑÐµÑÐ½ÐµÑÐ¾Ð¼ Ð±ÑÐ´ÑÑ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÑÑÑ Ð²ÑÐµ. ÐÑÐ¸Ð¼ÐµÑÐ½Ð¾ ÑÐ°Ðº Ð¶Ðµ, ÐºÐ°Ðº Ð¼Ð¾Ð±Ð¸Ð»ÑÐ½ÑÐ¼Ð¸.  ÐÐ½Ð°ÑÐ¸Ñ, ÑÑÐ½Ð¾Ðº Ð²ÑÑÐ°ÑÑÐµÑ, Ð° ÑÐ°ÑÑÑÑÐ¸Ð¹ ÑÑÐ½Ð¾Ðº â ÑÑÐ¾ ÑÐ¾, ÑÑÐ¾ Ð¸Ð½ÑÐµÑÐµÑÑÐµÑ Ð»ÑÐ±Ð¾Ð³Ð¾ Ð²ÐµÐ½ÑÑÑÐ½Ð¾Ð³Ð¾ Ð¸Ð½Ð²ÐµÑÑÐ¾ÑÐ°. ÐÐ½ ÑÐ¾ÑÐµÑ ÑÐ°Ð±Ð¾ÑÐ°ÑÑ Ð½Ð° Ð·Ð°ÑÐ¾Ð¶Ð´Ð°ÑÑÐµÐ¼ÑÑ ÑÑÐ½ÐºÐµ, Ð²ÐµÐ´Ñ ÑÐ°ÐºÐ¸Ð¼ Ð¾Ð±ÑÐ°Ð·Ð¾Ð¼ Ð¼Ð¾Ð¶Ð½Ð¾...</itunes:summary>
            <itunes:subtitle>Ð Ð°Ð½Ð¾ Ð¸Ð»Ð¸ Ð¿Ð¾Ð·Ð´Ð½Ð¾ ÐÐ½ÑÐµÑÐ½ÐµÑÐ¾Ð¼ Ð±ÑÐ´ÑÑ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÑÑÑ Ð²ÑÐµ. ÐÑÐ¸Ð¼ÐµÑÐ½Ð¾ ÑÐ°Ðº Ð¶Ðµ, ÐºÐ°Ðº Ð¼Ð¾Ð±Ð¸Ð»ÑÐ½ÑÐ¼Ð¸.  ÐÐ½Ð°ÑÐ¸Ñ, ÑÑÐ½Ð¾Ðº Ð²ÑÑÐ°ÑÑÐµÑ, Ð° ÑÐ°ÑÑÑÑÐ¸Ð¹ ÑÑÐ½Ð¾Ðº â ÑÑÐ¾ ÑÐ¾, ÑÑÐ¾ Ð¸Ð½ÑÐµÑÐµÑÑÐµÑ Ð»ÑÐ±Ð¾Ð³Ð¾ Ð²ÐµÐ½ÑÑÑÐ½Ð¾Ð³Ð¾ Ð¸Ð½Ð²ÐµÑÑÐ¾ÑÐ°. ÐÐ½ ÑÐ¾ÑÐµÑ ÑÐ°Ð±Ð¾ÑÐ°ÑÑ Ð½Ð° Ð·Ð°ÑÐ¾Ð¶Ð´Ð°ÑÑÐµÐ¼ÑÑ ÑÑÐ½ÐºÐµ, Ð²ÐµÐ´Ñ ÑÐ°ÐºÐ¸Ð¼ Ð¾Ð±ÑÐ°Ð·Ð¾Ð¼ Ð¼Ð¾Ð¶Ð½Ð¾...</itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>1</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x97m46_%D1%83%D0%BA%D1%80%D0%B0%D0%B8%D0%BD%D1%81%D0%BA%D0%B8%D0%B9-it-%D1%80%D1%8B%D0%BD%D0%BE%D0%BA-%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D0%B5%D1%81%D0%B5%D0%BD-%D0%B4%D0%BB%D1%8F-%D0%B8_news" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/Openbiz" type="application/rss+xml"/>
            <dm:views>403</dm:views>
            <dm:comments>0</dm:comments>
            <dm:favorites>0</dm:favorites>
            <dm:id>x97m46</dm:id>
            <dm:author>Openbiz</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x97m46?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=eq3rumn4f31f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=c0fa86efac26bd11934c3fdb61762f74</dm:loggerURL>
            <dm:authorAvatar>http://static1.dmcdn.net/images/avatar/female/80x80.jpg.v69eb35393aa934cb9</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>news</dm:channels>
            <pubDate>Thu, 07 May 2009 10:32:48 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x97m46_%D1%83%D0%BA%D1%80%D0%B0%D0%B8%D0%BD%D1%81%D0%BA%D0%B8%D0%B9-it-%D1%80%D1%8B%D0%BD%D0%BE%D0%BA-%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D0%B5%D1%81%D0%B5%D0%BD-%D0%B4%D0%BB%D1%8F-%D0%B8_news</guid>
            <media:title>Ð£ÐºÑÐ°Ð¸Ð½ÑÐºÐ¸Ð¹ IT-ÑÑÐ½Ð¾Ðº Ð¸Ð½ÑÐµÑÐµÑÐµÐ½ Ð´Ð»Ñ Ð¸Ð½Ð²ÐµÑÑÐ¾ÑÐ¾Ð²</media:title>
            <media:credit>Openbiz</media:credit>
            <media:thumbnail url="http://s2.dmcdn.net/Arquv/x240-Cs1.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x97m46_%D1%83%D0%BA%D1%80%D0%B0%D0%B8%D0%BD%D1%81%D0%BA%D0%B8%D0%B9-it-%D1%80%D1%8B%D0%BD%D0%BE%D0%BA-%D0%B8%D0%BD%D1%82%D0%B5%D1%80%D0%B5%D1%81%D0%B5%D0%BD-%D0%B4%D0%BB%D1%8F-%D0%B8_news" height="276" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x97m46"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x97m46" type="text/html" duration="63" width="480" height="276"/>
                <media:content url="http://www.dailymotion.com/swf/video/x97m46" type="application/x-shockwave-flash" duration="63" width="480" height="276"/>
            </media:group>
            <itunes:keywords>ÑÐ²ÑÐ·Ñ, ÐÐ½ÑÐµÑÐ½ÐµÑ, Ð¸Ð½Ð²ÐµÑÑÐ¸ÑÐ¸Ð¸, ÑÐºÑÐ°Ð¸Ð½Ð°, Ð±Ð¸Ð·Ð½ÐµÑ, openbiz, openbizcomua, ukraine</itunes:keywords>
            <media:category label="ÑÐ²ÑÐ·Ñ">ÑÐ²ÑÐ·Ñ</media:category>
            <media:category label="ÐÐ½ÑÐµÑÐ½ÐµÑ">ÐÐ½ÑÐµÑÐ½ÐµÑ</media:category>
            <media:category label="Ð¸Ð½Ð²ÐµÑÑÐ¸ÑÐ¸Ð¸">Ð¸Ð½Ð²ÐµÑÑÐ¸ÑÐ¸Ð¸</media:category>
            <media:category label="ÑÐºÑÐ°Ð¸Ð½Ð°">ÑÐºÑÐ°Ð¸Ð½Ð°</media:category>
            <media:category label="Ð±Ð¸Ð·Ð½ÐµÑ">Ð±Ð¸Ð·Ð½ÐµÑ</media:category>
            <media:category label="openbiz">openbiz</media:category>
            <media:category label="openbizcomua">openbizcomua</media:category>
            <media:category label="ukraine">ukraine</media:category>
        </item>
        <item>
            <title>ÐÑÑÐ¾ÐºÐ¸Ðµ ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸ Ð´Ð»Ñ ÐºÐ»Ð°Ð´Ð¾Ð¸ÑÐºÐ°ÑÐµÐ»ÐµÐ¹</title>
            <link>http://www.dailymotion.com/video/x94n4j_%D0%B2%D1%8B%D1%81%D0%BE%D0%BA%D0%B8%D0%B5-%D1%82%D0%B5%D1%85%D0%BD%D0%BE%D0%BB%D0%BE%D0%B3%D0%B8%D0%B8-%D0%B4%D0%BB%D1%8F-%D0%BA%D0%BB%D0%B0%D0%B4%D0%BE%D0%B8%D1%81%D0%BA%D0%B0%D1%82%D0%B5%D0%BB_news</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x94n4j_%D0%B2%D1%8B%D1%81%D0%BE%D0%BA%D0%B8%D0%B5-%D1%82%D0%B5%D1%85%D0%BD%D0%BE%D0%BB%D0%BE%D0%B3%D0%B8%D0%B8-%D0%B4%D0%BB%D1%8F-%D0%BA%D0%BB%D0%B0%D0%B4%D0%BE%D0%B8%D1%81%D0%BA%D0%B0%D1%82%D0%B5%D0%BB_news"><img align="right" width="120" height="90" src="http://s2.dmcdn.net/jf2-/160x90-Qke.jpg" style="border: 2px solid #B9D3FE;"></a><p></p><p>Author: <a href="http://www.dailymotion.com/Vedomosti"><img src="http://static2.dmcdn.net/static/user/556/540/27045655:avatar_medium.jpg?20090411112150" width="80" height="80" alt="avatar"/>Vedomosti</a><br />Tags: <a href="http://www.dailymotion.com/tag/ÐºÐ»Ð°Ð´">ÐºÐ»Ð°Ð´</a> <a href="http://www.dailymotion.com/tag/ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸">ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸</a> <a href="http://www.dailymotion.com/tag/ÐÐ¸Ð²ÐµÑÐ³Ð°Ð½Ñ">ÐÐ¸Ð²ÐµÑÐ³Ð°Ð½Ñ</a> <a href="http://www.dailymotion.com/tag/Ð³Ð°Ð·ÐµÑÐ°">Ð³Ð°Ð·ÐµÑÐ°</a> <a href="http://www.dailymotion.com/tag/ÐÐµÐ´Ð¾Ð¼Ð¾ÑÑÐ¸">ÐÐµÐ´Ð¾Ð¼Ð¾ÑÑÐ¸</a> <br />Posted: 29 April 2009<br />Rating: 5.0<br />Votes: 1<br /></p>]]></description>
            <author>rss@dailymotion.com (Vedomosti)</author>
            <itunes:author>Vedomosti</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary></itunes:summary>
            <itunes:subtitle></itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>1</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x94n4j_%D0%B2%D1%8B%D1%81%D0%BE%D0%BA%D0%B8%D0%B5-%D1%82%D0%B5%D1%85%D0%BD%D0%BE%D0%BB%D0%BE%D0%B3%D0%B8%D0%B8-%D0%B4%D0%BB%D1%8F-%D0%BA%D0%BB%D0%B0%D0%B4%D0%BE%D0%B8%D1%81%D0%BA%D0%B0%D1%82%D0%B5%D0%BB_news" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/Vedomosti" type="application/rss+xml"/>
            <dm:views>455</dm:views>
            <dm:comments>0</dm:comments>
            <dm:favorites>1</dm:favorites>
            <dm:id>x94n4j</dm:id>
            <dm:author>Vedomosti</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x94n4j?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=4k54mkijye1f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=2f525fe305c557c136481c269eaa33e8</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/556/540/27045655:avatar_medium.jpg?20090411112150</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>news</dm:channels>
            <pubDate>Wed, 29 Apr 2009 02:06:55 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x94n4j_%D0%B2%D1%8B%D1%81%D0%BE%D0%BA%D0%B8%D0%B5-%D1%82%D0%B5%D1%85%D0%BD%D0%BE%D0%BB%D0%BE%D0%B3%D0%B8%D0%B8-%D0%B4%D0%BB%D1%8F-%D0%BA%D0%BB%D0%B0%D0%B4%D0%BE%D0%B8%D1%81%D0%BA%D0%B0%D1%82%D0%B5%D0%BB_news</guid>
            <media:title>ÐÑÑÐ¾ÐºÐ¸Ðµ ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸ Ð´Ð»Ñ ÐºÐ»Ð°Ð´Ð¾Ð¸ÑÐºÐ°ÑÐµÐ»ÐµÐ¹</media:title>
            <media:credit>Vedomosti</media:credit>
            <media:thumbnail url="http://s2.dmcdn.net/jf2-/x240-sdX.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x94n4j_%D0%B2%D1%8B%D1%81%D0%BE%D0%BA%D0%B8%D0%B5-%D1%82%D0%B5%D1%85%D0%BD%D0%BE%D0%BB%D0%BE%D0%B3%D0%B8%D0%B8-%D0%B4%D0%BB%D1%8F-%D0%BA%D0%BB%D0%B0%D0%B4%D0%BE%D0%B8%D1%81%D0%BA%D0%B0%D1%82%D0%B5%D0%BB_news" height="379" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x94n4j"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x94n4j" type="text/html" duration="108" width="480" height="379"/>
                <media:content url="http://www.dailymotion.com/swf/video/x94n4j" type="application/x-shockwave-flash" duration="108" width="480" height="379"/>
            </media:group>
            <itunes:keywords>ÐºÐ»Ð°Ð´, ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸, ÐÐ¸Ð²ÐµÑÐ³Ð°Ð½Ñ, Ð³Ð°Ð·ÐµÑÐ°, ÐÐµÐ´Ð¾Ð¼Ð¾ÑÑÐ¸</itunes:keywords>
            <media:category label="ÐºÐ»Ð°Ð´">ÐºÐ»Ð°Ð´</media:category>
            <media:category label="ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸">ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸</media:category>
            <media:category label="ÐÐ¸Ð²ÐµÑÐ³Ð°Ð½Ñ">ÐÐ¸Ð²ÐµÑÐ³Ð°Ð½Ñ</media:category>
            <media:category label="Ð³Ð°Ð·ÐµÑÐ°">Ð³Ð°Ð·ÐµÑÐ°</media:category>
            <media:category label="ÐÐµÐ´Ð¾Ð¼Ð¾ÑÑÐ¸">ÐÐµÐ´Ð¾Ð¼Ð¾ÑÑÐ¸</media:category>
        </item>
        <item>
            <title>ÐÐµÑÐµÑÐ°Ð½Ñ ÐºÐ¾ÑÐ¼Ð¾ÑÐ° Ð²Ð½Ð¾Ð²Ñ Ð¿Ð¾Ð±ÑÐ²Ð°Ð»Ð¸ Ð½Ð° ÑÑÐ°Ð½ÑÐ¸Ð¸ Â«ÐÐ¸ÑÂ»</title>
            <link>http://www.dailymotion.com/video/x908pz_%D0%B2%D0%B5%D1%82%D0%B5%D1%80%D0%B0%D0%BD%D1%8B-%D0%BA%D0%BE%D1%81%D0%BC%D0%BE%D1%81%D0%B0-%D0%B2%D0%BD%D0%BE%D0%B2%D1%8C-%D0%BF%D0%BE%D0%B1%D1%8B%D0%B2%D0%B0%D0%BB%D0%B8-%D0%BD%D0%B0_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x908pz_%D0%B2%D0%B5%D1%82%D0%B5%D1%80%D0%B0%D0%BD%D1%8B-%D0%BA%D0%BE%D1%81%D0%BC%D0%BE%D1%81%D0%B0-%D0%B2%D0%BD%D0%BE%D0%B2%D1%8C-%D0%BF%D0%BE%D0%B1%D1%8B%D0%B2%D0%B0%D0%BB%D0%B8-%D0%BD%D0%B0_tech"><img align="right" width="120" height="90" src="http://s2.dmcdn.net/AOs7e/160x90-SxU.jpg" style="border: 2px solid #B9D3FE;"></a><p>ÐÐ°ÐºÐ°Ð½ÑÐ½Ðµ Ð¼ÐµÐ¶Ð´ÑÐ½Ð°ÑÐ¾Ð´Ð½Ð¾Ð³Ð¾ Ð´Ð½Ñ ÐºÐ¾ÑÐ¼Ð¾Ð½Ð°Ð²ÑÐ¸ÐºÐ¸ Ð¿Ð¾ÑÐ»Ðµ ÑÐµÐºÐ¾Ð½ÑÑÑÑÐºÑÐ¸Ð¸ Ð¾ÑÐºÑÑÐ»ÑÑ ÐÐµÐ¼Ð¾ÑÐ¸Ð°Ð»ÑÐ½ÑÐ¹ Ð¼ÑÐ·ÐµÐ¹ ÐºÐ¾ÑÐ¼Ð¾Ð½Ð°Ð²ÑÐ¸ÐºÐ¸. ÐÐ³Ð¾ Ð¿Ð»Ð¾ÑÐ°Ð´Ñ ÑÐ²ÐµÐ»Ð¸ÑÐ¸Ð»Ð°ÑÑ Ð² 3 ÑÐ°Ð·Ð°, Ð¸ Ð½Ð°ÑÐ¾Ð´Ð¸ÑÑÑ Ð¾Ð½ Ð¿Ð¾Ð´ Ð·ÐµÐ¼Ð»ÑÐ¹.</p><p>Author: <a href="http://www.dailymotion.com/RussianNTD"><img src="http://static2.dmcdn.net/static/user/473/499/23994374:avatar_medium.jpg?20110513130152" width="80" height="80" alt="avatar"/>RussianNTD</a><br />Tags: <a href="http://www.dailymotion.com/tag/new">new</a> <a href="http://www.dailymotion.com/tag/tang">tang</a> <a href="http://www.dailymotion.com/tag/dynasty">dynasty</a> <a href="http://www.dailymotion.com/tag/ntd">ntd</a> <a href="http://www.dailymotion.com/tag/Ð´ÐµÐ½Ñ">Ð´ÐµÐ½Ñ</a> <a href="http://www.dailymotion.com/tag/ÐºÐ¾ÑÐ¼Ð¾Ð½Ð°Ð²ÑÐ¸ÐºÐ¸">ÐºÐ¾ÑÐ¼Ð¾Ð½Ð°Ð²ÑÐ¸ÐºÐ¸</a> <a href="http://www.dailymotion.com/tag/ÑÑÐ°Ð½ÑÐ¸Ñ">ÑÑÐ°Ð½ÑÐ¸Ñ</a> <a href="http://www.dailymotion.com/tag/Ð¼Ð¸Ñ">Ð¼Ð¸Ñ</a> <a href="http://www.dailymotion.com/tag/Ð¼ÐµÐ¼Ð¾ÑÐ¸Ð°Ð»ÑÐ½ÑÐ¹">Ð¼ÐµÐ¼Ð¾ÑÐ¸Ð°Ð»ÑÐ½ÑÐ¹</a> <a href="http://www.dailymotion.com/tag/Ð¼ÑÐ·ÐµÐ¹">Ð¼ÑÐ·ÐµÐ¹</a> <a href="http://www.dailymotion.com/tag/ntdtv">ntdtv</a> <a href="http://www.dailymotion.com/tag/ÐºÐ¾ÑÐ¼Ð¾Ñ">ÐºÐ¾ÑÐ¼Ð¾Ñ</a> <a href="http://www.dailymotion.com/tag/Ð²ÐµÑÐµÑÐ°Ð½Ñ">Ð²ÐµÑÐµÑÐ°Ð½Ñ</a> <br />Posted: 17 April 2009<br />Rating: 5.0<br />Votes: 1<br /></p>]]></description>
            <author>rss@dailymotion.com (RussianNTD)</author>
            <itunes:author>RussianNTD</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>ÐÐ°ÐºÐ°Ð½ÑÐ½Ðµ Ð¼ÐµÐ¶Ð´ÑÐ½Ð°ÑÐ¾Ð´Ð½Ð¾Ð³Ð¾ Ð´Ð½Ñ ÐºÐ¾ÑÐ¼Ð¾Ð½Ð°Ð²ÑÐ¸ÐºÐ¸ Ð¿Ð¾ÑÐ»Ðµ ÑÐµÐºÐ¾Ð½ÑÑÑÑÐºÑÐ¸Ð¸ Ð¾ÑÐºÑÑÐ»ÑÑ ÐÐµÐ¼Ð¾ÑÐ¸Ð°Ð»ÑÐ½ÑÐ¹ Ð¼ÑÐ·ÐµÐ¹ ÐºÐ¾ÑÐ¼Ð¾Ð½Ð°Ð²ÑÐ¸ÐºÐ¸. ÐÐ³Ð¾ Ð¿Ð»Ð¾ÑÐ°Ð´Ñ ÑÐ²ÐµÐ»Ð¸ÑÐ¸Ð»Ð°ÑÑ Ð² 3 ÑÐ°Ð·Ð°, Ð¸ Ð½Ð°ÑÐ¾Ð´Ð¸ÑÑÑ Ð¾Ð½ Ð¿Ð¾Ð´ Ð·ÐµÐ¼Ð»ÑÐ¹.</itunes:summary>
            <itunes:subtitle>ÐÐ°ÐºÐ°Ð½ÑÐ½Ðµ Ð¼ÐµÐ¶Ð´ÑÐ½Ð°ÑÐ¾Ð´Ð½Ð¾Ð³Ð¾ Ð´Ð½Ñ ÐºÐ¾ÑÐ¼Ð¾Ð½Ð°Ð²ÑÐ¸ÐºÐ¸ Ð¿Ð¾ÑÐ»Ðµ ÑÐµÐºÐ¾Ð½ÑÑÑÑÐºÑÐ¸Ð¸ Ð¾ÑÐºÑÑÐ»ÑÑ ÐÐµÐ¼Ð¾ÑÐ¸Ð°Ð»ÑÐ½ÑÐ¹ Ð¼ÑÐ·ÐµÐ¹ ÐºÐ¾ÑÐ¼Ð¾Ð½Ð°Ð²ÑÐ¸ÐºÐ¸. ÐÐ³Ð¾ Ð¿Ð»Ð¾ÑÐ°Ð´Ñ ÑÐ²ÐµÐ»Ð¸ÑÐ¸Ð»Ð°ÑÑ Ð² 3 ÑÐ°Ð·Ð°, Ð¸ Ð½Ð°ÑÐ¾Ð´Ð¸ÑÑÑ Ð¾Ð½ Ð¿Ð¾Ð´ Ð·ÐµÐ¼Ð»ÑÐ¹.</itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>1</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x908pz_%D0%B2%D0%B5%D1%82%D0%B5%D1%80%D0%B0%D0%BD%D1%8B-%D0%BA%D0%BE%D1%81%D0%BC%D0%BE%D1%81%D0%B0-%D0%B2%D0%BD%D0%BE%D0%B2%D1%8C-%D0%BF%D0%BE%D0%B1%D1%8B%D0%B2%D0%B0%D0%BB%D0%B8-%D0%BD%D0%B0_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/RussianNTD" type="application/rss+xml"/>
            <dm:views>401</dm:views>
            <dm:comments>0</dm:comments>
            <dm:favorites>1</dm:favorites>
            <dm:id>x908pz</dm:id>
            <dm:author>RussianNTD</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x908pz?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=4u2ezy31t31f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=ce636f8a1fa472cd9471632fbb0e8af2</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/473/499/23994374:avatar_medium.jpg?20110513130152</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Fri, 17 Apr 2009 11:07:20 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x908pz_%D0%B2%D0%B5%D1%82%D0%B5%D1%80%D0%B0%D0%BD%D1%8B-%D0%BA%D0%BE%D1%81%D0%BC%D0%BE%D1%81%D0%B0-%D0%B2%D0%BD%D0%BE%D0%B2%D1%8C-%D0%BF%D0%BE%D0%B1%D1%8B%D0%B2%D0%B0%D0%BB%D0%B8-%D0%BD%D0%B0_tech</guid>
            <media:title>ÐÐµÑÐµÑÐ°Ð½Ñ ÐºÐ¾ÑÐ¼Ð¾ÑÐ° Ð²Ð½Ð¾Ð²Ñ Ð¿Ð¾Ð±ÑÐ²Ð°Ð»Ð¸ Ð½Ð° ÑÑÐ°Ð½ÑÐ¸Ð¸ Â«ÐÐ¸ÑÂ»</media:title>
            <media:credit>RussianNTD</media:credit>
            <media:thumbnail url="http://s2.dmcdn.net/AOs7e/x240-gj4.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x908pz_%D0%B2%D0%B5%D1%82%D0%B5%D1%80%D0%B0%D0%BD%D1%8B-%D0%BA%D0%BE%D1%81%D0%BC%D0%BE%D1%81%D0%B0-%D0%B2%D0%BD%D0%BE%D0%B2%D1%8C-%D0%BF%D0%BE%D0%B1%D1%8B%D0%B2%D0%B0%D0%BB%D0%B8-%D0%BD%D0%B0_tech" height="360" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x908pz"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x908pz" type="text/html" duration="122" width="480" height="360"/>
                <media:content url="http://www.dailymotion.com/swf/video/x908pz" type="application/x-shockwave-flash" duration="122" width="480" height="360"/>
            </media:group>
            <itunes:keywords>new, tang, dynasty, ntd, Ð´ÐµÐ½Ñ, ÐºÐ¾ÑÐ¼Ð¾Ð½Ð°Ð²ÑÐ¸ÐºÐ¸, ÑÑÐ°Ð½ÑÐ¸Ñ, Ð¼Ð¸Ñ, Ð¼ÐµÐ¼Ð¾ÑÐ¸Ð°Ð»ÑÐ½ÑÐ¹, Ð¼ÑÐ·ÐµÐ¹, ntdtv, ÐºÐ¾ÑÐ¼Ð¾Ñ, Ð²ÐµÑÐµÑÐ°Ð½Ñ</itunes:keywords>
            <media:category label="new">new</media:category>
            <media:category label="tang">tang</media:category>
            <media:category label="dynasty">dynasty</media:category>
            <media:category label="ntd">ntd</media:category>
            <media:category label="Ð´ÐµÐ½Ñ">Ð´ÐµÐ½Ñ</media:category>
            <media:category label="ÐºÐ¾ÑÐ¼Ð¾Ð½Ð°Ð²ÑÐ¸ÐºÐ¸">ÐºÐ¾ÑÐ¼Ð¾Ð½Ð°Ð²ÑÐ¸ÐºÐ¸</media:category>
            <media:category label="ÑÑÐ°Ð½ÑÐ¸Ñ">ÑÑÐ°Ð½ÑÐ¸Ñ</media:category>
            <media:category label="Ð¼Ð¸Ñ">Ð¼Ð¸Ñ</media:category>
            <media:category label="Ð¼ÐµÐ¼Ð¾ÑÐ¸Ð°Ð»ÑÐ½ÑÐ¹">Ð¼ÐµÐ¼Ð¾ÑÐ¸Ð°Ð»ÑÐ½ÑÐ¹</media:category>
            <media:category label="Ð¼ÑÐ·ÐµÐ¹">Ð¼ÑÐ·ÐµÐ¹</media:category>
            <media:category label="ntdtv">ntdtv</media:category>
            <media:category label="ÐºÐ¾ÑÐ¼Ð¾Ñ">ÐºÐ¾ÑÐ¼Ð¾Ñ</media:category>
            <media:category label="Ð²ÐµÑÐµÑÐ°Ð½Ñ">Ð²ÐµÑÐµÑÐ°Ð½Ñ</media:category>
        </item>
        <item>
            <title>ÐÑÐ·ÑÐºÐ°Ð»ÑÐ½ÑÐ¹ Ð²ÐµÐ±-ÑÐ°Ð¹Ñ Ð¾Ñ Google Ð² ÐÐ¸ÑÐ°Ðµ</title>
            <link>http://www.dailymotion.com/video/x92ltu_%D0%BC%D1%83%D0%B7%D1%8B%D0%BA%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9-%D0%B2%D0%B5%D0%B1-%D1%81%D0%B0%D0%B9%D1%82-%D0%BE%D1%82-google-%D0%B2-%D0%BA%D0%B8_music</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x92ltu_%D0%BC%D1%83%D0%B7%D1%8B%D0%BA%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9-%D0%B2%D0%B5%D0%B1-%D1%81%D0%B0%D0%B9%D1%82-%D0%BE%D1%82-google-%D0%B2-%D0%BA%D0%B8_music"><img align="right" width="120" height="90" src="http://s1.dmcdn.net/HxiB/160x90-EFF.jpg" style="border: 2px solid #B9D3FE;"></a><p>Ð ÑÑÐ¾Ð¼ Ð¼ÐµÑÑÑÐµ Google Ð¾ÑÐºÑÑÐ» Ð² ÐÐ¸ÑÐ°Ðµ Ð½Ð¾Ð²ÑÐ¹ Ð¼ÑÐ·ÑÐºÐ°Ð»ÑÐ½ÑÐ¹ Ð²ÐµÐ±-ÑÐ°Ð¹Ñ, Ð³Ð´Ðµ Ð¿Ð¾ÑÐµÑÐ¸ÑÐµÐ»Ð¸ Ð¼Ð¾Ð³ÑÑ Ð±ÐµÑÐ¿Ð»Ð°ÑÐ½Ð¾ ÑÐºÐ°ÑÐ°ÑÑ Ð¿Ð¾Ð¿ÑÐ»ÑÑÐ½ÑÐµ ÐÐ 3 Ð¿ÐµÑÐ½Ð¸. ÐÐ¾ ÑÐ¾Ð»ÑÐºÐ¾ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»Ð¸, ÑÐµÐ¹ IP-Ð°Ð´ÑÐµÑ Ð·Ð°ÑÐµÐ³Ð¸ÑÑÑÐ¸ÑÐ¾Ð²Ð°Ð½, ÑÐ¼Ð¾Ð³ÑÑ Ð·Ð°Ð¹ÑÐ¸ Ð½Ð° ÑÐ°Ð¹Ñ.</p><p>Author: <a href="http://www.dailymotion.com/RussianNTD"><img src="http://static2.dmcdn.net/static/user/473/499/23994374:avatar_medium.jpg?20110513130152" width="80" height="80" alt="avatar"/>RussianNTD</a><br />Tags: <a href="http://www.dailymotion.com/tag/google">google</a> <a href="http://www.dailymotion.com/tag/ÐºÐ¸ÑÐ°Ð¹">ÐºÐ¸ÑÐ°Ð¹</a> <a href="http://www.dailymotion.com/tag/ntd">ntd</a> <a href="http://www.dailymotion.com/tag/Ð¼Ñ">Ð¼Ñ</a> <a href="http://www.dailymotion.com/tag/Ð½Ð¾Ð²Ð¾ÑÑÐ¸">Ð½Ð¾Ð²Ð¾ÑÑÐ¸</a> <a href="http://www.dailymotion.com/tag/new">new</a> <a href="http://www.dailymotion.com/tag/tang">tang</a> <a href="http://www.dailymotion.com/tag/dynasty">dynasty</a> <a href="http://www.dailymotion.com/tag/Ð¿ÐµÑÐ½Ñ">Ð¿ÐµÑÐ½Ñ</a> <a href="http://www.dailymotion.com/tag/ntdtv">ntdtv</a> <a href="http://www.dailymotion.com/tag/ÑÐµÐ½Ð·ÑÑÐ°">ÑÐµÐ½Ð·ÑÑÐ°</a> <br />Posted: 23 April 2009<br />Rating: 5.0<br />Votes: 1<br /></p>]]></description>
            <author>rss@dailymotion.com (RussianNTD)</author>
            <itunes:author>RussianNTD</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>Ð ÑÑÐ¾Ð¼ Ð¼ÐµÑÑÑÐµ Google Ð¾ÑÐºÑÑÐ» Ð² ÐÐ¸ÑÐ°Ðµ Ð½Ð¾Ð²ÑÐ¹ Ð¼ÑÐ·ÑÐºÐ°Ð»ÑÐ½ÑÐ¹ Ð²ÐµÐ±-ÑÐ°Ð¹Ñ, Ð³Ð´Ðµ Ð¿Ð¾ÑÐµÑÐ¸ÑÐµÐ»Ð¸ Ð¼Ð¾Ð³ÑÑ Ð±ÐµÑÐ¿Ð»Ð°ÑÐ½Ð¾ ÑÐºÐ°ÑÐ°ÑÑ Ð¿Ð¾Ð¿ÑÐ»ÑÑÐ½ÑÐµ ÐÐ 3 Ð¿ÐµÑÐ½Ð¸. ÐÐ¾ ÑÐ¾Ð»ÑÐºÐ¾ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»Ð¸, ÑÐµÐ¹ IP-Ð°Ð´ÑÐµÑ Ð·Ð°ÑÐµÐ³Ð¸ÑÑÑÐ¸ÑÐ¾Ð²Ð°Ð½, ÑÐ¼Ð¾Ð³ÑÑ Ð·Ð°Ð¹ÑÐ¸ Ð½Ð° ÑÐ°Ð¹Ñ.</itunes:summary>
            <itunes:subtitle>Ð ÑÑÐ¾Ð¼ Ð¼ÐµÑÑÑÐµ Google Ð¾ÑÐºÑÑÐ» Ð² ÐÐ¸ÑÐ°Ðµ Ð½Ð¾Ð²ÑÐ¹ Ð¼ÑÐ·ÑÐºÐ°Ð»ÑÐ½ÑÐ¹ Ð²ÐµÐ±-ÑÐ°Ð¹Ñ, Ð³Ð´Ðµ Ð¿Ð¾ÑÐµÑÐ¸ÑÐµÐ»Ð¸ Ð¼Ð¾Ð³ÑÑ Ð±ÐµÑÐ¿Ð»Ð°ÑÐ½Ð¾ ÑÐºÐ°ÑÐ°ÑÑ Ð¿Ð¾Ð¿ÑÐ»ÑÑÐ½ÑÐµ ÐÐ 3 Ð¿ÐµÑÐ½Ð¸. ÐÐ¾ ÑÐ¾Ð»ÑÐºÐ¾ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»Ð¸, ÑÐµÐ¹ IP-Ð°Ð´ÑÐµÑ Ð·Ð°ÑÐµÐ³Ð¸ÑÑÑÐ¸ÑÐ¾Ð²Ð°Ð½, ÑÐ¼Ð¾Ð³ÑÑ Ð·Ð°Ð¹ÑÐ¸ Ð½Ð° ÑÐ°Ð¹Ñ.</itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>1</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x92ltu_%D0%BC%D1%83%D0%B7%D1%8B%D0%BA%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9-%D0%B2%D0%B5%D0%B1-%D1%81%D0%B0%D0%B9%D1%82-%D0%BE%D1%82-google-%D0%B2-%D0%BA%D0%B8_music" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/RussianNTD" type="application/rss+xml"/>
            <dm:views>988</dm:views>
            <dm:comments>0</dm:comments>
            <dm:favorites>0</dm:favorites>
            <dm:id>x92ltu</dm:id>
            <dm:author>RussianNTD</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x92ltu?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=808gjuyf4y1f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=0f6109380d0a748394e02ce9ae0d8947</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/473/499/23994374:avatar_medium.jpg?20110513130152</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>music</dm:channels>
            <pubDate>Thu, 23 Apr 2009 16:56:43 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x92ltu_%D0%BC%D1%83%D0%B7%D1%8B%D0%BA%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9-%D0%B2%D0%B5%D0%B1-%D1%81%D0%B0%D0%B9%D1%82-%D0%BE%D1%82-google-%D0%B2-%D0%BA%D0%B8_music</guid>
            <media:title>ÐÑÐ·ÑÐºÐ°Ð»ÑÐ½ÑÐ¹ Ð²ÐµÐ±-ÑÐ°Ð¹Ñ Ð¾Ñ Google Ð² ÐÐ¸ÑÐ°Ðµ</media:title>
            <media:credit>RussianNTD</media:credit>
            <media:thumbnail url="http://s1.dmcdn.net/HxiB/x240-Av3.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x92ltu_%D0%BC%D1%83%D0%B7%D1%8B%D0%BA%D0%B0%D0%BB%D1%8C%D0%BD%D1%8B%D0%B9-%D0%B2%D0%B5%D0%B1-%D1%81%D0%B0%D0%B9%D1%82-%D0%BE%D1%82-google-%D0%B2-%D0%BA%D0%B8_music" height="360" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x92ltu"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x92ltu" type="text/html" duration="59" width="480" height="360"/>
                <media:content url="http://www.dailymotion.com/swf/video/x92ltu" type="application/x-shockwave-flash" duration="59" width="480" height="360"/>
            </media:group>
            <itunes:keywords>google, ÐºÐ¸ÑÐ°Ð¹, ntd, Ð¼Ñ, Ð½Ð¾Ð²Ð¾ÑÑÐ¸, new, tang, dynasty, Ð¿ÐµÑÐ½Ñ, ntdtv, ÑÐµÐ½Ð·ÑÑÐ°</itunes:keywords>
            <media:category label="google">google</media:category>
            <media:category label="ÐºÐ¸ÑÐ°Ð¹">ÐºÐ¸ÑÐ°Ð¹</media:category>
            <media:category label="ntd">ntd</media:category>
            <media:category label="Ð¼Ñ">Ð¼Ñ</media:category>
            <media:category label="Ð½Ð¾Ð²Ð¾ÑÑÐ¸">Ð½Ð¾Ð²Ð¾ÑÑÐ¸</media:category>
            <media:category label="new">new</media:category>
            <media:category label="tang">tang</media:category>
            <media:category label="dynasty">dynasty</media:category>
            <media:category label="Ð¿ÐµÑÐ½Ñ">Ð¿ÐµÑÐ½Ñ</media:category>
            <media:category label="ntdtv">ntdtv</media:category>
            <media:category label="ÑÐµÐ½Ð·ÑÑÐ°">ÑÐµÐ½Ð·ÑÑÐ°</media:category>
        </item>
        <item>
            <title>Asus G71V: ÑÐµÑÑÑÐµ ÑÐ´ÑÐ° Ð² Ð½Ð¾ÑÑÐ±ÑÐºÐµ Ð´Ð»Ñ Ð¸Ð³Ñ</title>
            <link>http://www.dailymotion.com/video/x908rg_asus-g71v-%D1%87%D0%B5%D1%82%D1%8B%D1%80%D0%B5-%D1%8F%D0%B4%D1%80%D0%B0-%D0%B2-%D0%BD%D0%BE%D1%83%D1%82%D0%B1%D1%83%D0%BA%D0%B5-%D0%B4%D0%BB_videogames</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x908rg_asus-g71v-%D1%87%D0%B5%D1%82%D1%8B%D1%80%D0%B5-%D1%8F%D0%B4%D1%80%D0%B0-%D0%B2-%D0%BD%D0%BE%D1%83%D1%82%D0%B1%D1%83%D0%BA%D0%B5-%D0%B4%D0%BB_videogames"><img align="right" width="120" height="90" src="http://s2.dmcdn.net/AOtHO/160x90-0Nn.jpg" style="border: 2px solid #B9D3FE;"></a><p>ÐÐ±Ð·Ð¾Ñ ÑÐ°ÑÐ°ÐºÑÐµÑÐ¸ÑÑÐ¸Ðº, Ð´Ð¸Ð·Ð°Ð¹Ð½Ð° Ð¸ Ð²Ð¾Ð·Ð¼Ð¾Ð¶Ð½Ð¾ÑÑÐµÐ¹ Ð½Ð¾Ð²Ð¾Ð³Ð¾ Ð½Ð¾ÑÑÐ±ÑÐºÐ° Asus G71V, ÑÐ¿ÐµÑÐ¸Ð°Ð»ÑÐ½Ð¾ Ð¿ÑÐµÐ´Ð½Ð°Ð·Ð½Ð°ÑÐµÐ½Ð½Ð¾Ð³Ð¾ Ð´Ð»Ñ Ð¸Ð³Ñ.  <br><br>ÐÐ¾Ð¼Ð¿ÑÑÑÐµÑ Ð¾ÑÐ½Ð°ÑÐµÐ½ Ð¿ÑÐ¾ÑÐµÑÑÐ¾ÑÐ¾Ð¼ Intel Core 2 Extreme, Ð²Ð¸Ð´ÐµÐ¾ÐºÐ°ÑÑÐ¾Ð¹ NVIDIA GeForce 9700M GT. ÐÐ¸Ð·Ð°Ð½ ÐºÐ¾ÑÐ¿ÑÑÐ° Ð²ÑÐ¿Ð¾Ð»Ð½ÐµÐ½ Ð² ÑÐµÑÐ½Ð¾-ÐºÑÐ°ÑÐ½ÑÑ ÑÐ¾Ð½Ð°Ñ, Ð¸Ð¼ÐµÐµÑÑÑ Ð¿Ð¾Ð´ÑÐ²ÐµÑÐºÐ° Direct Flash.</p><p>Author: <a href="http://www.dailymotion.com/cnews"><img src="http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338" width="80" height="80" alt="avatar"/>cnews</a><br />Tags: <a href="http://www.dailymotion.com/tag/Asus">Asus</a> <a href="http://www.dailymotion.com/tag/Ð½Ð¾ÑÑÐ±ÑÐº">Ð½Ð¾ÑÑÐ±ÑÐº</a> <a href="http://www.dailymotion.com/tag/Ð¸Ð³ÑÑ">Ð¸Ð³ÑÑ</a> <a href="http://www.dailymotion.com/tag/Ð³ÐµÐ¹Ð¼ÐµÑ">Ð³ÐµÐ¹Ð¼ÐµÑ</a> <a href="http://www.dailymotion.com/tag/ÐºÑÑÑÐ¾Ð¹">ÐºÑÑÑÐ¾Ð¹</a> <a href="http://www.dailymotion.com/tag/gamer">gamer</a> <a href="http://www.dailymotion.com/tag/CNewsTV">CNewsTV</a> <a href="http://www.dailymotion.com/tag/Intel">Intel</a> <a href="http://www.dailymotion.com/tag/Core">Core</a> <a href="http://www.dailymotion.com/tag/NVIDIA">NVIDIA</a> <a href="http://www.dailymotion.com/tag/GeForce">GeForce</a> <br />Posted: 17 April 2009<br />Rating: 5.0<br />Votes: 1<br /></p>]]></description>
            <author>rss@dailymotion.com (cnews)</author>
            <itunes:author>cnews</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>ÐÐ±Ð·Ð¾Ñ ÑÐ°ÑÐ°ÐºÑÐµÑÐ¸ÑÑÐ¸Ðº, Ð´Ð¸Ð·Ð°Ð¹Ð½Ð° Ð¸ Ð²Ð¾Ð·Ð¼Ð¾Ð¶Ð½Ð¾ÑÑÐµÐ¹ Ð½Ð¾Ð²Ð¾Ð³Ð¾ Ð½Ð¾ÑÑÐ±ÑÐºÐ° Asus G71V, ÑÐ¿ÐµÑÐ¸Ð°Ð»ÑÐ½Ð¾ Ð¿ÑÐµÐ´Ð½Ð°Ð·Ð½Ð°ÑÐµÐ½Ð½Ð¾Ð³Ð¾ Ð´Ð»Ñ Ð¸Ð³Ñ.  ÐÐ¾Ð¼Ð¿ÑÑÑÐµÑ Ð¾ÑÐ½Ð°ÑÐµÐ½ Ð¿ÑÐ¾ÑÐµÑÑÐ¾ÑÐ¾Ð¼ Intel Core 2 Extreme, Ð²Ð¸Ð´ÐµÐ¾ÐºÐ°ÑÑÐ¾Ð¹ NVIDIA GeForce 9700M GT. ÐÐ¸Ð·Ð°Ð½ ÐºÐ¾ÑÐ¿ÑÑÐ° Ð²ÑÐ¿Ð¾Ð»Ð½ÐµÐ½ Ð² ÑÐµÑÐ½Ð¾-ÐºÑÐ°ÑÐ½ÑÑ...</itunes:summary>
            <itunes:subtitle>ÐÐ±Ð·Ð¾Ñ ÑÐ°ÑÐ°ÐºÑÐµÑÐ¸ÑÑÐ¸Ðº, Ð´Ð¸Ð·Ð°Ð¹Ð½Ð° Ð¸ Ð²Ð¾Ð·Ð¼Ð¾Ð¶Ð½Ð¾ÑÑÐµÐ¹ Ð½Ð¾Ð²Ð¾Ð³Ð¾ Ð½Ð¾ÑÑÐ±ÑÐºÐ° Asus G71V, ÑÐ¿ÐµÑÐ¸Ð°Ð»ÑÐ½Ð¾ Ð¿ÑÐµÐ´Ð½Ð°Ð·Ð½Ð°ÑÐµÐ½Ð½Ð¾Ð³Ð¾ Ð´Ð»Ñ Ð¸Ð³Ñ.  ÐÐ¾Ð¼Ð¿ÑÑÑÐµÑ Ð¾ÑÐ½Ð°ÑÐµÐ½ Ð¿ÑÐ¾ÑÐµÑÑÐ¾ÑÐ¾Ð¼ Intel Core 2 Extreme, Ð²Ð¸Ð´ÐµÐ¾ÐºÐ°ÑÑÐ¾Ð¹ NVIDIA GeForce 9700M GT. ÐÐ¸Ð·Ð°Ð½ ÐºÐ¾ÑÐ¿ÑÑÐ° Ð²ÑÐ¿Ð¾Ð»Ð½ÐµÐ½ Ð² ÑÐµÑÐ½Ð¾-ÐºÑÐ°ÑÐ½ÑÑ...</itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>1</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x908rg_asus-g71v-%D1%87%D0%B5%D1%82%D1%8B%D1%80%D0%B5-%D1%8F%D0%B4%D1%80%D0%B0-%D0%B2-%D0%BD%D0%BE%D1%83%D1%82%D0%B1%D1%83%D0%BA%D0%B5-%D0%B4%D0%BB_videogames" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/cnews" type="application/rss+xml"/>
            <dm:views>3646</dm:views>
            <dm:comments>0</dm:comments>
            <dm:favorites>1</dm:favorites>
            <dm:id>x908rg</dm:id>
            <dm:author>cnews</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x908rg?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=54r0e8tvlc1f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=225f1606e130ee2445c7bc69e7b374b3</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>videogames</dm:channels>
            <pubDate>Fri, 17 Apr 2009 11:11:00 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x908rg_asus-g71v-%D1%87%D0%B5%D1%82%D1%8B%D1%80%D0%B5-%D1%8F%D0%B4%D1%80%D0%B0-%D0%B2-%D0%BD%D0%BE%D1%83%D1%82%D0%B1%D1%83%D0%BA%D0%B5-%D0%B4%D0%BB_videogames</guid>
            <media:title>Asus G71V: ÑÐµÑÑÑÐµ ÑÐ´ÑÐ° Ð² Ð½Ð¾ÑÑÐ±ÑÐºÐµ Ð´Ð»Ñ Ð¸Ð³Ñ</media:title>
            <media:credit>cnews</media:credit>
            <media:thumbnail url="http://s2.dmcdn.net/AOtHO/x240-NBv.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x908rg_asus-g71v-%D1%87%D0%B5%D1%82%D1%8B%D1%80%D0%B5-%D1%8F%D0%B4%D1%80%D0%B0-%D0%B2-%D0%BD%D0%BE%D1%83%D1%82%D0%B1%D1%83%D0%BA%D0%B5-%D0%B4%D0%BB_videogames" height="360" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x908rg"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x908rg" type="text/html" duration="88" width="480" height="360"/>
                <media:content url="http://www.dailymotion.com/swf/video/x908rg" type="application/x-shockwave-flash" duration="88" width="480" height="360"/>
            </media:group>
            <itunes:keywords>Asus, Ð½Ð¾ÑÑÐ±ÑÐº, Ð¸Ð³ÑÑ, Ð³ÐµÐ¹Ð¼ÐµÑ, ÐºÑÑÑÐ¾Ð¹, gamer, CNewsTV, Intel, Core, NVIDIA, GeForce</itunes:keywords>
            <media:category label="Asus">Asus</media:category>
            <media:category label="Ð½Ð¾ÑÑÐ±ÑÐº">Ð½Ð¾ÑÑÐ±ÑÐº</media:category>
            <media:category label="Ð¸Ð³ÑÑ">Ð¸Ð³ÑÑ</media:category>
            <media:category label="Ð³ÐµÐ¹Ð¼ÐµÑ">Ð³ÐµÐ¹Ð¼ÐµÑ</media:category>
            <media:category label="ÐºÑÑÑÐ¾Ð¹">ÐºÑÑÑÐ¾Ð¹</media:category>
            <media:category label="gamer">gamer</media:category>
            <media:category label="CNewsTV">CNewsTV</media:category>
            <media:category label="Intel">Intel</media:category>
            <media:category label="Core">Core</media:category>
            <media:category label="NVIDIA">NVIDIA</media:category>
            <media:category label="GeForce">GeForce</media:category>
        </item>
        <item>
            <title>Techblog.gr AIBO robots</title>
            <link>http://www.dailymotion.com/video/x8x9ye_techblog-gr-aibo-robots_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x8x9ye_techblog-gr-aibo-robots_tech"><img align="right" width="120" height="90" src="http://s1.dmcdn.net/AfiOz/160x90-bGW.jpg" style="border: 2px solid #B9D3FE;"></a><p></p><p>Author: <a href="http://www.dailymotion.com/blogchannel"><img src="http://static2.dmcdn.net/static/user/899/612/24216998:avatar_medium.jpg?20090408193229" width="80" height="80" alt="avatar"/>blogchannel</a><br />Tags: <a href="http://www.dailymotion.com/tag/techbloggr">techbloggr</a> <a href="http://www.dailymotion.com/tag/aibo">aibo</a> <a href="http://www.dailymotion.com/tag/robots">robots</a> <br />Posted: 09 April 2009<br />Rating: 5.0<br />Votes: 4<br /></p>]]></description>
            <author>rss@dailymotion.com (blogchannel)</author>
            <itunes:author>blogchannel</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary></itunes:summary>
            <itunes:subtitle></itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>4</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x8x9ye_techblog-gr-aibo-robots_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/blogchannel" type="application/rss+xml"/>
            <dm:views>2109</dm:views>
            <dm:comments>0</dm:comments>
            <dm:favorites>4</dm:favorites>
            <dm:id>x8x9ye</dm:id>
            <dm:author>blogchannel</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x8x9ye?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=u2eq904hg11f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=3f11316f6206829cd4a032ee75b6e87b</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/899/612/24216998:avatar_medium.jpg?20090408193229</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Thu, 09 Apr 2009 06:16:10 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x8x9ye_techblog-gr-aibo-robots_tech</guid>
            <media:title>Techblog.gr AIBO robots</media:title>
            <media:credit>blogchannel</media:credit>
            <media:thumbnail url="http://s1.dmcdn.net/AfiOz/x240-yAU.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x8x9ye_techblog-gr-aibo-robots_tech" height="288" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x8x9ye"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x8x9ye" type="text/html" duration="165" width="480" height="288"/>
                <media:content url="http://www.dailymotion.com/swf/video/x8x9ye" type="application/x-shockwave-flash" duration="165" width="480" height="288"/>
            </media:group>
            <itunes:keywords>techbloggr, aibo, robots</itunes:keywords>
            <media:category label="techbloggr">techbloggr</media:category>
            <media:category label="aibo">aibo</media:category>
            <media:category label="robots">robots</media:category>
        </item>
        <item>
            <title>ÐÑÐ¾ÑÑÑÐµ Ð²Ð¾Ð¿ÑÐ¾ÑÑ: ÐÐµÐ¼Ñ Ð»Ð¸ ÑÑÐ±Ñ?</title>
            <link>http://www.dailymotion.com/video/x8s98z_%D0%BF%D1%80%D0%BE%D1%81%D1%82%D1%8B%D0%B5-%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%D1%8B-%D0%BD%D0%B5%D0%BC%D1%8B-%D0%BB%D0%B8-%D1%80%D1%8B%D0%B1%D1%8B_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x8s98z_%D0%BF%D1%80%D0%BE%D1%81%D1%82%D1%8B%D0%B5-%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%D1%8B-%D0%BD%D0%B5%D0%BC%D1%8B-%D0%BB%D0%B8-%D1%80%D1%8B%D0%B1%D1%8B_tech"><img align="right" width="120" height="90" src="http://s2.dmcdn.net/cnSF/160x90--ou.jpg" style="border: 2px solid #B9D3FE;"></a><p>ÐÐµÑÐ½Ð¾ Ð»Ð¸ ÑÑÐ²ÐµÑÐ¶Ð´ÐµÐ½Ð¸Ðµ: "ÐÑÐºÑÑÐ²Ð°ÐµÑ ÑÑÐ±Ð° ÑÐ¾Ñ, Ð´Ð° Ð½Ðµ ÑÐ»ÑÑÐ½Ð¾ ÑÑÐ¾ Ð¿Ð¾ÐµÑ?"</p><p>Author: <a href="http://www.dailymotion.com/praktika"><img src="http://static2.dmcdn.net/static/user/366/197/25791663:avatar_medium.jpg?20090219072133" width="80" height="80" alt="avatar"/>praktika</a><br />Tags: <a href="http://www.dailymotion.com/tag/ÑÑÐ±Ñ">ÑÑÐ±Ñ</a> <a href="http://www.dailymotion.com/tag/Ð°Ð½ÑÐ¾Ð½ÐµÑ">Ð°Ð½ÑÐ¾Ð½ÐµÑ</a> <a href="http://www.dailymotion.com/tag/Ð½Ð°ÑÐºÐ°">Ð½Ð°ÑÐºÐ°</a> <a href="http://www.dailymotion.com/tag/Ð¾ÑÐ²ÐµÑÑ">Ð¾ÑÐ²ÐµÑÑ</a> <br />Posted: 26 March 2009<br />Rating: 5.0<br />Votes: 2<br /></p>]]></description>
            <author>rss@dailymotion.com (praktika)</author>
            <itunes:author>praktika</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>ÐÐµÑÐ½Ð¾ Ð»Ð¸ ÑÑÐ²ÐµÑÐ¶Ð´ÐµÐ½Ð¸Ðµ: &quot;ÐÑÐºÑÑÐ²Ð°ÐµÑ ÑÑÐ±Ð° ÑÐ¾Ñ, Ð´Ð° Ð½Ðµ ÑÐ»ÑÑÐ½Ð¾ ÑÑÐ¾ Ð¿Ð¾ÐµÑ?&quot;</itunes:summary>
            <itunes:subtitle>ÐÐµÑÐ½Ð¾ Ð»Ð¸ ÑÑÐ²ÐµÑÐ¶Ð´ÐµÐ½Ð¸Ðµ: &quot;ÐÑÐºÑÑÐ²Ð°ÐµÑ ÑÑÐ±Ð° ÑÐ¾Ñ, Ð´Ð° Ð½Ðµ ÑÐ»ÑÑÐ½Ð¾ ÑÑÐ¾ Ð¿Ð¾ÐµÑ?&quot;</itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>2</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x8s98z_%D0%BF%D1%80%D0%BE%D1%81%D1%82%D1%8B%D0%B5-%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%D1%8B-%D0%BD%D0%B5%D0%BC%D1%8B-%D0%BB%D0%B8-%D1%80%D1%8B%D0%B1%D1%8B_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/praktika" type="application/rss+xml"/>
            <dm:views>492</dm:views>
            <dm:comments>0</dm:comments>
            <dm:favorites>0</dm:favorites>
            <dm:id>x8s98z</dm:id>
            <dm:author>praktika</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x8s98z?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=9wnpwtoup21f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=7aa38568c4e89920adaf099e0ffe0d35</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/366/197/25791663:avatar_medium.jpg?20090219072133</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Thu, 26 Mar 2009 12:11:33 +0100</pubDate>
            <guid>http://www.dailymotion.com/video/x8s98z_%D0%BF%D1%80%D0%BE%D1%81%D1%82%D1%8B%D0%B5-%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%D1%8B-%D0%BD%D0%B5%D0%BC%D1%8B-%D0%BB%D0%B8-%D1%80%D1%8B%D0%B1%D1%8B_tech</guid>
            <media:title>ÐÑÐ¾ÑÑÑÐµ Ð²Ð¾Ð¿ÑÐ¾ÑÑ: ÐÐµÐ¼Ñ Ð»Ð¸ ÑÑÐ±Ñ?</media:title>
            <media:credit>praktika</media:credit>
            <media:thumbnail url="http://s2.dmcdn.net/cnSF/x240-Aa1.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x8s98z_%D0%BF%D1%80%D0%BE%D1%81%D1%82%D1%8B%D0%B5-%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%D1%8B-%D0%BD%D0%B5%D0%BC%D1%8B-%D0%BB%D0%B8-%D1%80%D1%8B%D0%B1%D1%8B_tech" height="360" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x8s98z"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x8s98z" type="text/html" duration="355" width="480" height="360"/>
                <media:content url="http://www.dailymotion.com/swf/video/x8s98z" type="application/x-shockwave-flash" duration="355" width="480" height="360"/>
            </media:group>
            <itunes:keywords>ÑÑÐ±Ñ, Ð°Ð½ÑÐ¾Ð½ÐµÑ, Ð½Ð°ÑÐºÐ°, Ð¾ÑÐ²ÐµÑÑ</itunes:keywords>
            <media:category label="ÑÑÐ±Ñ">ÑÑÐ±Ñ</media:category>
            <media:category label="Ð°Ð½ÑÐ¾Ð½ÐµÑ">Ð°Ð½ÑÐ¾Ð½ÐµÑ</media:category>
            <media:category label="Ð½Ð°ÑÐºÐ°">Ð½Ð°ÑÐºÐ°</media:category>
            <media:category label="Ð¾ÑÐ²ÐµÑÑ">Ð¾ÑÐ²ÐµÑÑ</media:category>
        </item>
        <item>
            <title>ÐÑÐ¸Ð·Ð¸Ñ Ð½Ðµ Ð¿Ð¾Ð¼ÐµÑÐ°ÐµÑ Ð²Ð½ÐµÐ´ÑÐµÐ½Ð¸Ñ ÐÐ¢ Ð² Ð³Ð¾ÑÑÐµÐºÑÐ¾ÑÐµ</title>
            <link>http://www.dailymotion.com/video/x8sei0_%D0%BA%D1%80%D0%B8%D0%B7%D0%B8%D1%81-%D0%BD%D0%B5-%D0%BF%D0%BE%D0%BC%D0%B5%D1%88%D0%B0%D0%B5%D1%82-%D0%B2%D0%BD%D0%B5%D0%B4%D1%80%D0%B5%D0%BD%D0%B8%D1%8E-%D0%B8%D1%82-%D0%B2-%D0%B3_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x8sei0_%D0%BA%D1%80%D0%B8%D0%B7%D0%B8%D1%81-%D0%BD%D0%B5-%D0%BF%D0%BE%D0%BC%D0%B5%D1%88%D0%B0%D0%B5%D1%82-%D0%B2%D0%BD%D0%B5%D0%B4%D1%80%D0%B5%D0%BD%D0%B8%D1%8E-%D0%B8%D1%82-%D0%B2-%D0%B3_tech"><img align="right" width="120" height="90" src="http://s1.dmcdn.net/ucHT/160x90-LYl.jpg" style="border: 2px solid #B9D3FE;"></a><p>ÐÐ¾ÑÑÐµÐºÑÐ¾Ñ Ð½Ðµ Ð½Ð°Ð¼ÐµÑÐµÐ½ Ð¼ÐµÐ½ÑÑÑ ÑÐ¶Ðµ Ð½Ð°Ð¼ÐµÑÐµÐ½Ð½ÑÑ ÐÐ¢-ÑÑÑÐ°ÑÐµÐ³Ð¸Ñ. Ð ÑÐ°ÐºÐ¾Ð¼Ñ Ð²ÑÐ²Ð¾Ð´Ñ Ð¿ÑÐ¸ÑÐ»Ð¸ ÑÑÐ°ÑÑÐ½Ð¸ÐºÐ¸ ÐºÑÑÐ³Ð»Ð¾Ð³Ð¾ ÑÑÐ¾Ð»Ð° CNews Conferences.  <br>Ð ÐµÐ¿Ð¾ÑÑÐ°Ð¶ Ñ http://tv.cnews.ru</p><p>Author: <a href="http://www.dailymotion.com/cnews"><img src="http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338" width="80" height="80" alt="avatar"/>cnews</a><br />Tags: <a href="http://www.dailymotion.com/tag/ÐÑÐ¸Ð·Ð¸Ñ">ÐÑÐ¸Ð·Ð¸Ñ</a> <a href="http://www.dailymotion.com/tag/Ð³Ð¾ÑÑÐµÐºÑÐ¾Ñ">Ð³Ð¾ÑÑÐµÐºÑÐ¾Ñ</a> <a href="http://www.dailymotion.com/tag/ÐÐ¢-ÑÑÑÐ°ÑÐµÐ³Ð¸Ñ">ÐÐ¢-ÑÑÑÐ°ÑÐµÐ³Ð¸Ñ</a> <a href="http://www.dailymotion.com/tag/CNews">CNews</a> <a href="http://www.dailymotion.com/tag/Conferences">Conferences</a> <a href="http://www.dailymotion.com/tag/CNewsTV">CNewsTV</a> <a href="http://www.dailymotion.com/tag/high-tech">high-tech</a> <a href="http://www.dailymotion.com/tag/hi-tech">hi-tech</a> <a href="http://www.dailymotion.com/tag/technology">technology</a> <a href="http://www.dailymotion.com/tag/Ð²ÑÑÐ¾ÐºÐ¸Ðµ">Ð²ÑÑÐ¾ÐºÐ¸Ðµ</a> <a href="http://www.dailymotion.com/tag/ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸">ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸</a> <a href="http://www.dailymotion.com/tag/ÐÐ¢">ÐÐ¢</a> <a href="http://www.dailymotion.com/tag/Ð±Ð¸Ð·Ð½ÐµÑ">Ð±Ð¸Ð·Ð½ÐµÑ</a> <a href="http://www.dailymotion.com/tag/ÑÐµÑÐ½Ð¸ÐºÐ°">ÑÐµÑÐ½Ð¸ÐºÐ°</a> <br />Posted: 26 March 2009<br />Rating: 5.0<br />Votes: 3<br /></p>]]></description>
            <author>rss@dailymotion.com (cnews)</author>
            <itunes:author>cnews</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>ÐÐ¾ÑÑÐµÐºÑÐ¾Ñ Ð½Ðµ Ð½Ð°Ð¼ÐµÑÐµÐ½ Ð¼ÐµÐ½ÑÑÑ ÑÐ¶Ðµ Ð½Ð°Ð¼ÐµÑÐµÐ½Ð½ÑÑ ÐÐ¢-ÑÑÑÐ°ÑÐµÐ³Ð¸Ñ. Ð ÑÐ°ÐºÐ¾Ð¼Ñ Ð²ÑÐ²Ð¾Ð´Ñ Ð¿ÑÐ¸ÑÐ»Ð¸ ÑÑÐ°ÑÑÐ½Ð¸ÐºÐ¸ ÐºÑÑÐ³Ð»Ð¾Ð³Ð¾ ÑÑÐ¾Ð»Ð° CNews Conferences.  Ð ÐµÐ¿Ð¾ÑÑÐ°Ð¶ Ñ http://tv.cnews.ru</itunes:summary>
            <itunes:subtitle>ÐÐ¾ÑÑÐµÐºÑÐ¾Ñ Ð½Ðµ Ð½Ð°Ð¼ÐµÑÐµÐ½ Ð¼ÐµÐ½ÑÑÑ ÑÐ¶Ðµ Ð½Ð°Ð¼ÐµÑÐµÐ½Ð½ÑÑ ÐÐ¢-ÑÑÑÐ°ÑÐµÐ³Ð¸Ñ. Ð ÑÐ°ÐºÐ¾Ð¼Ñ Ð²ÑÐ²Ð¾Ð´Ñ Ð¿ÑÐ¸ÑÐ»Ð¸ ÑÑÐ°ÑÑÐ½Ð¸ÐºÐ¸ ÐºÑÑÐ³Ð»Ð¾Ð³Ð¾ ÑÑÐ¾Ð»Ð° CNews Conferences.  Ð ÐµÐ¿Ð¾ÑÑÐ°Ð¶ Ñ http://tv.cnews.ru</itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>3</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x8sei0_%D0%BA%D1%80%D0%B8%D0%B7%D0%B8%D1%81-%D0%BD%D0%B5-%D0%BF%D0%BE%D0%BC%D0%B5%D1%88%D0%B0%D0%B5%D1%82-%D0%B2%D0%BD%D0%B5%D0%B4%D1%80%D0%B5%D0%BD%D0%B8%D1%8E-%D0%B8%D1%82-%D0%B2-%D0%B3_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/cnews" type="application/rss+xml"/>
            <dm:views>173</dm:views>
            <dm:comments>0</dm:comments>
            <dm:favorites>0</dm:favorites>
            <dm:id>x8sei0</dm:id>
            <dm:author>cnews</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x8sei0?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=6ieezi7g3g1f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=0f217ce1de786dfd0575da24c9d42829</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Thu, 26 Mar 2009 20:04:23 +0100</pubDate>
            <guid>http://www.dailymotion.com/video/x8sei0_%D0%BA%D1%80%D0%B8%D0%B7%D0%B8%D1%81-%D0%BD%D0%B5-%D0%BF%D0%BE%D0%BC%D0%B5%D1%88%D0%B0%D0%B5%D1%82-%D0%B2%D0%BD%D0%B5%D0%B4%D1%80%D0%B5%D0%BD%D0%B8%D1%8E-%D0%B8%D1%82-%D0%B2-%D0%B3_tech</guid>
            <media:title>ÐÑÐ¸Ð·Ð¸Ñ Ð½Ðµ Ð¿Ð¾Ð¼ÐµÑÐ°ÐµÑ Ð²Ð½ÐµÐ´ÑÐµÐ½Ð¸Ñ ÐÐ¢ Ð² Ð³Ð¾ÑÑÐµÐºÑÐ¾ÑÐµ</media:title>
            <media:credit>cnews</media:credit>
            <media:thumbnail url="http://s1.dmcdn.net/ucHT/x240-uVP.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x8sei0_%D0%BA%D1%80%D0%B8%D0%B7%D0%B8%D1%81-%D0%BD%D0%B5-%D0%BF%D0%BE%D0%BC%D0%B5%D1%88%D0%B0%D0%B5%D1%82-%D0%B2%D0%BD%D0%B5%D0%B4%D1%80%D0%B5%D0%BD%D0%B8%D1%8E-%D0%B8%D1%82-%D0%B2-%D0%B3_tech" height="276" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x8sei0"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x8sei0" type="text/html" duration="280" width="480" height="276"/>
                <media:content url="http://www.dailymotion.com/swf/video/x8sei0" type="application/x-shockwave-flash" duration="280" width="480" height="276"/>
            </media:group>
            <itunes:keywords>ÐÑÐ¸Ð·Ð¸Ñ, Ð³Ð¾ÑÑÐµÐºÑÐ¾Ñ, ÐÐ¢-ÑÑÑÐ°ÑÐµÐ³Ð¸Ñ, CNews, Conferences, CNewsTV, high-tech, hi-tech, technology, Ð²ÑÑÐ¾ÐºÐ¸Ðµ, ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸, ÐÐ¢, Ð±Ð¸Ð·Ð½ÐµÑ, ÑÐµÑÐ½Ð¸ÐºÐ°</itunes:keywords>
            <media:category label="ÐÑÐ¸Ð·Ð¸Ñ">ÐÑÐ¸Ð·Ð¸Ñ</media:category>
            <media:category label="Ð³Ð¾ÑÑÐµÐºÑÐ¾Ñ">Ð³Ð¾ÑÑÐµÐºÑÐ¾Ñ</media:category>
            <media:category label="ÐÐ¢-ÑÑÑÐ°ÑÐµÐ³Ð¸Ñ">ÐÐ¢-ÑÑÑÐ°ÑÐµÐ³Ð¸Ñ</media:category>
            <media:category label="CNews">CNews</media:category>
            <media:category label="Conferences">Conferences</media:category>
            <media:category label="CNewsTV">CNewsTV</media:category>
            <media:category label="high-tech">high-tech</media:category>
            <media:category label="hi-tech">hi-tech</media:category>
            <media:category label="technology">technology</media:category>
            <media:category label="Ð²ÑÑÐ¾ÐºÐ¸Ðµ">Ð²ÑÑÐ¾ÐºÐ¸Ðµ</media:category>
            <media:category label="ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸">ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸</media:category>
            <media:category label="ÐÐ¢">ÐÐ¢</media:category>
            <media:category label="Ð±Ð¸Ð·Ð½ÐµÑ">Ð±Ð¸Ð·Ð½ÐµÑ</media:category>
            <media:category label="ÑÐµÑÐ½Ð¸ÐºÐ°">ÑÐµÑÐ½Ð¸ÐºÐ°</media:category>
        </item>
        <item>
            <title>Ð§ÐµÐ³Ð¾ Microsoft Ð¶Ð´ÐµÑ Ð¾Ñ Internet Explorer 8</title>
            <link>http://www.dailymotion.com/video/x8uqpb_%D1%87%D0%B5%D0%B3%D0%BE-microsoft-%D0%B6%D0%B4%D0%B5%D1%82-%D0%BE%D1%82-internet-exp_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x8uqpb_%D1%87%D0%B5%D0%B3%D0%BE-microsoft-%D0%B6%D0%B4%D0%B5%D1%82-%D0%BE%D1%82-internet-exp_tech"><img align="right" width="120" height="90" src="http://s1.dmcdn.net/ENb5/160x90-4WD.jpg" style="border: 2px solid #B9D3FE;"></a><p></p><p>Author: <a href="http://www.dailymotion.com/Openbiz"><img src="http://static1.dmcdn.net/images/avatar/female/80x80.jpg.v69eb35393aa934cb9" width="80" height="80" alt="avatar"/>Openbiz</a><br />Tags: <a href="http://www.dailymotion.com/tag/Microsoft">Microsoft</a> <a href="http://www.dailymotion.com/tag/Internet">Internet</a> <a href="http://www.dailymotion.com/tag/Explorer">Explorer</a> <a href="http://www.dailymotion.com/tag/Ukraine">Ukraine</a> <a href="http://www.dailymotion.com/tag/openbiz">openbiz</a> <a href="http://www.dailymotion.com/tag/openbizcomua">openbizcomua</a> <a href="http://www.dailymotion.com/tag/Ð±ÑÐ°ÑÐ·ÐµÑ">Ð±ÑÐ°ÑÐ·ÐµÑ</a> <a href="http://www.dailymotion.com/tag/Ð¸Ð½ÑÐµÑÐ½ÐµÑ">Ð¸Ð½ÑÐµÑÐ½ÐµÑ</a> <a href="http://www.dailymotion.com/tag/ÑÐºÑÐ°Ð¸Ð½Ð°">ÑÐºÑÐ°Ð¸Ð½Ð°</a> <br />Posted: 02 April 2009<br />Rating: 5.0<br />Votes: 1<br /></p>]]></description>
            <author>rss@dailymotion.com (Openbiz)</author>
            <itunes:author>Openbiz</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary></itunes:summary>
            <itunes:subtitle></itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>1</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x8uqpb_%D1%87%D0%B5%D0%B3%D0%BE-microsoft-%D0%B6%D0%B4%D0%B5%D1%82-%D0%BE%D1%82-internet-exp_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/Openbiz" type="application/rss+xml"/>
            <dm:views>306</dm:views>
            <dm:comments>0</dm:comments>
            <dm:favorites>0</dm:favorites>
            <dm:id>x8uqpb</dm:id>
            <dm:author>Openbiz</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x8uqpb?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=exx4tsxd771f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=57935a13a8dc82028aa109b190efe4e0</dm:loggerURL>
            <dm:authorAvatar>http://static1.dmcdn.net/images/avatar/female/80x80.jpg.v69eb35393aa934cb9</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Thu, 02 Apr 2009 11:56:25 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x8uqpb_%D1%87%D0%B5%D0%B3%D0%BE-microsoft-%D0%B6%D0%B4%D0%B5%D1%82-%D0%BE%D1%82-internet-exp_tech</guid>
            <media:title>Ð§ÐµÐ³Ð¾ Microsoft Ð¶Ð´ÐµÑ Ð¾Ñ Internet Explorer 8</media:title>
            <media:credit>Openbiz</media:credit>
            <media:thumbnail url="http://s1.dmcdn.net/ENb5/x240-9l2.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x8uqpb_%D1%87%D0%B5%D0%B3%D0%BE-microsoft-%D0%B6%D0%B4%D0%B5%D1%82-%D0%BE%D1%82-internet-exp_tech" height="276" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x8uqpb"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x8uqpb" type="text/html" duration="98" width="480" height="276"/>
                <media:content url="http://www.dailymotion.com/swf/video/x8uqpb" type="application/x-shockwave-flash" duration="98" width="480" height="276"/>
            </media:group>
            <itunes:keywords>Microsoft, Internet, Explorer, Ukraine, openbiz, openbizcomua, Ð±ÑÐ°ÑÐ·ÐµÑ, Ð¸Ð½ÑÐµÑÐ½ÐµÑ, ÑÐºÑÐ°Ð¸Ð½Ð°</itunes:keywords>
            <media:category label="Microsoft">Microsoft</media:category>
            <media:category label="Internet">Internet</media:category>
            <media:category label="Explorer">Explorer</media:category>
            <media:category label="Ukraine">Ukraine</media:category>
            <media:category label="openbiz">openbiz</media:category>
            <media:category label="openbizcomua">openbizcomua</media:category>
            <media:category label="Ð±ÑÐ°ÑÐ·ÐµÑ">Ð±ÑÐ°ÑÐ·ÐµÑ</media:category>
            <media:category label="Ð¸Ð½ÑÐµÑÐ½ÐµÑ">Ð¸Ð½ÑÐµÑÐ½ÐµÑ</media:category>
            <media:category label="ÑÐºÑÐ°Ð¸Ð½Ð°">ÑÐºÑÐ°Ð¸Ð½Ð°</media:category>
        </item>
        <item>
            <title>MacBook Pro: cÐ°Ð¼ÑÐ¹ Ð´Ð¾ÑÐ¾Ð³Ð¾Ð¹ Ð½Ð¾ÑÑÐ±ÑÐº Ð² Ð Ð¾ÑÑÐ¸Ð¸</title>
            <link>http://www.dailymotion.com/video/x8thgj_macbook-pro-c%D0%B0%D0%BC%D1%8B%D0%B9-%D0%B4%D0%BE%D1%80%D0%BE%D0%B3%D0%BE%D0%B9-%D0%BD%D0%BE%D1%83%D1%82%D0%B1%D1%83%D0%BA-%D0%B2_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x8thgj_macbook-pro-c%D0%B0%D0%BC%D1%8B%D0%B9-%D0%B4%D0%BE%D1%80%D0%BE%D0%B3%D0%BE%D0%B9-%D0%BD%D0%BE%D1%83%D1%82%D0%B1%D1%83%D0%BA-%D0%B2_tech"><img align="right" width="120" height="90" src="http://s1.dmcdn.net/XMgG/160x90-X3j.jpg" style="border: 2px solid #B9D3FE;"></a><p>ÐÐ¾ÐºÐ° Ð±Ð¾Ð»ÑÑÐ¸Ð½ÑÑÐ²Ð¾ Ð¿ÑÐ¾Ð¸Ð·Ð²Ð¾Ð´Ð¸ÑÐµÐ»ÐµÐ¹ Ð»ÑÐ¿ÑÐ¾Ð¿Ð¾Ð² Ð²ÐºÐ»ÑÑÐ°ÑÑ Ð² ÑÐ²Ð¾Ð¸ Ð»Ð¸Ð½ÐµÐ¹ÐºÐ¸ Ð´ÐµÑÑÐ²ÑÐµ Ð½ÐµÑÐ±ÑÐºÐ¸, Apple Ð½Ðµ ÑÐ´Ð°ÑÑÑÑ Ð¸ Ð²ÑÐ¿ÑÑÐºÐ°ÐµÑ Ð½Ð° ÑÑÐ½Ð¾Ðº ÑÐ°Ð¼ÑÐ¹ Ð´Ð¾ÑÐ¾Ð³Ð¾Ð¹ Ð½Ð° ÑÐµÐ³Ð¾Ð´Ð½ÑÑÐ½Ð¸Ð¹ Ð´ÐµÐ½Ñ Ð¿Ð¾ÑÑÐ°ÑÐ¸Ð²Ð½ÑÐ¹ ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑ. ÐÑ, ÑÐ°Ð·ÑÐ¼ÐµÐµÑÑÑ, ÐµÑÐ»Ð¸ Ð½Ðµ Ð±ÑÐ°ÑÑ Ð² ÑÐ°ÑÑÑÑ Ð²ÑÐµÐ²Ð¾Ð·Ð¼Ð¾Ð¶Ð½ÑÐµ Ð¿ÐµÑÐ²ÐµÑÑÐ¸Ð¸ ÑÐ¾ ÑÑÑÐ°Ð·Ð°Ð¼Ð¸ Ð¸ Ð¿Ð¾Ð·Ð¾Ð»Ð¾ÑÐ¾Ð¹. Ð Ð Ð¾ÑÑÐ¸Ð¸ ÑÐ°ÐºÐ¾Ð¹ Ð²Ð¾Ñ MacBook Pro Ð¿Ð¾ÑÐ»ÐµÐ´Ð½ÐµÐ¹ Ð²ÐµÑÑÐ¸Ð¸ Ð¸ Ð² ÑÐ°Ð¼Ð¾Ð¹ Ð½Ð°Ð²Ð¾ÑÐ¾ÑÐµÐ½Ð½Ð¾Ð¹ ÐºÐ¾Ð¼Ð¿Ð»ÐµÐºÑÐ°ÑÐ¸Ð¸ ÑÑÐ¾Ð¸Ñ Ð¿Ð¾ÑÑÐ´ÐºÐ° 170 ÑÑÑ. ÑÑÐ±. Ð¤Ð°ÐºÑÐ¸ÑÐµÑÐºÐ¸, ÑÑÐ¾ ÑÐµÐ½Ð° Ð½ÐµÐ´Ð¾ÑÐ¾Ð³Ð¾Ð³Ð¾ Ð°Ð²ÑÐ¾Ð¼Ð¾Ð±Ð¸Ð»Ñ. Ð§ÑÐ¾ Ð¶Ðµ Ð¿ÑÐµÐ´Ð»Ð°Ð³Ð°ÐµÑÑÑ Ð¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°ÑÐµÐ»Ñ Ð·Ð° ÑÐ°ÐºÐ¸Ðµ Ð±ÐµÑÐµÐ½ÑÐµ Ð´ÐµÐ½ÑÐ³Ð¸? <br>Ð ÐµÐ¿Ð¾ÑÑÐ°Ð¶ Ñ http://tv.cnews.ru</p><p>Author: <a href="http://www.dailymotion.com/cnews"><img src="http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338" width="80" height="80" alt="avatar"/>cnews</a><br />Tags: <a href="http://www.dailymotion.com/tag/MacBook">MacBook</a> <a href="http://www.dailymotion.com/tag/Pro">Pro</a> <a href="http://www.dailymotion.com/tag/Ð½Ð¾ÑÑÐ±ÑÐº">Ð½Ð¾ÑÑÐ±ÑÐº</a> <a href="http://www.dailymotion.com/tag/Ð»ÑÐ¿ÑÐ¾Ð¿">Ð»ÑÐ¿ÑÐ¾Ð¿</a> <a href="http://www.dailymotion.com/tag/Ð½ÐµÑÐ±ÑÐºÐ¸">Ð½ÐµÑÐ±ÑÐºÐ¸</a> <a href="http://www.dailymotion.com/tag/Apple">Apple</a> <a href="http://www.dailymotion.com/tag/ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑ">ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑ</a> <a href="http://www.dailymotion.com/tag/CNewsTV">CNewsTV</a> <a href="http://www.dailymotion.com/tag/high-tech">high-tech</a> <a href="http://www.dailymotion.com/tag/hi-tech">hi-tech</a> <a href="http://www.dailymotion.com/tag/technology">technology</a> <a href="http://www.dailymotion.com/tag/Ð²ÑÑÐ¾ÐºÐ¸Ðµ">Ð²ÑÑÐ¾ÐºÐ¸Ðµ</a> <a href="http://www.dailymotion.com/tag/ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸">ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸</a> <a href="http://www.dailymotion.com/tag/ÐÐ¢">ÐÐ¢</a> <a href="http://www.dailymotion.com/tag/Ð±Ð¸Ð·Ð½ÐµÑ">Ð±Ð¸Ð·Ð½ÐµÑ</a> <br />Posted: 29 March 2009<br />Rating: 5.0<br />Votes: 1<br /></p>]]></description>
            <author>rss@dailymotion.com (cnews)</author>
            <itunes:author>cnews</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>ÐÐ¾ÐºÐ° Ð±Ð¾Ð»ÑÑÐ¸Ð½ÑÑÐ²Ð¾ Ð¿ÑÐ¾Ð¸Ð·Ð²Ð¾Ð´Ð¸ÑÐµÐ»ÐµÐ¹ Ð»ÑÐ¿ÑÐ¾Ð¿Ð¾Ð² Ð²ÐºÐ»ÑÑÐ°ÑÑ Ð² ÑÐ²Ð¾Ð¸ Ð»Ð¸Ð½ÐµÐ¹ÐºÐ¸ Ð´ÐµÑÑÐ²ÑÐµ Ð½ÐµÑÐ±ÑÐºÐ¸, Apple Ð½Ðµ ÑÐ´Ð°ÑÑÑÑ Ð¸ Ð²ÑÐ¿ÑÑÐºÐ°ÐµÑ Ð½Ð° ÑÑÐ½Ð¾Ðº ÑÐ°Ð¼ÑÐ¹ Ð´Ð¾ÑÐ¾Ð³Ð¾Ð¹ Ð½Ð° ÑÐµÐ³Ð¾Ð´Ð½ÑÑÐ½Ð¸Ð¹ Ð´ÐµÐ½Ñ Ð¿Ð¾ÑÑÐ°ÑÐ¸Ð²Ð½ÑÐ¹ ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑ. ÐÑ, ÑÐ°Ð·ÑÐ¼ÐµÐµÑÑÑ, ÐµÑÐ»Ð¸ Ð½Ðµ Ð±ÑÐ°ÑÑ Ð² ÑÐ°ÑÑÑÑ Ð²ÑÐµÐ²Ð¾Ð·Ð¼Ð¾Ð¶Ð½ÑÐµ Ð¿ÐµÑÐ²ÐµÑÑÐ¸Ð¸ ÑÐ¾ ÑÑÑÐ°Ð·Ð°Ð¼Ð¸ Ð¸...</itunes:summary>
            <itunes:subtitle>ÐÐ¾ÐºÐ° Ð±Ð¾Ð»ÑÑÐ¸Ð½ÑÑÐ²Ð¾ Ð¿ÑÐ¾Ð¸Ð·Ð²Ð¾Ð´Ð¸ÑÐµÐ»ÐµÐ¹ Ð»ÑÐ¿ÑÐ¾Ð¿Ð¾Ð² Ð²ÐºÐ»ÑÑÐ°ÑÑ Ð² ÑÐ²Ð¾Ð¸ Ð»Ð¸Ð½ÐµÐ¹ÐºÐ¸ Ð´ÐµÑÑÐ²ÑÐµ Ð½ÐµÑÐ±ÑÐºÐ¸, Apple Ð½Ðµ ÑÐ´Ð°ÑÑÑÑ Ð¸ Ð²ÑÐ¿ÑÑÐºÐ°ÐµÑ Ð½Ð° ÑÑÐ½Ð¾Ðº ÑÐ°Ð¼ÑÐ¹ Ð´Ð¾ÑÐ¾Ð³Ð¾Ð¹ Ð½Ð° ÑÐµÐ³Ð¾Ð´Ð½ÑÑÐ½Ð¸Ð¹ Ð´ÐµÐ½Ñ Ð¿Ð¾ÑÑÐ°ÑÐ¸Ð²Ð½ÑÐ¹ ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑ. ÐÑ, ÑÐ°Ð·ÑÐ¼ÐµÐµÑÑÑ, ÐµÑÐ»Ð¸ Ð½Ðµ Ð±ÑÐ°ÑÑ Ð² ÑÐ°ÑÑÑÑ Ð²ÑÐµÐ²Ð¾Ð·Ð¼Ð¾Ð¶Ð½ÑÐµ Ð¿ÐµÑÐ²ÐµÑÑÐ¸Ð¸ ÑÐ¾ ÑÑÑÐ°Ð·Ð°Ð¼Ð¸ Ð¸...</itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>1</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x8thgj_macbook-pro-c%D0%B0%D0%BC%D1%8B%D0%B9-%D0%B4%D0%BE%D1%80%D0%BE%D0%B3%D0%BE%D0%B9-%D0%BD%D0%BE%D1%83%D1%82%D0%B1%D1%83%D0%BA-%D0%B2_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/cnews" type="application/rss+xml"/>
            <dm:views>1755</dm:views>
            <dm:comments>0</dm:comments>
            <dm:favorites>1</dm:favorites>
            <dm:id>x8thgj</dm:id>
            <dm:author>cnews</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x8thgj?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=etrdkiquld1f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=6665f054e171cd3fbfda2371316beda1</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Sun, 29 Mar 2009 21:52:32 +0200</pubDate>
            <guid>http://www.dailymotion.com/video/x8thgj_macbook-pro-c%D0%B0%D0%BC%D1%8B%D0%B9-%D0%B4%D0%BE%D1%80%D0%BE%D0%B3%D0%BE%D0%B9-%D0%BD%D0%BE%D1%83%D1%82%D0%B1%D1%83%D0%BA-%D0%B2_tech</guid>
            <media:title>MacBook Pro: cÐ°Ð¼ÑÐ¹ Ð´Ð¾ÑÐ¾Ð³Ð¾Ð¹ Ð½Ð¾ÑÑÐ±ÑÐº Ð² Ð Ð¾ÑÑÐ¸Ð¸</media:title>
            <media:credit>cnews</media:credit>
            <media:thumbnail url="http://s1.dmcdn.net/XMgG/x240-USA.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x8thgj_macbook-pro-c%D0%B0%D0%BC%D1%8B%D0%B9-%D0%B4%D0%BE%D1%80%D0%BE%D0%B3%D0%BE%D0%B9-%D0%BD%D0%BE%D1%83%D1%82%D0%B1%D1%83%D0%BA-%D0%B2_tech" height="276" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x8thgj"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x8thgj" type="text/html" duration="107" width="480" height="276"/>
                <media:content url="http://www.dailymotion.com/swf/video/x8thgj" type="application/x-shockwave-flash" duration="107" width="480" height="276"/>
            </media:group>
            <itunes:keywords>MacBook, Pro, Ð½Ð¾ÑÑÐ±ÑÐº, Ð»ÑÐ¿ÑÐ¾Ð¿, Ð½ÐµÑÐ±ÑÐºÐ¸, Apple, ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑ, CNewsTV, high-tech, hi-tech, technology, Ð²ÑÑÐ¾ÐºÐ¸Ðµ, ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸, ÐÐ¢, Ð±Ð¸Ð·Ð½ÐµÑ</itunes:keywords>
            <media:category label="MacBook">MacBook</media:category>
            <media:category label="Pro">Pro</media:category>
            <media:category label="Ð½Ð¾ÑÑÐ±ÑÐº">Ð½Ð¾ÑÑÐ±ÑÐº</media:category>
            <media:category label="Ð»ÑÐ¿ÑÐ¾Ð¿">Ð»ÑÐ¿ÑÐ¾Ð¿</media:category>
            <media:category label="Ð½ÐµÑÐ±ÑÐºÐ¸">Ð½ÐµÑÐ±ÑÐºÐ¸</media:category>
            <media:category label="Apple">Apple</media:category>
            <media:category label="ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑ">ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑ</media:category>
            <media:category label="CNewsTV">CNewsTV</media:category>
            <media:category label="high-tech">high-tech</media:category>
            <media:category label="hi-tech">hi-tech</media:category>
            <media:category label="technology">technology</media:category>
            <media:category label="Ð²ÑÑÐ¾ÐºÐ¸Ðµ">Ð²ÑÑÐ¾ÐºÐ¸Ðµ</media:category>
            <media:category label="ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸">ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸</media:category>
            <media:category label="ÐÐ¢">ÐÐ¢</media:category>
            <media:category label="Ð±Ð¸Ð·Ð½ÐµÑ">Ð±Ð¸Ð·Ð½ÐµÑ</media:category>
        </item>
        <item>
            <title>ÐÑÐ´ÑÑÐµÐµ Ð³Ð»Ð°Ð·Ð°Ð¼Ð¸ Microsoft</title>
            <link>http://www.dailymotion.com/video/x8qzyh_%D0%B1%D1%83%D0%B4%D1%83%D1%89%D0%B5%D0%B5-%D0%B3%D0%BB%D0%B0%D0%B7%D0%B0%D0%BC%D0%B8-microsoft_tech</link>
            <description><![CDATA[<a href="http://www.dailymotion.com/video/x8qzyh_%D0%B1%D1%83%D0%B4%D1%83%D1%89%D0%B5%D0%B5-%D0%B3%D0%BB%D0%B0%D0%B7%D0%B0%D0%BC%D0%B8-microsoft_tech"><img align="right" width="120" height="90" src="http://s2.dmcdn.net/XTcV/160x90-hgd.jpg" style="border: 2px solid #B9D3FE;"></a><p>Ð¡Ð¾Ð³Ð»Ð°ÑÐ½Ð¾ Ð²Ð¸Ð´ÐµÐ½Ð¸Ñ ÑÐ¾ÑÑÐ²ÐµÑÐ½Ð¾Ð³Ð¾ Ð³Ð¸Ð³Ð°Ð½ÑÐ°, ÑÐ¶Ðµ Ðº 2019 Ð³. ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑÑ Ð¸Ð·Ð¼ÐµÐ½ÑÑÑÑ Ð´Ð¾ Ð½ÐµÑÐ·Ð½Ð°Ð²Ð°ÐµÐ¼Ð¾ÑÑÐ¸. ÐÐµÑÐ¸ÑÐµÑÐ¸Ð¹Ð½ÑÐµ ÑÑÑÑÐ¾Ð¹ÑÑÐ²Ð° ÑÐ¹Ð´ÑÑ Ð² Ð¿ÑÐ¾ÑÐ»Ð¾Ðµ, Ð¾ÑÑÐ°Ð²Ð¸Ð² Ð¼ÐµÑÑÐ¾ ÑÐµÐ½ÑÐ¾ÑÐ½ÑÐ¼ ÑÐºÑÐ°Ð½Ð°Ð¼. Ð Ð°Ð±Ð¾ÑÐ°ÑÑ Ñ Ð¸Ð½ÑÐ¾ÑÐ¼Ð°ÑÐ¸ÐµÐ¹ Ð±ÑÐ´ÐµÑ Ð½ÐµÐ²ÐµÑÐ¾ÑÑÐ½Ð¾ Ð¿ÑÐ¾ÑÑÐ¾, ÐºÐ°Ðº ÐµÑÐ»Ð¸ Ð±Ñ ÐµÐµ Ð¼Ð¾Ð¶Ð½Ð¾ Ð±ÑÐ»Ð¾ Ð²Ð·ÑÑÑ Ð² ÑÑÐºÑ Ð¸ Ð¿Ð¾Ð¼ÐµÑÑÐ¸ÑÑ ÐºÑÐ´Ð° ÑÐ³Ð¾Ð´Ð½Ð¾.   <br>Ð ÐµÐ¿Ð¾ÑÑÐ°Ð¶ Ñ http://tv.cnews.ru</p><p>Author: <a href="http://www.dailymotion.com/cnews"><img src="http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338" width="80" height="80" alt="avatar"/>cnews</a><br />Tags: <a href="http://www.dailymotion.com/tag/Microsoft">Microsoft</a> <a href="http://www.dailymotion.com/tag/ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸">ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸</a> <a href="http://www.dailymotion.com/tag/ÑÐµÑÐ½Ð¸ÐºÐ°">ÑÐµÑÐ½Ð¸ÐºÐ°</a> <a href="http://www.dailymotion.com/tag/ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑ">ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑ</a> <a href="http://www.dailymotion.com/tag/ÐÐ">ÐÐ</a> <a href="http://www.dailymotion.com/tag/ÑÐ¾ÑÑ">ÑÐ¾ÑÑ</a> <a href="http://www.dailymotion.com/tag/ÑÐºÑÐ°Ð½">ÑÐºÑÐ°Ð½</a> <a href="http://www.dailymotion.com/tag/Ð¿ÐµÑÐ¸ÑÐµÑÐ¸Ñ">Ð¿ÐµÑÐ¸ÑÐµÑÐ¸Ñ</a> <a href="http://www.dailymotion.com/tag/ÑÐµÐ½ÑÐ¾ÑÐ½ÑÐ¹">ÑÐµÐ½ÑÐ¾ÑÐ½ÑÐ¹</a> <a href="http://www.dailymotion.com/tag/CNewsTV">CNewsTV</a> <a href="http://www.dailymotion.com/tag/high-tech">high-tech</a> <a href="http://www.dailymotion.com/tag/hi-tech">hi-tech</a> <a href="http://www.dailymotion.com/tag/technology">technology</a> <a href="http://www.dailymotion.com/tag/Ð²ÑÑÐ¾ÐºÐ¸Ðµ">Ð²ÑÑÐ¾ÐºÐ¸Ðµ</a> <a href="http://www.dailymotion.com/tag/ÐÐ¢">ÐÐ¢</a> <a href="http://www.dailymotion.com/tag/Ð±Ð¸Ð·Ð½ÐµÑ">Ð±Ð¸Ð·Ð½ÐµÑ</a> <br />Posted: 22 March 2009<br />Rating: 5.0<br />Votes: 4<br /></p>]]></description>
            <author>rss@dailymotion.com (cnews)</author>
            <itunes:author>cnews</itunes:author>
            <itunes:explicit>no</itunes:explicit>
            <itunes:summary>Ð¡Ð¾Ð³Ð»Ð°ÑÐ½Ð¾ Ð²Ð¸Ð´ÐµÐ½Ð¸Ñ ÑÐ¾ÑÑÐ²ÐµÑÐ½Ð¾Ð³Ð¾ Ð³Ð¸Ð³Ð°Ð½ÑÐ°, ÑÐ¶Ðµ Ðº 2019 Ð³. ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑÑ Ð¸Ð·Ð¼ÐµÐ½ÑÑÑÑ Ð´Ð¾ Ð½ÐµÑÐ·Ð½Ð°Ð²Ð°ÐµÐ¼Ð¾ÑÑÐ¸. ÐÐµÑÐ¸ÑÐµÑÐ¸Ð¹Ð½ÑÐµ ÑÑÑÑÐ¾Ð¹ÑÑÐ²Ð° ÑÐ¹Ð´ÑÑ Ð² Ð¿ÑÐ¾ÑÐ»Ð¾Ðµ, Ð¾ÑÑÐ°Ð²Ð¸Ð² Ð¼ÐµÑÑÐ¾ ÑÐµÐ½ÑÐ¾ÑÐ½ÑÐ¼ ÑÐºÑÐ°Ð½Ð°Ð¼. Ð Ð°Ð±Ð¾ÑÐ°ÑÑ Ñ Ð¸Ð½ÑÐ¾ÑÐ¼Ð°ÑÐ¸ÐµÐ¹ Ð±ÑÐ´ÐµÑ Ð½ÐµÐ²ÐµÑÐ¾ÑÑÐ½Ð¾ Ð¿ÑÐ¾ÑÑÐ¾, ÐºÐ°Ðº ÐµÑÐ»Ð¸ Ð±Ñ ÐµÐµ Ð¼Ð¾Ð¶Ð½Ð¾ Ð±ÑÐ»Ð¾ Ð²Ð·ÑÑÑ Ð² ÑÑÐºÑ...</itunes:summary>
            <itunes:subtitle>Ð¡Ð¾Ð³Ð»Ð°ÑÐ½Ð¾ Ð²Ð¸Ð´ÐµÐ½Ð¸Ñ ÑÐ¾ÑÑÐ²ÐµÑÐ½Ð¾Ð³Ð¾ Ð³Ð¸Ð³Ð°Ð½ÑÐ°, ÑÐ¶Ðµ Ðº 2019 Ð³. ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑÑ Ð¸Ð·Ð¼ÐµÐ½ÑÑÑÑ Ð´Ð¾ Ð½ÐµÑÐ·Ð½Ð°Ð²Ð°ÐµÐ¼Ð¾ÑÑÐ¸. ÐÐµÑÐ¸ÑÐµÑÐ¸Ð¹Ð½ÑÐµ ÑÑÑÑÐ¾Ð¹ÑÑÐ²Ð° ÑÐ¹Ð´ÑÑ Ð² Ð¿ÑÐ¾ÑÐ»Ð¾Ðµ, Ð¾ÑÑÐ°Ð²Ð¸Ð² Ð¼ÐµÑÑÐ¾ ÑÐµÐ½ÑÐ¾ÑÐ½ÑÐ¼ ÑÐºÑÐ°Ð½Ð°Ð¼. Ð Ð°Ð±Ð¾ÑÐ°ÑÑ Ñ Ð¸Ð½ÑÐ¾ÑÐ¼Ð°ÑÐ¸ÐµÐ¹ Ð±ÑÐ´ÐµÑ Ð½ÐµÐ²ÐµÑÐ¾ÑÑÐ½Ð¾ Ð¿ÑÐ¾ÑÑÐ¾, ÐºÐ°Ðº ÐµÑÐ»Ð¸ Ð±Ñ ÐµÐµ Ð¼Ð¾Ð¶Ð½Ð¾ Ð±ÑÐ»Ð¾ Ð²Ð·ÑÑÑ Ð² ÑÑÐºÑ...</itunes:subtitle>
            <dm:videorating>5.0</dm:videorating>
            <dm:videovotes>4</dm:videovotes>
            <dm:link rel="uql" href="http://www.dailymotion.com/rss/video/x8qzyh_%D0%B1%D1%83%D0%B4%D1%83%D1%89%D0%B5%D0%B5-%D0%B3%D0%BB%D0%B0%D0%B7%D0%B0%D0%BC%D0%B8-microsoft_tech" type="application/rss+xml"/>
            <dm:link rel="userProfile" href="http://www.dailymotion.com/rss/cnews" type="application/rss+xml"/>
            <dm:views>1694</dm:views>
            <dm:comments>1</dm:comments>
            <dm:favorites>4</dm:favorites>
            <dm:id>x8qzyh</dm:id>
            <dm:author>cnews</dm:author>
            <dm:loggerURL>http://www.dailymotion.com/logger/video/access/x8qzyh?session_id=&amp;referer=&amp;country=US&amp;lon=-77.6024000000000&amp;lat=43.1858000000000&amp;user_agent=Mozilla%2F5.0+%28X11%3B+Linux+x86_64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Ubuntu+Chromium%2F28.0.1500.71+Chrome%2F28.0.1500.71+Safari%2F537.36&amp;key=8rjajhbns01f7wuknmr6emo&amp;v=5202a290&amp;i=b89975c7&amp;h=4b79e1b456cd81f5989683da65daa045</dm:loggerURL>
            <dm:authorAvatar>http://static2.dmcdn.net/static/user/203/495/19594302:avatar_medium.jpg?20080923081338</dm:authorAvatar>
            <dm:relativeDate>posted 4 years ago</dm:relativeDate>
            <dm:channels>tech</dm:channels>
            <pubDate>Sun, 22 Mar 2009 22:06:21 +0100</pubDate>
            <guid>http://www.dailymotion.com/video/x8qzyh_%D0%B1%D1%83%D0%B4%D1%83%D1%89%D0%B5%D0%B5-%D0%B3%D0%BB%D0%B0%D0%B7%D0%B0%D0%BC%D0%B8-microsoft_tech</guid>
            <media:title>ÐÑÐ´ÑÑÐµÐµ Ð³Ð»Ð°Ð·Ð°Ð¼Ð¸ Microsoft</media:title>
            <media:credit>cnews</media:credit>
            <media:thumbnail url="http://s2.dmcdn.net/XTcV/x240-j8o.jpg" height="240" width="320" />
            <media:player url="http://www.dailymotion.com/video/x8qzyh_%D0%B1%D1%83%D0%B4%D1%83%D1%89%D0%B5%D0%B5-%D0%B3%D0%BB%D0%B0%D0%B7%D0%B0%D0%BC%D0%B8-microsoft_tech" height="276" width="480"><![CDATA[<iframe frameborder="0" width="480" height="270" src="http://www.dailymotion.com/embed/video/x8qzyh"></iframe>]]></media:player>
            <media:group>
                <media:content url="http://www.dailymotion.com/embed/video/x8qzyh" type="text/html" duration="343" width="480" height="276"/>
                <media:content url="http://www.dailymotion.com/swf/video/x8qzyh" type="application/x-shockwave-flash" duration="343" width="480" height="276"/>
            </media:group>
            <itunes:keywords>Microsoft, ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸, ÑÐµÑÐ½Ð¸ÐºÐ°, ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑ, ÐÐ, ÑÐ¾ÑÑ, ÑÐºÑÐ°Ð½, Ð¿ÐµÑÐ¸ÑÐµÑÐ¸Ñ, ÑÐµÐ½ÑÐ¾ÑÐ½ÑÐ¹, CNewsTV, high-tech, hi-tech, technology, Ð²ÑÑÐ¾ÐºÐ¸Ðµ, ÐÐ¢, Ð±Ð¸Ð·Ð½ÐµÑ</itunes:keywords>
            <media:category label="Microsoft">Microsoft</media:category>
            <media:category label="ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸">ÑÐµÑÐ½Ð¾Ð»Ð¾Ð³Ð¸Ð¸</media:category>
            <media:category label="ÑÐµÑÐ½Ð¸ÐºÐ°">ÑÐµÑÐ½Ð¸ÐºÐ°</media:category>
            <media:category label="ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑ">ÐºÐ¾Ð¼Ð¿ÑÑÑÐµÑ</media:category>
            <media:category label="ÐÐ">ÐÐ</media:category>
            <media:category label="ÑÐ¾ÑÑ">ÑÐ¾ÑÑ</media:category>
            <media:category label="ÑÐºÑÐ°Ð½">ÑÐºÑÐ°Ð½</media:category>
            <media:category label="Ð¿ÐµÑÐ¸ÑÐµÑÐ¸Ñ">Ð¿ÐµÑÐ¸ÑÐµÑÐ¸Ñ</media:category>
            <media:category label="ÑÐµÐ½ÑÐ¾ÑÐ½ÑÐ¹">ÑÐµÐ½ÑÐ¾ÑÐ½ÑÐ¹</media:category>
            <media:category label="CNewsTV">CNewsTV</media:category>
            <media:category label="high-tech">high-tech</media:category>
            <media:category label="hi-tech">hi-tech</media:category>
            <media:category label="technology">technology</media:category>
            <media:category label="Ð²ÑÑÐ¾ÐºÐ¸Ðµ">Ð²ÑÑÐ¾ÐºÐ¸Ðµ</media:category>
            <media:category label="ÐÐ¢">ÐÐ¢</media:category>
            <media:category label="Ð±Ð¸Ð·Ð½ÐµÑ">Ð±Ð¸Ð·Ð½ÐµÑ</media:category>
        </item>
    </channel>
</rss>"""

YOUTUBE_USER_FEED_XML = """\
<?xml version="1.0" ?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:gd="http://schemas.google.com/g/2005" xmlns:media="http://search.yahoo.com/mrss/" xmlns:openSearch="http://a9.com/-/spec/opensearchrss/1.0/" xmlns:yt="http://gdata.youtube.com/schemas/2007">
	<id>http://gdata.youtube.com/feeds/api/users/amaratestuser/uploads</id>
	<updated>2013-08-07T16:50:26.163Z</updated>
	<category scheme="http://schemas.google.com/g/2005#kind" term="http://gdata.youtube.com/schemas/2007#video"/>
	<title type="text">Uploads by amaratestuser</title>
	<logo>http://www.gstatic.com/youtube/img/logo.png</logo>
	<link href="https://gdata.youtube.com/feeds/api/users/amaratestuser" rel="related" type="application/atom+xml"/>
	<link href="https://www.youtube.com/channel/UCc8Gu4WfiMzsVgqYiHT0ubg/videos" rel="alternate" type="text/html"/>
	<link href="https://gdata.youtube.com/feeds/api/users/amaratestuser/uploads" rel="http://schemas.google.com/g/2005#feed" type="application/atom+xml"/>
	<link href="https://gdata.youtube.com/feeds/api/users/amaratestuser/uploads/batch" rel="http://schemas.google.com/g/2005#batch" type="application/atom+xml"/>
	<link href="https://gdata.youtube.com/feeds/api/users/amaratestuser/uploads?start-index=1&amp;max-results=25" rel="self" type="application/atom+xml"/>
	<author>
		<name>amaratestuser</name>
		<uri>https://gdata.youtube.com/feeds/api/users/amaratestuser</uri>
	</author>
	<generator uri="http://gdata.youtube.com" version="2.1">YouTube data API</generator>
	<openSearch:totalResults>3</openSearch:totalResults>
	<openSearch:startIndex>1</openSearch:startIndex>
	<openSearch:itemsPerPage>25</openSearch:itemsPerPage>
	<entry>
		<id>http://gdata.youtube.com/feeds/api/videos/1GAIwV7eRNQ</id>
		<published>2012-10-31T18:04:53.000Z</published>
		<updated>2012-10-31T18:06:13.000Z</updated>
		<category scheme="http://schemas.google.com/g/2005#kind" term="http://gdata.youtube.com/schemas/2007#video"/>
		<category label="People &amp; Blogs" scheme="http://gdata.youtube.com/schemas/2007/categories.cat" term="People"/>
		<title type="text">Amara Test Video 3</title>
		<content type="text"/>
		<link href="https://www.youtube.com/watch?v=1GAIwV7eRNQ&amp;feature=youtube_gdata" rel="alternate" type="text/html"/>
		<link href="https://gdata.youtube.com/feeds/api/videos/1GAIwV7eRNQ/responses" rel="http://gdata.youtube.com/schemas/2007#video.responses" type="application/atom+xml"/>
		<link href="https://gdata.youtube.com/feeds/api/videos/1GAIwV7eRNQ/related" rel="http://gdata.youtube.com/schemas/2007#video.related" type="application/atom+xml"/>
		<link href="https://m.youtube.com/details?v=1GAIwV7eRNQ" rel="http://gdata.youtube.com/schemas/2007#mobile" type="text/html"/>
		<link href="https://gdata.youtube.com/feeds/api/users/amaratestuser/uploads/1GAIwV7eRNQ" rel="self" type="application/atom+xml"/>
		<author>
			<name>amaratestuser</name>
			<uri>https://gdata.youtube.com/feeds/api/users/amaratestuser</uri>
		</author>
		<gd:comments>
			<gd:feedLink countHint="0" href="https://gdata.youtube.com/feeds/api/videos/1GAIwV7eRNQ/comments" rel="http://gdata.youtube.com/schemas/2007#comments"/>
		</gd:comments>
		<yt:hd/>
		<media:group>
			<media:category label="People &amp; Blogs" scheme="http://gdata.youtube.com/schemas/2007/categories.cat">People</media:category>
			<media:content duration="4" expression="full" isDefault="true" medium="video" type="application/x-shockwave-flash" url="https://www.youtube.com/v/1GAIwV7eRNQ?version=3&amp;f=user_uploads&amp;app=youtube_gdata" yt:format="5"/>
			<media:content duration="4" expression="full" medium="video" type="video/3gpp" url="rtsp://v8.cache3.c.youtube.com/CigLENy73wIaHwnURN5ewQhg1BMYDSANFEgGUgx1c2VyX3VwbG9hZHMM/0/0/0/video.3gp" yt:format="1"/>
			<media:content duration="4" expression="full" medium="video" type="video/3gpp" url="rtsp://v8.cache3.c.youtube.com/CigLENy73wIaHwnURN5ewQhg1BMYESARFEgGUgx1c2VyX3VwbG9hZHMM/0/0/0/video.3gp" yt:format="6"/>
			<media:description type="plain"/>
			<media:keywords/>
			<media:player url="https://www.youtube.com/watch?v=1GAIwV7eRNQ&amp;feature=youtube_gdata_player"/>
			<media:thumbnail height="360" time="00:00:02" url="https://i1.ytimg.com/vi/1GAIwV7eRNQ/0.jpg" width="480"/>
			<media:thumbnail height="90" time="00:00:01" url="https://i1.ytimg.com/vi/1GAIwV7eRNQ/1.jpg" width="120"/>
			<media:thumbnail height="90" time="00:00:02" url="https://i1.ytimg.com/vi/1GAIwV7eRNQ/2.jpg" width="120"/>
			<media:thumbnail height="90" time="00:00:03" url="https://i1.ytimg.com/vi/1GAIwV7eRNQ/3.jpg" width="120"/>
			<media:title type="plain">Amara Test Video 3</media:title>
			<yt:duration seconds="4"/>
		</media:group>
		<yt:statistics favoriteCount="0" viewCount="4"/>
	</entry>
	<entry>
		<id>http://gdata.youtube.com/feeds/api/videos/q26umaF242I</id>
		<published>2012-10-31T18:04:38.000Z</published>
		<updated>2012-10-31T18:04:38.000Z</updated>
		<category scheme="http://schemas.google.com/g/2005#kind" term="http://gdata.youtube.com/schemas/2007#video"/>
		<category label="People &amp; Blogs" scheme="http://gdata.youtube.com/schemas/2007/categories.cat" term="People"/>
		<title type="text">Amara Test Video 2</title>
		<content type="text"/>
		<link href="https://www.youtube.com/watch?v=q26umaF242I&amp;feature=youtube_gdata" rel="alternate" type="text/html"/>
		<link href="https://gdata.youtube.com/feeds/api/videos/q26umaF242I/responses" rel="http://gdata.youtube.com/schemas/2007#video.responses" type="application/atom+xml"/>
		<link href="https://gdata.youtube.com/feeds/api/videos/q26umaF242I/related" rel="http://gdata.youtube.com/schemas/2007#video.related" type="application/atom+xml"/>
		<link href="https://m.youtube.com/details?v=q26umaF242I" rel="http://gdata.youtube.com/schemas/2007#mobile" type="text/html"/>
		<link href="https://gdata.youtube.com/feeds/api/users/amaratestuser/uploads/q26umaF242I" rel="self" type="application/atom+xml"/>
		<author>
			<name>amaratestuser</name>
			<uri>https://gdata.youtube.com/feeds/api/users/amaratestuser</uri>
		</author>
		<gd:comments>
			<gd:feedLink countHint="0" href="https://gdata.youtube.com/feeds/api/videos/q26umaF242I/comments" rel="http://gdata.youtube.com/schemas/2007#comments"/>
		</gd:comments>
		<yt:hd/>
		<media:group>
			<media:category label="People &amp; Blogs" scheme="http://gdata.youtube.com/schemas/2007/categories.cat">People</media:category>
			<media:content duration="4" expression="full" isDefault="true" medium="video" type="application/x-shockwave-flash" url="https://www.youtube.com/v/q26umaF242I?version=3&amp;f=user_uploads&amp;app=youtube_gdata" yt:format="5"/>
			<media:content duration="4" expression="full" medium="video" type="video/3gpp" url="rtsp://v4.cache1.c.youtube.com/CigLENy73wIaHwli43ahma5uqxMYDSANFEgGUgx1c2VyX3VwbG9hZHMM/0/0/0/video.3gp" yt:format="1"/>
			<media:content duration="4" expression="full" medium="video" type="video/3gpp" url="rtsp://v4.cache1.c.youtube.com/CigLENy73wIaHwli43ahma5uqxMYESARFEgGUgx1c2VyX3VwbG9hZHMM/0/0/0/video.3gp" yt:format="6"/>
			<media:description type="plain"/>
			<media:keywords/>
			<media:player url="https://www.youtube.com/watch?v=q26umaF242I&amp;feature=youtube_gdata_player"/>
			<media:thumbnail height="360" time="00:00:02" url="https://i1.ytimg.com/vi/q26umaF242I/0.jpg" width="480"/>
			<media:thumbnail height="90" time="00:00:01" url="https://i1.ytimg.com/vi/q26umaF242I/1.jpg" width="120"/>
			<media:thumbnail height="90" time="00:00:02" url="https://i1.ytimg.com/vi/q26umaF242I/2.jpg" width="120"/>
			<media:thumbnail height="90" time="00:00:03" url="https://i1.ytimg.com/vi/q26umaF242I/3.jpg" width="120"/>
			<media:title type="plain">Amara Test Video 2</media:title>
			<yt:duration seconds="4"/>
		</media:group>
	</entry>
	<entry>
		<id>http://gdata.youtube.com/feeds/api/videos/cvAZQZa9iWM</id>
		<published>2012-10-31T17:58:13.000Z</published>
		<updated>2012-10-31T17:58:13.000Z</updated>
		<category scheme="http://schemas.google.com/g/2005#kind" term="http://gdata.youtube.com/schemas/2007#video"/>
		<category label="People &amp; Blogs" scheme="http://gdata.youtube.com/schemas/2007/categories.cat" term="People"/>
		<title type="text">Αmara Test Video 1</title>
		<content type="text"/>
		<link href="https://www.youtube.com/watch?v=cvAZQZa9iWM&amp;feature=youtube_gdata" rel="alternate" type="text/html"/>
		<link href="https://gdata.youtube.com/feeds/api/videos/cvAZQZa9iWM/responses" rel="http://gdata.youtube.com/schemas/2007#video.responses" type="application/atom+xml"/>
		<link href="https://gdata.youtube.com/feeds/api/videos/cvAZQZa9iWM/related" rel="http://gdata.youtube.com/schemas/2007#video.related" type="application/atom+xml"/>
		<link href="https://m.youtube.com/details?v=cvAZQZa9iWM" rel="http://gdata.youtube.com/schemas/2007#mobile" type="text/html"/>
		<link href="https://gdata.youtube.com/feeds/api/users/amaratestuser/uploads/cvAZQZa9iWM" rel="self" type="application/atom+xml"/>
		<author>
			<name>amaratestuser</name>
			<uri>https://gdata.youtube.com/feeds/api/users/amaratestuser</uri>
		</author>
		<gd:comments>
			<gd:feedLink countHint="0" href="https://gdata.youtube.com/feeds/api/videos/cvAZQZa9iWM/comments" rel="http://gdata.youtube.com/schemas/2007#comments"/>
		</gd:comments>
		<yt:hd/>
		<media:group>
			<media:category label="People &amp; Blogs" scheme="http://gdata.youtube.com/schemas/2007/categories.cat">People</media:category>
			<media:content duration="4" expression="full" isDefault="true" medium="video" type="application/x-shockwave-flash" url="https://www.youtube.com/v/cvAZQZa9iWM?version=3&amp;f=user_uploads&amp;app=youtube_gdata" yt:format="5"/>
			<media:content duration="4" expression="full" medium="video" type="video/3gpp" url="rtsp://v6.cache7.c.youtube.com/CigLENy73wIaHwljib2WQRnwchMYDSANFEgGUgx1c2VyX3VwbG9hZHMM/0/0/0/video.3gp" yt:format="1"/>
			<media:content duration="4" expression="full" medium="video" type="video/3gpp" url="rtsp://v6.cache7.c.youtube.com/CigLENy73wIaHwljib2WQRnwchMYESARFEgGUgx1c2VyX3VwbG9hZHMM/0/0/0/video.3gp" yt:format="6"/>
			<media:description type="plain"/>
			<media:keywords/>
			<media:player url="https://www.youtube.com/watch?v=cvAZQZa9iWM&amp;feature=youtube_gdata_player"/>
			<media:thumbnail height="360" time="00:00:02" url="https://i1.ytimg.com/vi/cvAZQZa9iWM/0.jpg" width="480"/>
			<media:thumbnail height="90" time="00:00:01" url="https://i1.ytimg.com/vi/cvAZQZa9iWM/1.jpg" width="120"/>
			<media:thumbnail height="90" time="00:00:02" url="https://i1.ytimg.com/vi/cvAZQZa9iWM/2.jpg" width="120"/>
			<media:thumbnail height="90" time="00:00:03" url="https://i1.ytimg.com/vi/cvAZQZa9iWM/3.jpg" width="120"/>
			<media:title type="plain">Αmara Test Video 1</media:title>
			<yt:duration seconds="4"/>
		</media:group>
		<yt:statistics favoriteCount="0" viewCount="4"/>
	</entry>
</feed>"""

VIMEO_FEED_XML = """\
<?xml version="1.0" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:media="http://search.yahoo.com/mrss/">
	<channel>
		<title>Vimeo / Blake Whitman's videos</title>
		<link>http://vimeo.com/blakewhitman/videos</link>
		<description>Videos uploaded by Blake Whitman on Vimeo.</description>
		<pubDate>Wed, 07 Aug 2013 10:02:39 -0400</pubDate>
		<generator>Vimeo</generator>
		<atom:link href="http://vimeo.com/blakewhitman/videos/rss" rel="self"/>
		<atom:link href="http://vimeo.superfeedr.com" rel="hub"/>
		<image>
			<url>http://b.vimeocdn.com/ps/470/470474_100.jpg</url>
			<title>Vimeo / Blake Whitman's videos</title>
			<link>http://vimeo.com/blakewhitman/videos</link>
		</image>
		<item>
			<title>Colorado mountain hail</title>
			<pubDate>Sat, 03 Aug 2013 14:51:40 -0400</pubDate>
			<link>http://vimeo.com/71645256</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/71645256&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/445/268/445268476_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt; &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt; &lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2013-08-03:clip71645256</guid>
			<enclosure length="1482783" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=71645256"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=71645256"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/445/268/445268476_200.jpg" width="200"/>
				<media:title>Colorado mountain hail</media:title>
			</media:content>
		</item>
		<item>
			<title>Rental car music magic</title>
			<pubDate>Fri, 26 Jul 2013 15:18:34 -0400</pubDate>
			<link>http://vimeo.com/71118404</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/71118404&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/444/586/444586958_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;rental car jams.&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt; &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt; &lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2013-07-26:clip71118404</guid>
			<enclosure length="1493369" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=71118404"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=71118404"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/444/586/444586958_200.jpg" width="200"/>
				<media:title>Rental car music magic</media:title>
			</media:content>
		</item>
		<item>
			<title>Vernal Falls</title>
			<pubDate>Fri, 26 Jul 2013 12:16:45 -0400</pubDate>
			<link>http://vimeo.com/71105844</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/71105844&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/444/569/444569916_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;Yosemite&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt; &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:yosemite&quot;&gt;yosemite&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:hiking&quot;&gt;hiking&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:fun&quot;&gt;fun&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:placeofwonder&quot;&gt;placeofwonder&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2013-07-26:clip71105844</guid>
			<enclosure length="1538621" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=71105844"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=71105844"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/444/569/444569916_200.jpg" width="200"/>
				<media:title>Vernal Falls</media:title>
			</media:content>
		</item>
		<item>
			<title>I'm watching you, Emily</title>
			<pubDate>Tue, 14 May 2013 17:56:35 -0400</pubDate>
			<link>http://vimeo.com/66196239</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/66196239&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/437/582/437582686_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;Gotcha!&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/meisemily&quot;&gt;Emily Getman&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:I%26%23039%3Bm+watching+you&quot;&gt;I'm watching you&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:you+are+being+watched&quot;&gt;you are being watched&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:winning&quot;&gt;winning&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2013-05-14:clip66196239</guid>
			<enclosure length="11605853" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=66196239"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=66196239"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/437/582/437582686_200.jpg" width="200"/>
				<media:title>I'm watching you, Emily</media:title>
			</media:content>
		</item>
		<item>
			<title>I'm watching you, Zach</title>
			<pubDate>Tue, 16 Apr 2013 10:56:09 -0400</pubDate>
			<link>http://vimeo.com/64153154</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/64153154&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/434/687/434687142_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;Yep&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/zachtothefuture&quot;&gt;Zach Goodman&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt; &lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2013-04-16:clip64153154</guid>
			<enclosure length="14553146" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=64153154"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=64153154"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/434/687/434687142_200.jpg" width="200"/>
				<media:title>I'm watching you, Zach</media:title>
			</media:content>
		</item>
		<item>
			<title>Muscle Music: what? Vimeo Sausages.</title>
			<pubDate>Wed, 29 Aug 2012 17:28:15 -0400</pubDate>
			<link>http://vimeo.com/48480754</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/48480754&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/334/540/334540377_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt; &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice&quot;&gt;Old Spice&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+deodorant&quot;&gt;Old Spice deodorant&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+music&quot;&gt;Old Spice music&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Muscle+Music&quot;&gt;Muscle Music&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Terry+Crews&quot;&gt;Terry Crews&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:New+Old+Spice&quot;&gt;New Old Spice&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+cool&quot;&gt;Old Spice cool&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Terry+Crews+video&quot;&gt;Terry Crews video&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Funny+video&quot;&gt;Funny video&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+guy&quot;&gt;Old Spice guy&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Funny+ab+video&quot;&gt;Funny ab video&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Terry+Crews+muscles&quot;&gt;Terry Crews muscles&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+commercial&quot;&gt;Old Spice commercial&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Terry+Crews+ad&quot;&gt;Terry Crews ad&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+muscle&quot;&gt;Old Spice muscle&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+ad&quot;&gt;Old Spice ad&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+Danger+Zone&quot;&gt;Old Spice Danger Zone&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:Music+game&quot;&gt;Music game&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2012-08-29:clip48480754</guid>
			<enclosure length="1398087" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=48480754"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=48480754"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/334/540/334540377_200.jpg" width="200"/>
				<media:title>Muscle Music: what? Vimeo Sausages.</media:title>
			</media:content>
		</item>
		<item>
			<title>Muscle Music: a jingle</title>
			<pubDate>Tue, 28 Aug 2012 13:06:25 -0400</pubDate>
			<link>http://vimeo.com/48382614</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/48382614&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/334/263/334263669_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt; &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice&quot;&gt;Old Spice&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+deodorant&quot;&gt;Old Spice deodorant&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+music&quot;&gt;Old Spice music&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Muscle+Music&quot;&gt;Muscle Music&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Terry+Crews&quot;&gt;Terry Crews&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:New+Old+Spice&quot;&gt;New Old Spice&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+cool&quot;&gt;Old Spice cool&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Terry+Crews+video&quot;&gt;Terry Crews video&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Funny+video&quot;&gt;Funny video&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+guy&quot;&gt;Old Spice guy&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Funny+ab+video&quot;&gt;Funny ab video&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Terry+Crews+muscles&quot;&gt;Terry Crews muscles&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+commercial&quot;&gt;Old Spice commercial&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Terry+Crews+ad&quot;&gt;Terry Crews ad&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+muscle&quot;&gt;Old Spice muscle&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+ad&quot;&gt;Old Spice ad&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Old+Spice+Danger+Zone&quot;&gt;Old Spice Danger Zone&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:Music+game&quot;&gt;Music game&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2012-08-28:clip48382614</guid>
			<enclosure length="4218572" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=48382614"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=48382614"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/334/263/334263669_200.jpg" width="200"/>
				<media:title>Muscle Music: a jingle</media:title>
			</media:content>
		</item>
		<item>
			<title>subway time</title>
			<pubDate>Sat, 04 Aug 2012 00:48:29 -0400</pubDate>
			<link>http://vimeo.com/46918437</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/46918437&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/326/845/326845864_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;sometimes this happens.&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt; &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt; &lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2012-08-04:clip46918437</guid>
			<enclosure length="4983797" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=46918437"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=46918437"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/326/845/326845864_200.jpg" width="200"/>
				<media:title>subway time</media:title>
			</media:content>
		</item>
		<item>
			<title>The Colosseum</title>
			<pubDate>Thu, 16 Feb 2012 19:48:02 -0500</pubDate>
			<link>http://vimeo.com/36938127</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/36938127&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/253/537/253537278_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;4500 ft vertical climb – then one of the longest backcountry runs of my life.&lt;/p&gt; &lt;p&gt;Vaux Glacier//Sir Donald Range//Roger's Pass//British Columbia&lt;/p&gt; &lt;p&gt;Filmed by Patrick Gault&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt; &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:British+Columbia&quot;&gt;British Columbia&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Rogers+Pass&quot;&gt;Rogers Pass&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:skiing&quot;&gt;skiing&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:backcountry&quot;&gt;backcountry&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:snow&quot;&gt;snow&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:so+sick&quot;&gt;so sick&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2012-02-16:clip36938127</guid>
			<enclosure length="7666575" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=36938127"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=36938127"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/253/537/253537278_200.jpg" width="200"/>
				<media:title>The Colosseum</media:title>
			</media:content>
		</item>
		<item>
			<title>renovation</title>
			<pubDate>Tue, 27 Dec 2011 17:45:09 -0500</pubDate>
			<link>http://vimeo.com/34268996</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/34268996&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/233/232/233232905_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;A couple friends and I renovated my kitchen up in Maine. It took a week, many cases of Coors Light, and patience. But it was worth it!&lt;/p&gt; &lt;p&gt;September 2011.&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt; &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:maine&quot;&gt;maine&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:north+haven&quot;&gt;north haven&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:beer&quot;&gt;beer&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:renovation&quot;&gt;renovation&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:kitchen&quot;&gt;kitchen&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-12-27:clip34268996</guid>
			<enclosure length="31991175" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=34268996"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=34268996"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/233/232/233232905_200.jpg" width="200"/>
				<media:title>renovation</media:title>
			</media:content>
		</item>
		<item>
			<title>a hint</title>
			<pubDate>Thu, 22 Dec 2011 23:58:11 -0500</pubDate>
			<link>http://vimeo.com/34113771</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/34113771&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/232/075/232075557_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;of something to come&lt;/p&gt; &lt;p&gt;a 5X5&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/damianwashington&quot;&gt;Damian Washington&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/mssngpeces&quot;&gt;m ss ng p eces&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:5x5&quot;&gt;5x5&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:hint&quot;&gt;hint&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:preview&quot;&gt;preview&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:something+big+is+coming&quot;&gt;something big is coming&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-12-22:clip34113771</guid>
			<enclosure length="2776501" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=34113771"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=34113771"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/232/075/232075557_200.jpg" width="200"/>
				<media:title>a hint</media:title>
			</media:content>
		</item>
		<item>
			<title>gentleman's squash</title>
			<pubDate>Wed, 14 Dec 2011 10:14:16 -0500</pubDate>
			<link>http://vimeo.com/33664145</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/33664145&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/228/654/228654500_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/ryanbrown&quot;&gt;ryan brown&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt; &lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-12-14:clip33664145</guid>
			<enclosure length="6522571" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=33664145"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=33664145"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/228/654/228654500_200.jpg" width="200"/>
				<media:title>gentleman's squash</media:title>
			</media:content>
		</item>
		<item>
			<title>11\\11\\11</title>
			<pubDate>Sat, 12 Nov 2011 12:42:51 -0500</pubDate>
			<link>http://vimeo.com/32007180</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/32007180&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/216/196/216196208_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;For the One Day on Earth global film project. Onedayonearth.org&lt;/p&gt; &lt;p&gt;Jefferson stop on the L. Brooklyn, New York. November 11, 2011&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt; &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:one+day+on+earth&quot;&gt;one day on earth&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Brooklyn&quot;&gt;Brooklyn&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:subway&quot;&gt;subway&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-11-12:clip32007180</guid>
			<enclosure length="8335339" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=32007180"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=32007180"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/216/196/216196208_200.jpg" width="200"/>
				<media:title>11\\11\\11</media:title>
			</media:content>
		</item>
		<item>
			<title>Ichke Jergez</title>
			<pubDate>Tue, 08 Nov 2011 22:43:17 -0500</pubDate>
			<link>http://vimeo.com/31827647</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/31827647&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/214/847/214847591_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;Kyrgyzstan, November 2010&lt;/p&gt; &lt;p&gt;&lt;a href=&quot;http://fortytribesbackcountry.com&quot; target=&quot;_blank&quot; rel=&quot;nofollow&quot;&gt;fortytribesbackcountry.com&lt;/a&gt;&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/squeakofapika&quot;&gt;ryan&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:kyrgystan&quot;&gt;kyrgystan&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:40+tribes+backcountry&quot;&gt;40 tribes backcountry&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:skiing&quot;&gt;skiing&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:backcountry&quot;&gt;backcountry&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-11-08:clip31827647</guid>
			<enclosure length="6379219" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=31827647"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=31827647"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/214/847/214847591_200.jpg" width="200"/>
				<media:title>Ichke Jergez</media:title>
			</media:content>
		</item>
		<item>
			<title>Mobius :: Behind The Scenes</title>
			<pubDate>Wed, 02 Nov 2011 23:56:37 -0400</pubDate>
			<link>http://vimeo.com/31526888</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/31526888&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/212/874/212874375_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;A Vimeo Exclusive!&lt;/p&gt; &lt;p&gt;Vincent Laforet invited Vimeo out to film the behind the scenes of his new short film, Mobius, filmed with the all-new Canon EOS C300 camera. &lt;/p&gt; &lt;p&gt;Mobius, full film - &lt;a href=&quot;http://vimeo.com/31525127&quot;&gt;vimeo.com/31525127&lt;/a&gt;&lt;/p&gt; &lt;p&gt;Read more about the new Canon EOS C300 here - &lt;a href=&quot;http://bit.ly/u0m8gz&quot; target=&quot;_blank&quot; rel=&quot;nofollow&quot;&gt;bit.ly/u0m8gz&lt;/a&gt;&lt;/p&gt; &lt;p&gt;Music: &quot;Smash &amp; Grab&quot; by mGee &lt;a href=&quot;http://mgee.blocsonic.com&quot; target=&quot;_blank&quot; rel=&quot;nofollow&quot;&gt;mgee.blocsonic.com&lt;/a&gt;&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/sammorrill&quot;&gt;Sam Morrill&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/laforet&quot;&gt;Vincent Laforet&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:mobius&quot;&gt;mobius&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:behind+the+scenes&quot;&gt;behind the scenes&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:vincent+laforet&quot;&gt;vincent laforet&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:blake+whitman&quot;&gt;blake whitman&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:vimeo+films&quot;&gt;vimeo films&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:desert&quot;&gt;desert&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-11-02:clip31526888</guid>
			<enclosure length="30614743" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=31526888"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=31526888"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/212/874/212874375_200.jpg" width="200"/>
				<media:title>Mobius :: Behind The Scenes</media:title>
			</media:content>
		</item>
		<item>
			<title>FAST</title>
			<pubDate>Tue, 27 Sep 2011 09:17:14 -0400</pubDate>
			<link>http://vimeo.com/29663711</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/29663711&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/198/828/198828615_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;driving down dirt road toward soggy lake, california. fast.&lt;/p&gt; &lt;p&gt;filmed on HD GoPro edited using FCP7 and Magic Bullet Looks&lt;/p&gt; &lt;p&gt;music found and purchased in Vimeo's new Music Store!&lt;br&gt; &lt;a href=&quot;http://vimeo.com/musicstore/track/110194&quot;&gt;vimeo.com/musicstore/track/110194&lt;/a&gt;&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt; &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:desert&quot;&gt;desert&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:gopro&quot;&gt;gopro&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:drive&quot;&gt;drive&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:driving&quot;&gt;driving&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:fast&quot;&gt;fast&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:soggy+lake&quot;&gt;soggy lake&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:this+was+fun&quot;&gt;this was fun&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-09-27:clip29663711</guid>
			<enclosure length="15914596" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=29663711"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=29663711"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/198/828/198828615_200.jpg" width="200"/>
				<media:title>FAST</media:title>
			</media:content>
		</item>
		<item>
			<title>ISTANBUL//10</title>
			<pubDate>Thu, 22 Sep 2011 00:11:20 -0400</pubDate>
			<link>http://vimeo.com/29411757</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/29411757&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/197/045/197045121_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;November, 2010.&lt;/p&gt; &lt;p&gt;Edited in the order it was shot, using only natural sounds.&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/user254152&quot;&gt;bgault&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:Istanbul&quot;&gt;Istanbul&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Turkey&quot;&gt;Turkey&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Travel&quot;&gt;Travel&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:Fun&quot;&gt;Fun&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-09-22:clip29411757</guid>
			<enclosure length="44161669" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=29411757"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=29411757"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/197/045/197045121_200.jpg" width="200"/>
				<media:title>ISTANBUL//10</media:title>
			</media:content>
		</item>
		<item>
			<title>walking off rocks</title>
			<pubDate>Tue, 05 Jul 2011 00:39:07 -0400</pubDate>
			<link>http://vimeo.com/25995047</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/25995047&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/171/487/171487405_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;Music // Yasmin by Trigg - &lt;a href=&quot;http://freemusicarchive.org/music/Trigg/&quot; target=&quot;_blank&quot; rel=&quot;nofollow&quot;&gt;freemusicarchive.org/music/Trigg/&lt;/a&gt; shared under (CC BY-NC-SA 3.0)&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/andreaallen&quot;&gt;Andrea Allen&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/katieallen&quot;&gt;Katie Allen&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/user203842&quot;&gt;Uncle Nutsy&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:maine&quot;&gt;maine&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:north+haven&quot;&gt;north haven&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:jumping&quot;&gt;jumping&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:ocean&quot;&gt;ocean&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:swimming&quot;&gt;swimming&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:weird&quot;&gt;weird&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:everything+is+normal+here+too&quot;&gt;everything is normal here too&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-07-05:clip25995047</guid>
			<enclosure length="33460878" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=25995047"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=25995047"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/171/487/171487405_200.jpg" width="200"/>
				<media:title>walking off rocks</media:title>
			</media:content>
		</item>
		<item>
			<title>Everything is Normal</title>
			<pubDate>Mon, 04 Jul 2011 14:33:18 -0400</pubDate>
			<link>http://vimeo.com/25977725</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/25977725&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/171/357/171357605_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/sniebauer&quot;&gt;Stephen Niebauer&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/derekbeck&quot;&gt;Derek Beck&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/andreaallen&quot;&gt;Andrea Allen&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/bretheiman&quot;&gt;Bret Heiman&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/iandurkin&quot;&gt;Ian Durkin&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/billbergen&quot;&gt;Bill Bergen&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/sammorrill&quot;&gt;Sam Morrill&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/danielhayek&quot;&gt;Daniel Hayek&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/katiearmstrong&quot;&gt;Katie Armstrong&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/jimi&quot;&gt;Jimmy Heffernan&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/katieallen&quot;&gt;Katie Allen&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:maine&quot;&gt;maine&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:north+haven&quot;&gt;north haven&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:everything+is+normal&quot;&gt;everything is normal&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:really&quot;&gt;really&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:it%26%23039%3Bs+normal&quot;&gt;it's normal&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-07-04:clip25977725</guid>
			<enclosure length="15106012" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=25977725"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=25977725"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/171/357/171357605_200.jpg" width="200"/>
				<media:title>Everything is Normal</media:title>
			</media:content>
		</item>
		<item>
			<title>Buenos</title>
			<pubDate>Sun, 26 Jun 2011 14:56:30 -0400</pubDate>
			<link>http://vimeo.com/25630889</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/25630889&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/168/868/168868100_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;Buenos Aires. a 5x5.&lt;/p&gt; &lt;p&gt;Some moments from our trip to BA. We're having an incredible time down here. Larger edit to come soon.&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/sammorrill&quot;&gt;Sam Morrill&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/donrudi&quot;&gt;Rudi Borrmann&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/conzpreti&quot;&gt;Connie Preti&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/unblogged&quot;&gt;Pablo M Sanchez&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/user7297626&quot;&gt;Mauro Montauti&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:5x5&quot;&gt;5x5&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:5+vignettes&quot;&gt;5 vignettes&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:buenos+aires&quot;&gt;buenos aires&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:argentina&quot;&gt;argentina&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:this+place+is+sweet%21&quot;&gt;this place is sweet!&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-06-26:clip25630889</guid>
			<enclosure length="2693253" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=25630889"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=25630889"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/168/868/168868100_200.jpg" width="200"/>
				<media:title>Buenos</media:title>
			</media:content>
		</item>
		<item>
			<title>sam</title>
			<pubDate>Sat, 25 Jun 2011 10:42:05 -0400</pubDate>
			<link>http://vimeo.com/25593783</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/25593783&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/168/615/168615093_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;approx 4:23 am&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt; &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt; &lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-06-25:clip25593783</guid>
			<enclosure length="3250412" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=25593783"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=25593783"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/168/615/168615093_200.jpg" width="200"/>
				<media:title>sam</media:title>
			</media:content>
		</item>
		<item>
			<title>torrential</title>
			<pubDate>Mon, 20 Jun 2011 15:11:56 -0400</pubDate>
			<link>http://vimeo.com/25366242</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/25366242&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/166/942/166942484_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;one minute of a freak storm in the lobby of IAC&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt; &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:rain&quot;&gt;rain&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:storm&quot;&gt;storm&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:1+minute&quot;&gt;1 minute&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:nyc&quot;&gt;nyc&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:new+york&quot;&gt;new york&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:iac&quot;&gt;iac&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:street&quot;&gt;street&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-06-20:clip25366242</guid>
			<enclosure length="6546277" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=25366242"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=25366242"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/166/942/166942484_200.jpg" width="200"/>
				<media:title>torrential</media:title>
			</media:content>
		</item>
		<item>
			<title>far from now</title>
			<pubDate>Sun, 12 Jun 2011 23:43:33 -0400</pubDate>
			<link>http://vimeo.com/25013553</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/25013553&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/164/407/164407538_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;Short film commissioned by the OFFF Festival 2011 in Barcelona. &lt;/p&gt; &lt;p&gt;The theme of this year's festival was &quot;Year Zero&quot;, sort of a re-imagining or a new beginning for everything. I was honored to speak there with a host of other amazing artists, filmmakers, agencies, designers etc. Really fantastic event.&lt;/p&gt; &lt;p&gt;music: burning glow by WYPER - &lt;a href=&quot;http://soundcloud.com/wyper54/burning-glow&quot; target=&quot;_blank&quot; rel=&quot;nofollow&quot;&gt;soundcloud.com/wyper54/burning-glow&lt;/a&gt;&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/julia&quot;&gt;Julia Quinn&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:Short+film&quot;&gt;Short film&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:OFFF&quot;&gt;OFFF&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:OFFF+Festival&quot;&gt;OFFF Festival&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Coney+Island&quot;&gt;Coney Island&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:5D&quot;&gt;5D&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:Canon&quot;&gt;Canon&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:year+zero&quot;&gt;year zero&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-06-12:clip25013553</guid>
			<enclosure length="23525790" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=25013553"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=25013553"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/164/407/164407538_200.jpg" width="200"/>
				<media:title>far from now</media:title>
			</media:content>
		</item>
		<item>
			<title>chores</title>
			<pubDate>Mon, 16 May 2011 08:27:04 -0400</pubDate>
			<link>http://vimeo.com/23795058</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/23795058&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/155/287/155287151_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;5:15 am. big picture farm. townshend, vermont.&lt;/p&gt; &lt;p&gt;my friend louisa does her morning milking and feeding chores with her lovely goats and kids.&lt;/p&gt; &lt;p&gt;&lt;a href=&quot;http://www.bigpicturefarm.com&quot; target=&quot;_blank&quot; rel=&quot;nofollow&quot;&gt;bigpicturefarm.com&lt;/a&gt;&lt;/p&gt; &lt;p&gt;you can subscribe to their daily farm videos here - &lt;a href=&quot;http://vimeo.com/channels/goats&quot;&gt;vimeo.com/channels/goats&lt;/a&gt;&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/louisaconrad&quot;&gt;louisa conrad&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:vermont&quot;&gt;vermont&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:farm&quot;&gt;farm&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:milking&quot;&gt;milking&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:big+picture+farm&quot;&gt;big picture farm&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-05-16:clip23795058</guid>
			<enclosure length="35691787" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=23795058"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=23795058"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/155/287/155287151_200.jpg" width="200"/>
				<media:title>chores</media:title>
			</media:content>
		</item>
		<item>
			<title>Louisa</title>
			<pubDate>Sat, 14 May 2011 21:11:31 -0400</pubDate>
			<link>http://vimeo.com/23740477</link>
			<dc:creator>Blake Whitman</dc:creator>
			<description>&lt;p&gt;&lt;a href=&quot;http://vimeo.com/23740477&quot;&gt;&lt;img src=&quot;http://b.vimeocdn.com/ts/154/892/154892572_200.jpg&quot; alt=&quot;&quot; /&gt;&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;p class=&quot;first&quot;&gt;my friend Louisa and her husband Luke work on a farm. These are their goats. This is what Louisa does. Everyday. Twice.&lt;/p&gt; &lt;p&gt;milking: &lt;a href=&quot;http://vimeo.com/23795058&quot;&gt;vimeo.com/23795058&lt;/a&gt;&lt;/p&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Cast:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/blakewhitman&quot;&gt;Blake Whitman&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/louisaconrad&quot;&gt;louisa conrad&lt;/a&gt;&lt;/p&gt;&lt;p&gt;&lt;strong&gt;Tags:&lt;/strong&gt;  &lt;a href=&quot;http://vimeo.com/tag:goats&quot;&gt;goats&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:farm&quot;&gt;farm&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:farming&quot;&gt;farming&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:vermont&quot;&gt;vermont&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:fun&quot;&gt;fun&lt;/a&gt;,  &lt;a href=&quot;http://vimeo.com/tag:not+fun&quot;&gt;not fun&lt;/a&gt;  and &lt;a href=&quot;http://vimeo.com/tag:kinda+want+to+do+this&quot;&gt;kinda want to do this&lt;/a&gt;&lt;/p&gt;</description>
			<guid isPermaLink="false">tag:vimeo,2011-05-14:clip23740477</guid>
			<enclosure length="13329903" type="application/x-shockwave-flash" url="http://vimeo.com/moogaloop.swf?clip_id=23740477"/>
			<media:content>
				<media:player url="http://vimeo.com/moogaloop.swf?clip_id=23740477"/>
				<media:credit role="author" scheme="http://vimeo.com/blakewhitman"/>
				<media:thumbnail height="150" url="http://b.vimeocdn.com/ts/154/892/154892572_200.jpg" width="200"/>
				<media:title>Louisa</media:title>
			</media:content>
		</item>
	</channel>
</rss>"""
