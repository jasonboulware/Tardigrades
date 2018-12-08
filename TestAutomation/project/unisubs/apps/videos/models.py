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

from collections import defaultdict
from datetime import datetime, date, timedelta
import hashlib
import logging
import json
import string
import random
import time
import re
import urlparse

from django.utils.safestring import mark_safe
from django.core.cache import cache
from django.dispatch import receiver
from django.db import connection, models, IntegrityError
from django.db.models.signals import post_save, pre_delete
from django.db import transaction
from django.db.models import Q, query
from django.db import IntegrityError
from django.utils.dateformat import format as date_format
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.forms.forms import NON_FIELD_ERRORS

from auth.models import CustomUser as User, Awards
from caching import ModelCacheManager
from externalsites import google
from videos import behaviors
from videos import metadata
from videos import signals
from videos.types import (video_type_registrar, video_type_choices,
                          VideoTypeError, YoutubeVideoType, VimeoVideoType)
from videos.feed_parser import VideoImporter
from comments.models import Comment
from widget import video_cache
from utils import codes
from utils import dates
from utils import translation
from utils.amazon import S3EnabledImageField
from utils.panslugify import pan_slugify
from utils.searching import get_terms
from utils.subtitles import create_new_subtitles, dfxp_merge
from utils.text import fmt
from utils.url_escape import url_escape
from teams.moderation_const import MODERATION_STATUSES, UNMODERATED

logger = logging.getLogger("videos-models")

URL_MAX_LENGTH = 2048

NO_SUBTITLES, SUBTITLES_FINISHED = range(2)
VIDEO_TYPE_HTML5 = 'H'
VIDEO_TYPE_YOUTUBE = 'Y'
VIDEO_TYPE_BLIPTV = 'B'
VIDEO_TYPE_GOOGLE = 'G'
VIDEO_TYPE_FORA = 'F'
VIDEO_TYPE_VIMEO = 'V'
VIDEO_TYPE_WISTIA = 'W'
VIDEO_TYPE_DAILYMOTION = 'D'
VIDEO_TYPE_FLV = 'L'
VIDEO_TYPE_BRIGHTCOVE = 'C'
VIDEO_TYPE_MP3 = 'M'
VIDEO_TYPE_KALTURA = 'K'
VIDEO_META_CHOICES = (
    (1, 'Author',),
    (2, 'Creation Date',),
)
VIDEO_META_TYPE_NAMES = {}
VIDEO_META_TYPE_VARS = {}
VIDEO_META_TYPE_IDS = {}

MAX_VIDEO_SEARCH_TERMS = 10

MAX_SEACH_TEXT_LENGTH = 10 * 1000 * 1000

def url_hash(url):
    return hashlib.md5(url.encode("utf-8")).hexdigest()

def update_metadata_choices():
    """Refresh the VIDEO_META_TYPE_* set of constants.

    When VIDEO_META_CHOICES is updated through VideoMetadata.add_metadata_type()
    the set of extra lookup variables needs to be updated as well.  This
    function does that.

    You should never need to call this directly --
    VideoMetadata.add_metadata_type() will take care of it.

    """
    global VIDEO_META_TYPE_NAMES, VIDEO_META_TYPE_VARS , VIDEO_META_TYPE_IDS
    VIDEO_META_TYPE_NAMES = dict(VIDEO_META_CHOICES)
    VIDEO_META_TYPE_VARS = dict((k, name.lower().replace(' ', '_'))
                                for k, name in VIDEO_META_CHOICES)
    VIDEO_META_TYPE_IDS = dict([choice[::-1] for choice in VIDEO_META_CHOICES])
update_metadata_choices()

ALL_LANGUAGES = [(val, _(name))for val, name in settings.ALL_LANGUAGES]
VALID_LANGUAGE_CODES = [unicode(x[0]) for x in ALL_LANGUAGES]

def make_title_from_url(url):
    url = url.strip('/')
    if url.startswith('http://'):
        url = url[7:]

    parts = url.split('/')
    if len(parts) > 1:
        return '%s/.../%s' % (parts[0], parts[-1])
    else:
        return url

class AlreadyEditingException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __unicode__(self):
        return self.msg


# Video

class VideoQuerySet(query.QuerySet):
    def select_has_public_version(self):
        """Add a subquery to check if there is a public version for this video

        This will speed up the has_public_version() method.
        """
        sql = """\
EXISTS(
    SELECT * FROM subtitles_subtitleversion sv
    WHERE sv.video_id = videos_video.id
        AND (sv.visibility_override='public'
            OR (sv.visibility_override = '' AND sv.visibility='public')))"""

        return self.extra({ '_has_public_version': sql })

    def featured(self):
        return self.filter(featured__isnull=False).order_by('-featured')

    def latest(self):
        return self.public().order_by('-id')

    def public(self):
        return self.filter(is_public=True)

    def search(self, query):
        # If only one query term, search normally,
        # otherwise only use terms with 3 or more chars.
        # Terms with less chars are not indexed, so they will never match anything.
        terms = get_terms(query)
        if len(terms) == 1 and len(terms[0]) > 2:
            return self.filter(search_text__search=terms[0])
        else:
            terms = [t for t in get_terms(query) if len(t) > 2]
            if len(terms) > MAX_VIDEO_SEARCH_TERMS:
                terms = terms[:MAX_VIDEO_SEARCH_TERMS]
            new_query = u' '.join(u'+"{}"'.format(t) for t in terms)
            return self.filter(search_text__search=new_query)

    def add_num_completed_languages(self):
        sql = ("""
               (SELECT COUNT(*) FROM subtitles_subtitlelanguage sl
               WHERE sl.video_id=videos_video.id AND
               sl.subtitles_complete)""")
        return self.extra(select={
            'num_completed_languages': sql
        })

    def any_completed_languages(self):
        sql = ("""
               EXISTS (SELECT * FROM subtitles_subtitlelanguage sl
               WHERE sl.video_id=videos_video.id AND
               sl.subtitles_complete)""")
        return self.extra(where=[sql])

    def no_completed_languages(self):
        sql = ("""
               NOT EXISTS (SELECT * FROM subtitles_subtitlelanguage sl
               WHERE sl.video_id=videos_video.id AND
               sl.subtitles_complete)""")
        return self.extra(where=[sql])

    def has_completed_language(self, language_code):
        sql = ("""
               EXISTS (SELECT * FROM subtitles_subtitlelanguage sl
               WHERE sl.video_id=videos_video.id AND
               sl.language_code=%s AND sl.subtitles_complete)""")
        return self.extra(where=[sql], params=[language_code])

    def missing_completed_language(self, language_code):
        sql = ("""
               NOT EXISTS (SELECT * FROM subtitles_subtitlelanguage sl
               WHERE sl.video_id=videos_video.id AND
               sl.language_code=%s AND sl.subtitles_complete)""")
        return self.extra(where=[sql], params=[language_code])

    def for_url(self, url):
        return self.filter(videourl__url_hash=url_hash(url))

class SubtitleLanguageFetcher(object):
    """Fetches/caches subtitle languages for videos."""
    def __init__(self):
        self.cache = {}
        self.all_languages_fetched = False

    def fetch_one_language(self, video, language_code, create=False):
        if language_code in self.cache:
            return self.cache[language_code]
        try:
            lang = (video.newsubtitlelanguage_set
                    .get(language_code=language_code))
            lang.video = video
        except models.ObjectDoesNotExist:
            if create:
                lang = video.newsubtitlelanguage_set.create(
                    language_code=language_code)
            else:
                lang = None
        self.cache[language_code] = lang
        return lang

    def fetch_all_languages(self, video):
        if self.all_languages_fetched:
            return [l for l in self.cache.values() if l is not None]

        languages = list(video.newsubtitlelanguage_set.all())
        for lang in languages:
            lang.video = video
            self.cache[lang.language_code] = lang
        self.all_languages_fetched = True
        return languages

    def prefetch_languages(self, video, languages, with_public_tips,
                           with_private_tips):
        language_qs = video.newsubtitlelanguage_set.all()
        if languages is not None:
            language_qs = language_qs.filter(
                language_code__in=languages)
        fetched_languages = language_qs.fetch_and_join(
            video=video, public_tips=with_public_tips,
            private_tips=with_private_tips)
        for lang in fetched_languages:
            self.cache[lang.language_code] = lang
        if languages is None:
            self.all_languages_fetched = True

    def clear_cache(self):
        self.cache = {}
        self.all_languages_fetched = False

class VideoCacheManager(ModelCacheManager):
    def __init__(self, cache_pattern=None):
        super(VideoCacheManager, self).__init__(cache_pattern)
        self._video_id_to_pk = {}

    def get_instance(self, pk, cache_pattern=None):
        video = super(VideoCacheManager, self).get_instance(pk, cache_pattern)
        # use a cached team_video as well
        video._cached_teamvideo = self._get_team_video_from_cache(video)
        return video

    def _get_team_video_from_cache(self, video):
        from teams.models import TeamVideo
        try:
            team_video = video.cache.get_model(TeamVideo, 'teamvideo')
            if team_video is not None:
                team_video.video = video
                return team_video
        except TeamVideo.DoesNotExist:
            return None
        # cache miss
        team_video = video.get_team_video()
        video.cache.set_model('teamvideo', team_video)
        return team_video

    def get_instance_by_video_id(self, video_id, cache_pattern=None):
        return self.get_instance(self._pk_for_video_id(video_id),
                                 cache_pattern)

    def _pk_for_video_id(self, video_id):
        # find the video PK using the video ID.  This should never take a long
        # time so we cache it in several ways
        try:
            return self._video_id_to_pk[video_id]
        except KeyError:
            pass
        cache_key = 'videopk:{0}'.format(video_id)
        pk = cache.get(cache_key)
        if pk is None:
            pk = Video.objects.get(video_id=video_id).pk
            cache.set(cache_key, pk)
        self._video_id_to_pk[video_id] = pk
        return pk

class VideoFieldMonitor(object):
    """Monitor model fields for the Video model"""

    # map field names to signals
    field_map = {
        'title': signals.title_changed,
        'duration': signals.duration_changed,
        'primary_audio_language_code': signals.language_changed,
    }

    def __init__(self, video):
        self.data = {
            name: getattr(video, name, None)
            for name in self.field_map
        }

    def on_save(self, video, created):
        """Call this in the save() method.  If any of the fields have changed,
        then we will emit the corresponding signal.
        """
        for name in self.field_map:
            new_value = getattr(video, name, None)
            old_value = self.data[name]
            if new_value != old_value:
                self.data[name] = new_value
                if not created:
                    self.send_signal(video, name, old_value)

    def send_signal(self, video, name, old_value):
        signal = self.field_map[name]
        kwargs = {
            'old_{}'.format(name): old_value
        }
        signal.send(sender=video, **kwargs)

class Video(models.Model):
    """Central object in the system"""

    video_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=2048, blank=True)
    description = models.TextField(blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True, help_text=_(u'in seconds'))
    allow_community_edits = models.BooleanField(default=False)
    allow_video_urls_edit = models.BooleanField(default=True)
    writelock_time = models.DateTimeField(null=True, editable=False)
    writelock_session_key = models.CharField(max_length=255, editable=False)
    writelock_owner = models.ForeignKey(User, null=True, editable=False,
                                        related_name="writelock_owners")
    is_subtitled = models.BooleanField(default=False)
    was_subtitled = models.BooleanField(default=False, db_index=True)
    thumbnail = models.CharField(max_length=500, blank=True)
    small_thumbnail = models.CharField(max_length=500, blank=True)
    s3_thumbnail = S3EnabledImageField(
        blank=True,
        upload_to='video/thumbnail/',
        thumb_sizes=(
            (720,405),
            (480,270),
            (288,162),
            (120,90),))
    edited = models.DateTimeField(null=True, editable=False)
    created = models.DateTimeField()
    user = models.ForeignKey(User, null=True, blank=True,
                             default=settings.ANONYMOUS_USER_ID)
    followers = models.ManyToManyField(User, blank=True, related_name='followed_videos', editable=False)
    complete_date = models.DateTimeField(null=True, blank=True, editable=False)
    featured = models.DateTimeField(null=True, blank=True)
    # Metadata fields for this video.  These are translatable strings for
    # metadata on the video.  One example is Speaker name for TED videos.
    #
    # This overlaps with VideoMetadata, but we hopefully will be phasing that
    # out.
    meta_1_type = metadata.MetadataTypeField()
    meta_1_content = metadata.MetadataContentField()
    meta_2_type = metadata.MetadataTypeField()
    meta_2_content = metadata.MetadataContentField()
    meta_3_type = metadata.MetadataTypeField()
    meta_3_content = metadata.MetadataContentField()

    # counter for the # of times the video page is shown in the unisubs website
    view_count = models.PositiveIntegerField(_(u'Views'), default=0, db_index=True, editable=False)

    # Denormalizing the subtitles(had_version) count, in order to get faster joins
    # updated from update_languages_count()
    languages_count = models.PositiveIntegerField(default=0, db_index=True, editable=False)
    moderated_by = models.ForeignKey("teams.Team", blank=True, null=True, related_name="moderating")

    # denormalized convenience from VideoVisibility, should not be set
    # directely
    is_public = models.BooleanField(default=True)
    primary_audio_language_code = models.CharField(
        max_length=16, blank=True, default='',
        choices=translation.ALL_LANGUAGE_CHOICES)
    search_text = models.TextField(default='')

    cache = VideoCacheManager()

    objects = VideoQuerySet.as_manager()

    class DuplicateUrlError(Exception):
        """
        Raised where a video URL would be added twice to videos on the same
        team or two non-team videos.

        Attributes:
          video: Video for the URL
          video_url: VideoUrl for the URL
          from_prevent_duplicate_public_videos: Was this caused be a team
              with the prevent_duplicate_public_videos flag set?
        """
        def __init__(self, video_url,
                     from_prevent_duplicate_public_videos=False):
            self.video_url = video_url
            self.video = video_url.video
            self.from_prevent_duplicate_public_videos = \
                from_prevent_duplicate_public_videos

        def __unicode__(self):
            return 'Video.DuplicateUrlError: {}'.format(self.video_url.url)

    def __init__(self, *args, **kwargs):
        super(Video, self).__init__(*args, **kwargs)
        self._language_fetcher = SubtitleLanguageFetcher()
        self.monitor = VideoFieldMonitor(self)
        self.re_unicode = re.compile(u'[^\u0000-\uD7FF\uE000-\uFFFF]', re.UNICODE)
    def __unicode__(self):
        title = self.title_display()
        if len(title) > 35:
            title = title[:35]+'...'
        return title

    def save(self, *args, **kwargs):
        creating = self.id is None
        if creating:
            self.created = dates.now()
        super(Video, self).save(*args, **kwargs)
        self.monitor.on_save(self, creating)

    def delete(self, user=None):
        signals.video_deleted.send(sender=self, user=user)
        super(Video, self).delete()

    def update_search_index(self, commit=True):
        """Update this video's search index text."""

        self.search_text = self.calc_search_text(MAX_SEACH_TEXT_LENGTH)
        if commit:
            self.save()

    def calc_search_text(self, max_length=None):
        parts = [
            self.title_display(),
            self.description,
            self.video_id,
            self.meta_1_content,
            self.meta_2_content,
            self.meta_3_content,
        ]
        parts.extend(vurl.url for vurl in self.get_video_urls())
        for tip in self.newsubtitleversion_set.public_tips():
            parts.extend([
                tip.title, tip.description,
                tip.meta_1_content, tip.meta_2_content, tip.meta_3_content,
            ])

        text = '\n'.join(p for p in parts if p is not None)
        if max_length is not None:
            text = text[:max_length]
        return text

    def title_display(self, use_language_title=True):
        """
        Get the full title to display for users

        :param use_language_title: should we fetch the title from our primary
        audio language?
        """
        if self.title:
            return self.title
        video_url = self.get_primary_videourl_obj()
        if video_url:
            return make_title_from_url(video_url.url)
        else:
            return 'No title'

    def update_title(self, user, new_title):
        from subtitles.pipeline import add_subtitles
        from subtitles.models import ORIGIN_MANAGEMENT_PAGE
        old_title = self.title
        with transaction.atomic():
            self.title = new_title
            self.save()
            subtitle_language = self.get_primary_audio_subtitle_language()
            if subtitle_language:
                version = subtitle_language.get_tip()
                if version:
                    subtitles = version.get_subtitles()
                    add_subtitles(
                        self, subtitle_language.language_code, subtitles,
                        title=new_title, author=user, committer=self.user,
                        visibility=version.visibility,
                        origin=ORIGIN_MANAGEMENT_PAGE,
                        visibility_override=version.visibility_override)
        signals.video_title_edited.send(sender=self, user=user,
                                        old_title=self.title)
        self.update_search_index()

    def get_subtitle(self):
        return behaviors.get_video_subtitle(self, self.get_metadata())

    def get_download_filename(self):
        """Get the filename to download this video as

        This is basically the video title, with some chars replaced.
        """
        title = self.title_display()
        # replace newlines with ' '
        title = title.replace("\n", ' ')
        # remove any questionable characters
        return re.sub(r'(?u)[^-\w ]', '', title)

    def get_thumbnail(self, fallback=True):
        """Return a URL to this video's thumbnail.

        This may be an absolute or relative URL, depending on whether the
        thumbnail is stored in our media folder or on S3.

        If fallback is True, it will fallback to the default thumbnail

        """
        if self.s3_thumbnail:
            return self.s3_thumbnail.url

        if self.thumbnail:
            return self.thumbnail
        if fallback:
            return "%simages/video-no-thumbnail-medium.png" % settings.STATIC_URL

    def get_huge_thumbnail(self):
        """Return a URL to a huge version of this video's thumbnail

        This may be an absolute or relative URL, depending on whether the
        thumbnail is stored in our media folder or on S3.

        """
        if self.s3_thumbnail:
            return self.s3_thumbnail.thumb_url(720, 405)

        if self.thumbnail:
            return self.thumbnail
        return "%simages/video-no-thumbnail-wide.png" % settings.STATIC_URL

    def get_wide_thumbnail(self):
        """Return a URL to a widescreen version of this video's thumbnail

        This may be an absolute or relative URL, depending on whether the
        thumbnail is stored in our media folder or on S3.

        """
        if self.s3_thumbnail:
            return self.s3_thumbnail.thumb_url(480, 270)

        if self.thumbnail:
            return self.thumbnail
        return "%simages/video-no-thumbnail-wide.png" % settings.STATIC_URL

    def get_small_thumbnail(self):
        """Return a URL to a small version of this video's thumbnail

        This may be an absolute or relative URL, depending on whether the
        thumbnail is stored in our media folder or on S3.

        """
        if self.s3_thumbnail:
            return self.s3_thumbnail.thumb_url(120, 90)

        if self.small_thumbnail:
            return self.small_thumbnail

        if self.thumbnail:
            return self.thumbnail

        return "%simages/video-no-thumbnail-small.png" % settings.STATIC_URL

    def get_medium_thumbnail(self):
        """Return a URL to a medium version of this video's thumbnail, or '' if there isn't one.

        This may be an absolute or relative URL, depending on whether the
        thumbnail is stored in our media folder or on S3.

        """
        if self.s3_thumbnail:
            return self.s3_thumbnail.thumb_url(288, 162)

        if self.thumbnail:
            return self.thumbnail

        return "%simages/video-no-thumbnail-medium.png" % settings.STATIC_URL

    def is_team_video(self):
        return bool(self.get_team_video())

    def get_team_video(self):
        """Return the TeamVideo object for this video, or None if there isn't one."""
        from teams.models import TeamVideo

        # django caches the teamvideo attribute, but only if it's not None.
        # So we do our own caching here as well
        if hasattr(self, '_cached_teamvideo'):
            return self._cached_teamvideo
        try:
            team_video = self.teamvideo
            if team_video is not None:
                team_video.video = self
            rv = team_video
        except TeamVideo.DoesNotExist:
            rv = None
        self._cached_teamvideo = rv
        return rv

    def get_team(self):
        """Return the Team for this video or None."""
        team_video = self.get_team_video()
        return team_video.team if team_video else None

    def clear_team_video_cache(self):
        if hasattr(self, '_cached_teamvideo'):
            del self._cached_teamvideo

    def get_workflow(self):
        # need to import here because things are all tangled up
        from subtitles.workflows import get_workflow
        if not hasattr(self, '_cached_workflow'):
            self._cached_workflow = get_workflow(self)
        return self._cached_workflow

    def clear_workflow_cache(self):
        if hasattr(self, '_cached_workflow'):
            del self._cached_workflow

    def can_user_see(self, user):
        return self.get_workflow().user_can_view_video(user)

    def is_html5(self):
        """Return whether if the original URL for this video is an HTML5 one."""
        try:
            return self.videourl_set.filter(original=True)[:1].get().is_html5()
        except models.ObjectDoesNotExist:
            return False

    def search_page_url(self):
        return self.get_absolute_url()

    def title_for_url(self):
        """Return this video's title with non-URL-friendly characters replaced.

        NOTE: this method is used in videos.search_indexes.VideoSearchResult to
        prevent duplication of code in search result and in DB-query result.

        """
        return pan_slugify(self.title)

    def _get_absolute_url(self, video_id=None):
        """
        NOTE: this method is used in videos.search_indexes.VideoSearchResult
        to prevent duplication of code in search result and in DB-query result

        This is a little hack, because Django uses get_absolute_url in own way,
        so it was impossible just copy to VideoSearchResult
        """
        kwargs = {'video_id': video_id or self.video_id}
        title = self.title_for_url()
        if title:
            kwargs['title'] = title
            return reverse('videos:video_with_title',
                           kwargs=kwargs)
        return reverse('videos:video',  kwargs=kwargs)

    get_absolute_url = _get_absolute_url

    def get_language_url(self, language_code):
        if language_code in (None, ''):
            return ''
        return reverse('videos:translation_history_legacy', kwargs={
            'video_id': self.video_id,
            'lang': language_code,
        })

    def get_language_url_with_id(self, language_code):
        sl = self.subtitle_language(language_code)
        if sl is None:
            self.get_language_url(language_code)
        else:
            return reverse('videos:translation_history', kwargs={
                'video_id': self.video_id,
                'lang': language_code,
                'lang_id': int(sl.id),
            })

    def get_primary_videourl_obj(self):
        """Return the primary video URL for this video if one exists, otherwise None.

        This will return a VideoUrl object.

        """
        try:
            return self.videourl_set.filter(primary=True).all()[:1].get()
        except models.ObjectDoesNotExist:
            return None

    def get_video_url(self):
        """Return the primary video URL for this video if one exists, otherwise None.

        This will return a string of an actual URL, not a VideoUrl.

        """
        vurl = self.get_primary_videourl_obj()
        return vurl.url if vurl else None

    def get_video_url_type_display(self):
        vurl = self.get_primary_videourl_obj()
        return vurl.get_type_display() if vurl else _("No Video URL")

    def get_video_urls(self):
        """Return the video URLs for this video."""
        return self.videourl_set.all()

    def url_count(self):
        return self.cache.get_or_calc('url-count', self._calc_url_count)

    def _calc_url_count(self):
        return self.videourl_set.count()

    @classmethod
    def add(cls, url, user, setup_callback=None, team=None):
        """
        Add a new Video

        Note:
            If you want to do some extra setup of the video like setting some
            attributes, adding it to a team, etc, then you must use the
            setup_callback param to do it.  Simply calling add_video(), then
            do the setup after creates a race condition because we have all
            kinds of tasks that run once a video is added.  There's no knowing
            if those tasks will happen before or after your database update
            gets committed.

        Args:
            url: URL of the video to add (either a string or a VideoType)
            user: User adding the video
            setup_callback: callback function to do extra setup on the video.
              It will be passed 2 args: a Video and VideoUrl.  Video.save()
              will be called after, so there's no need to call it in
              setup_callback().
            team: Team that the video will be added to

        Raises:
            VideoTypeError: The video URL is invalid
            Video.DuplicateUrlError: The video URL has already been added for
                the team

        Returns:
            (video, video_url) tuple
        """
        with transaction.atomic():
            url = url_escape(url)
            video, video_url = cls._get_video_for_add(url, user, team)
            if setup_callback:
                setup_callback(video, video_url)
            video.update_search_index()
            video.save()
            if user and user.notify_by_message:
                video.followers.add(user)
        # Run post-creation code
        video_cache.invalidate_cache(video.video_id)
        video.cache.invalidate()
        signals.video_added.send(sender=video, video_url=video_url)
        signals.video_url_added.send(sender=video_url, video=video,
                                     new_video=True, user=user, team=team)
        return (video, video_url)

    @classmethod
    def _get_video_for_add(cls, url, user, team):
        """Get a video for Video.add()

        Normally this means creating a new video, but if
        team.prevent_duplicate_public_videos is set, then sometimes we'll use
        an existing public video and move it to the team.
        """
        vt, url = cls._coerce_url_param(url)
        # handle the prevent_duplicate_public_videos flag
        if team and team.prevent_duplicate_public_videos:
            try:
                public_video_url = (
                    VideoUrl.objects
                    .filter(url=url, team_id=0)
                    .select_related('video').get())
                public_video_url.team_id = team.id
                public_video_url.save()
                return public_video_url.video, public_video_url
            except VideoUrl.DoesNotExist:
                pass
        elif not team:
            cls._check_prevent_duplicate_public_videos(url)
        # We need to be a little careful when creating the VideoUrl.
        # We want to call VideoUrl.get_or_create() and we need to pass a Video
        # objects to that.  However, we don't want to fully set up the video
        # since that's wasted work if the VideoUrl already exists.
        #
        # To work around this, we create an video without the setup code,
        # and use that for video._add_video_url().  If that works, then we can
        # run the setup code.
        video = Video.objects.create()
        video_url = video._add_video_url(vt, user, True, team)
        # okay, we can now run the setup
        incomplete = video.set_values(vt, video_url, user, team)
        video.user = user
        if not (incomplete or video.title):
            video.title = make_title_from_url(video_url.url)
        return video, video_url

    def set_values(self, video_type, video_url, user, team):
        incomplete = video_type.set_values(self, user, team, video_url)
        if not incomplete:
            if self.title is None:
                self.title = ""
            else:
                self.title = self.re_unicode.sub(u'\uFFFD', self.title)
            if self.description is None:
                self.description = ""
            else:
                self.description = self.re_unicode.sub(u'\uFFFD', self.description)
        return incomplete

    def add_url(self, url, user):
        """
        Add an extra URL to an existing video

        Args:
            url: URL of the video to add (either a string or a VideoType)
            user: User adding the URL

        Returns:
            VideoUrl object that was added

        Raises:
            Video.DuplicateUrlError: The URL was already added to a
                                     different video
        """
        team = self.get_team()
        vt, url = self._coerce_url_param(url)
        self._check_prevent_duplicate_public_videos(url, team)
        video_url = self._add_video_url(vt, user, False, team)
        if type(vt) is YoutubeVideoType:
            try:
                video_info, incomplete = vt.get_video_info(self, user, team, video_url)
                YoutubeVideoType.set_owner_username(self, video_url, video_info)
            except google.APIError:
                pass
        elif type(vt) is VimeoVideoType:
            try:
                video_info = vt.get_video_info(user, team, video_url)
                VimeoVideoType.set_owner_username(video_url, video_info[4])
            except Exception:
                pass

        video_cache.invalidate_cache(self.video_id)
        self.cache.invalidate()
        signals.video_url_added.send(sender=video_url, video=self,
                                     new_video=False)

        return video_url

    def _add_video_url(self, vt, user, primary, team):
        # Low-level video URL adding code for add() and add_url()
        team_id = team.id if team else 0
        video_url, created = VideoUrl.objects.get_or_create(
            url=vt.convert_to_video_url(), team_id=team_id,
                type=vt.abbreviation,
            defaults={
                'video': self,
                'added_by': user,
                'primary': primary,
                'original': primary,
                'videoid': vt.video_id if vt.video_id else '',
            })
        if not created:
            raise Video.DuplicateUrlError(video_url)
        return video_url

    @staticmethod
    def _coerce_url_param(url):
        """Get a VideoType object for an url param

        Several of our methods input a url param that can be either a string,
        or a VideoType object.  This method handles standardizing the
        paramaters

        returns: (VideoType, str) tuple with the VideoType and the URL as a
        string
        raises VideoTypeError: can't find a VideoType for a URL
        """
        if isinstance(url, basestring):
            vt = video_type_registrar.video_type_for_url(url)
            if vt is None:
                raise VideoTypeError(url)
        else:
            vt = url
        return vt, vt.convert_to_video_url()

    @classmethod
    def _check_prevent_duplicate_public_videos(cls, url, team=None,
                                               ignore_video=None):
        """Check if there are any duplicate video URLs on teams with
        prevent_duplicate_public_videos set

        Call this whenever a URL is being added to amara, or moved to a team

        Args:
            url(str): url being added
            team(Team): team the URL is being added to, or None if it's being
                added to the public area
            video(Video): Video to ignore for the URL checking.  We use this
                when we move a video to/from a team and need to ignore the
                video being moved when performing the check.
        """
        if team and team.prevent_duplicate_public_videos:
            # Adding to a team with prevent_duplicate_public_videos set, check
            # for videos in the public area
            qs = VideoUrl.objects.filter(url=url, video__teamvideo__isnull=True)
        elif not team:
            # Adding to the public are, check for teams with
            # prevent_duplicate_public_videos set
            qs = VideoUrl.objects.filter(
                url=url, video__teamvideo__team__prevent_duplicate_public_videos=True)
        else:
            # nothing to check
            return

        if ignore_video:
            qs = qs.exclude(video=ignore_video)

        # We don't care about video URLs past the first, so add a LIMIT clause
        # to make the query go a bit faster
        qs = qs[:1]

        if qs:
            raise Video.DuplicateUrlError(
                qs[0], from_prevent_duplicate_public_videos=True)

    def update_team(self, team):
        """Update the team for this video

        This method must be called whenever the video changes teams.  For
        example:

            - Being added to a team from the public area (new TeamVideo object
              created)
            - Being moved from team to team (TeamVideo object changed)
            - Being moved from a team back to the public area (TeamVideo
              object deleted)

        Raises:
            DuplicateUrlError: One of the video URLs for this video was
                already added to the team
        """
        for vurl in self.get_video_urls():
            self._check_prevent_duplicate_public_videos(vurl.url, team,
                                                        ignore_video=self)
        new_team_id = team.id if team else 0
        try:
            with transaction.atomic():
                self.videourl_set.update(team_id=new_team_id)
        except IntegrityError:
            for vurl in self.get_video_urls():
                try:
                    dup_vurl = VideoUrl.objects.get(
                        url=vurl.url, type=vurl.type, team_id=new_team_id)
                    raise Video.DuplicateUrlError(vurl)
                except VideoUrl.DoesNotExist:
                    pass
            raise

    @property
    def language(self):
        """Return the language code of this video's original language as a string.

        Will return None if unknown.

        """
        return self.primary_audio_language_code or None

    @property
    def readable_language(self):
        if self.primary_audio_language_code:
            return translation.get_language_label(self.primary_audio_language_code)
        else:
            return None

    @property
    def filename(self):
        """Return a filename-safe version of this video's string representation.

        Could be useful when providing a user with a file related to this video
        to download, etc.

        """
        from django.utils.text import get_valid_filename

        return get_valid_filename(self.title_display())

    def lang_filename(self, language):
        """Return a filename-safe version of this video's string representation with a language code.

        Could be useful when providing a user with a file of subs to download,
        etc.

        """
        name = self.filename
        if not isinstance(language, basestring):
            lang = language.language or u'original'
        else:
            lang = language
        return u'%s.%s' % (name, lang)

    @property
    def subtitle_state(self):
        """Return the subtitling state for this video.

        The value returned will be one of the NO_SUBTITLES or SUBTITLES_FINISHED
        constants.

        """
        return NO_SUBTITLES if self.latest_version() is None else SUBTITLES_FINISHED

    def get_primary_audio_subtitle_language(self):
        """Return the SubtitleLanguage for the primary audio language, or None.

        Caches the result in the object.

        """
        return self._original_subtitle_language()

    def _original_subtitle_language(self):
        """Return the SubtitleLanguage in the original language of this video, or None.

        Caches the result in the object.

        """
        if not hasattr(self, '_original_subtitle'):
            try:
                palc = self.primary_audio_language_code
                original = (self.newsubtitlelanguage_set
                                .filter(language_code=palc)[:1].get())
            except models.ObjectDoesNotExist:
                original = None

            setattr(self, '_original_subtitle', original)

        return getattr(self, '_original_subtitle')

    def has_original_language(self):
        """Return whether this video has a SubtitleLanguage for its original language.

        NOTE: this uses another method which caches the result in the object, so
        this will effectively be cached in-object as well.

        """
        return True if self._original_subtitle_language() else False

    def is_rtl(self):
        return (self.primary_audio_language_code
                and translation.is_rtl(self.primary_audio_language_code))

    def subtitle_language(self, language_code=None, create=False):
        """Get as SubtitleLanguage for this video

        If None is passed as a language_code, the original language
        SubtitleLanguage will be returned.  In this case the value will be
        cached in-object.
        """
        if language_code is None:
            language_code = self.primary_audio_language_code
            if not language_code:
                if create:
                    raise ValueError("no primary audio language set")
                return None
        return self._language_fetcher.fetch_one_language(self, language_code,
                                                         create)

    def all_subtitle_languages(self):
        return self._language_fetcher.fetch_all_languages(self)

    def languages_with_versions(self):
        cached = self.cache.get('langs-with-versions')
        if cached is not None:
            return cached
        languages = [
            l.language_code for l in
            self.newsubtitlelanguage_set.having_versions()
        ]
        self.cache.set('langs-with-versions', languages)
        return languages

    def language_with_pk(self, language_pk):
        language_pk = int(language_pk)
        for lang in self.all_subtitle_languages():
            if lang.pk == language_pk:
                return lang
        return None

    def prefetch_languages(self, languages=None, with_public_tips=False,
                           with_private_tips=False):
        """Prefetch and cache languages/versions for this video

        This method fetches subtitle languages and subtitle versions for this
        video and sets up various caches to reduce future queries.

        :lanuages: list of languages to fetch, or None to fetch all languages.
        subtitle_language() and all_subtitle_languages() will cache these
        languages.
        :with_public_tips: fetch the public tips for all the languages and
        cache them
        :with_private_tips: fetch the private tips for all the languages and
        cache them
        """
        self._language_fetcher.prefetch_languages(self, languages,
                                                  with_public_tips,
                                                  with_private_tips)

    def clear_language_cache(self):
        self._language_fetcher.clear_cache()

    def subtitle_languages(self, language_code):
        """Return all SubtitleLanguages for this video with the given language code."""
        return self.newsubtitlelanguage_set.filter(language_code=language_code)

    def incomplete_languages(self):
        return [
            l for l in self.all_subtitle_languages() if not l.subtitles_complete
        ]

    def complete_languages(self):
        return [
            l for l in self.all_subtitle_languages() if l.subtitles_complete
        ]

    def complete_or_writelocked_language_codes(self):
        return [
            l.language_code for l in self.all_subtitle_languages() if l.subtitles_complete 
                                                                   or l.is_writelocked
        ]

    def incomplete_languages_sorted(self):
        return sorted(self.incomplete_languages(), key=lambda l: l.language_code)
    
    def complete_languages_sorted(self):
        return sorted(self.complete_languages(), key=lambda l: l.language_code)

    def incomplete_languages_with_public_versions(self):
        self.prefetch_languages(with_public_tips=True)
        return [
            l for l in self.all_subtitle_languages()
            if not l.subtitles_complete and l.get_public_tip() is not None
        ]

    def complete_languages_with_public_versions(self):
        self.prefetch_languages(with_public_tips=True)
        return [
            l for l in self.all_subtitle_languages()
            if l.subtitles_complete and l.get_public_tip() is not None
        ]

    def get_merged_dfxp(self):
        """Get a DFXP file containing subtitles for all languages."""
        self.prefetch_languages(with_public_tips=True)

        subtitle_sets = []
        for language in self.all_subtitle_languages():
            tip = language.get_public_tip()
            if tip is not None:
                if language.is_primary_audio_language():
                    subtitle_sets.insert(0, tip.get_subtitles())
                else:
                    subtitle_sets.append(tip.get_subtitles())

        if len(subtitle_sets) > 0:
            return dfxp_merge(subtitle_sets)
        else:
            return None

    def version(self, version_number=None, language=None, public_only=True):
        """Return the SubtitleVersion for this video matching the given criteria.

        If language is given (it must be a SubtitleLanguage, NOT a string
        language code) the version will be looked up for that, otherwise the
        original language will be used.

        If version_no is given, the version with that number will be returned.

        If public_only is True (the default) only versions visible to the public
        (i.e.: not moderated) will be considered.  If it is false all versions
        are eligable.

        If no version fitting all the criteria is found, None is returned.

        """
        if language is None:
            language = self.subtitle_language()

        return (None if language is None else
                language.version(version_number=version_number,
                                 public_only=public_only))

    def latest_version(self, language_code=None, public_only=True):
        """Return the latest SubtitleVersion for this video matching the given criteria.

        If language is given (as a language code string) the version will be
        looked up for that, otherwise the original language will be used.

        If public_only is True (the default) only versions visible to the public
        (i.e.: not moderated) will be considered.  If it is false all versions
        are eligable.

        If no version fitting all the criteria is found, None is returned.

        Deleted versions cannot be retrieved with this method.  If you need
        those you'll need to look them up another way.

        """
        language = self.subtitle_language(language_code)
        return None if language is None else language.get_tip(public=public_only)

    def has_public_version(self):
        """Check if there are any public versions for any language."""
        if hasattr(self, '_has_public_version'):
            return bool(self._has_public_version)
        return self.newsubtitlelanguage_set.having_public_versions().exists()

    def subtitles(self, version_number=None, language_code=None, language_pk=None):
        if language_pk is None:
            language = self.subtitle_language(language_code)
        else:
            try:
                language = self.newsubtitlelanguage_set.get(pk=language_pk)
            except models.ObjectDoesNotExist:
                language = None

        version = self.version(version_number, language)

        if version:
            return version.get_subtitles()
        else:
            language_code = language.language_code if language else self.primary_audio_language_code
            return create_new_subtitles(language_code)

    def latest_subtitles(self, language_code=None, public_only=True):
        version = self.latest_version(language_code, public_only=public_only)
        return [] if version is None else version.get_subtitles()

    def translation_language_codes(self):
        """All iso language codes with finished translations."""
        return set([sl.language for sl
                    in self.newsubtitlelanguage_set.filter(
                    subtitles_complete=True).filter(is_forked=False)])

    def user_is_follower(self, user):
        followers = self.cache.get('followers')
        if followers is None:
            followers = list(self.followers.values_list('id', flat=True))
            self.cache.set('followers', followers)
        return user.id in followers

    def notification_list(self, exclude=None):
        qs = self.followers.filter(notify_by_email=True, is_active=True)
        if exclude:
            if not isinstance(exclude, (list, tuple)):
                exclude = [exclude]
            qs = qs.exclude(pk__in=[u.pk for u in exclude if u and u.is_authenticated()])
        return qs

    def notification_list_all(self, exclude=None):
        users = []
        for language in self.newsubtitlelanguage_set.all():
            for u in language.notification_list(exclude):
                if not u in users:
                    users.append(u)
        for user in self.notification_list(exclude):
            if not user in users:
                users.append(user)
        return users

    def subtitle_language_dict(self):
        langs = {}
        for sl in self.newsubtitlelanguage_set.all():
            if not sl.language:
                continue
            if sl.language in langs:
                langs[sl.language_code].append(sl)
            else:
                langs[sl.language_code] = [sl]
        return langs

    def is_solo_subtitled_by_uploader(self):
        """
        Returns whether subtitles for this video has been worked upon only by the uploader 
        """
        return not self.newsubtitleversion_set.exclude(author=self.user).exists()

    @property
    def is_complete(self):
        """Return whether at least one of this video's languages is marked complete."""

        for sl in self.newsubtitlelanguage_set.all():
            if sl.is_complete_and_synced():
                return True
        return False

    def is_language_complete(self, lc):
        return (lc in [sl.language_code for sl in self.completed_subtitle_languages()])

    def completed_subtitle_languages(self, public_only=True):
        return [sl for sl in self.newsubtitlelanguage_set.all()
                if sl.is_complete_and_synced(public=public_only)]

    def get_description_display(self):
        """Return a suitable description to display to a user for this video.

        This will use the most specific description if it's present, but if it's
        blank it will fall back to the less-specific-but-at-least-it-exists
        video description instead.

        """
        l = self.subtitle_language()
        return l.get_description() if l else self.description

    @property
    def is_moderated(self):
        '''
        Delegates check to team.moderates_video to keep logic in one place.
        This is cached because the widget uses it, and else we'll incurr on
        extra db calls on each widget view.
        '''
        cached_attr_name = '_cache_is_moderated'
        if not hasattr(self, cached_attr_name):
            tv = self.get_team_video()
            setattr(self, cached_attr_name,  tv and tv.team.moderates_videos())
        return cached_attr_name

    def get_metadata(self):
        return metadata.get_metadata_for_video(self)

    def get_metadata_for_locale(self, language_code):
        language_for_locale = self.subtitle_language(language_code)
        if language_for_locale:
            return language_for_locale.get_metadata()
        else:
            return self.get_metadata()

    def update_metadata(self, new_metadata, commit=True):
        metadata.update_video(self, new_metadata, commit)

    def metadata(self):
        '''Return a dict of metadata for this video.

        Deprecated: don't use this function in new code.  See comments in
        VideoMetadata for why.

        Example:

        { 'author': 'Sample author',
          'creation_date': datetime(...), }

        '''
        meta = dict([(VIDEO_META_TYPE_VARS[md.key], md.data)
                     for md in self.videometadata_set.all()])

        meta['creation_date'] = VideoMetadata.string_to_date(meta.get('creation_date'))

        return meta

    @property
    def translations(self):
        from subtitles.models import SubtitleLanguage as SL
        return SL.objects.filter(video=self).exclude(
                language_code=self.primary_audio_language_code)

    def comment_count(self):
        return self.cache.get_or_calc('comment-count',
                                      self._calc_comment_count)

    def _calc_comment_count(self):
        return Comment.get_for_object(self).count()

    class Meta(object):
        permissions = (
            ("can_moderate_version"   , "Can moderate version" ,),
        )

@receiver(post_save, sender=Comment)
def on_comment_save(sender, instance, **kwargs):
    if isinstance(instance.content_object, Video):
        instance.content_object.cache.invalidate()

def create_video_id(sender, instance, **kwargs):
    """Generate (and set) a random video_id for this video before saving.

    Also fills in the edited timestamp.
    TODO: Split the 'edited' update out into a new function.

    """
    instance.edited = datetime.now()
    if not instance or instance.video_id:
        return
    alphanum = string.letters+string.digits
    instance.video_id = ''.join([random.choice(alphanum) for i in xrange(12)])

def video_delete_handler(sender, instance, **kwargs):
    video_cache.invalidate_cache(instance.video_id)

models.signals.pre_save.connect(create_video_id, sender=Video)
models.signals.pre_delete.connect(video_delete_handler, sender=Video)
models.signals.m2m_changed.connect(User.video_followers_change_handler, sender=Video.followers.through)

# VideoMetadata
#
# TODO: remove this this class.  We use this class for a couple things:
#
# Author and Creation Date for team videos.  Why do we need these things?
# Seems like they could easily be attributes on either Video and
# SubtitleVersion.  This probably can go away when we switch to the new
# collaboration model.
#
# Video IDs for partners like TED so we can translate back and forth between
# the our IDs and theirs.  However, it would be better/simpler to just use a
# map table for that.
class VideoMetadata(models.Model):
    video = models.ForeignKey(Video)
    key = models.PositiveIntegerField(choices=VIDEO_META_CHOICES)
    data = models.CharField(max_length=255)

    created = models.DateTimeField(editable=False, auto_now_add=True)
    modified = models.DateTimeField(editable=False, auto_now=True)

    @classmethod
    def add_metadata_type(cls, num, readable_name):
        """Add a new key choice.

        These can't be added at class creation time because some of those types
        live on the integration repo and therefore can't be referenced from
        here.

        This makes sure that if code is trying to do this dynamically we'll
        never allow it to overwrite a key with a different name.

        """
        field = VideoMetadata._meta.get_field('key')

        choices = field.choices
        for x in choices:
            if x[0] == num and x[1] != readable_name:
                raise ValueError(
                    "Cannot add a metadata value twice, tried %s -> %s which clashes with %s -> %s" %
                    (num, readable_name, x[0], x[1]))
            elif x[0] == num and x[1] == readable_name:
                return
        choices = choices + ((num, readable_name,),)

        # public attr is read only
        global VIDEO_META_CHOICES
        VIDEO_META_CHOICES = field._choices = choices
        update_metadata_choices()


    class Meta:
        ordering = ('created',)
        verbose_name_plural = 'video metadata'

    def __unicode__(self):
        data = self.data
        if len(data) > 30:
            data = data[:30] + '...'
        return u'%s - %s: %s' % (self.video,
                                 self.get_key_display(),
                                 data)

    @classmethod
    def date_to_string(cls, d):
        return d.strftime('%Y-%m-%d') if d else ''

    @classmethod
    def string_to_date(cls, s):
        return datetime.strptime(s, '%Y-%m-%d').date() if s else None


# SubtitleLanguage
class SubtitleLanguage(models.Model):
    video = models.ForeignKey(Video)
    is_original = models.BooleanField(default=False)
    language = models.CharField(max_length=16, choices=ALL_LANGUAGES, blank=True)
    writelock_time = models.DateTimeField(null=True, editable=False)
    writelock_session_key = models.CharField(max_length=255, blank=True, editable=False)
    writelock_owner = models.ForeignKey(User, null=True, blank=True, editable=False)
    is_complete = models.BooleanField(default=False)
    subtitle_count = models.IntegerField(default=0, editable=False)

    # has_version: Is there more than one version, and does the latest version
    # have more than 0 subtitles?
    has_version = models.BooleanField(default=False, editable=False,
            db_index=True)

    # had_version: Is there more than one version, and did some previous version
    # have more than 0 subtitles?
    had_version = models.BooleanField(default=False, editable=False)

    is_forked = models.BooleanField(default=False, editable=False)
    created = models.DateTimeField()
    followers = models.ManyToManyField(User, blank=True, related_name='followed_languages', editable=False)
    percent_done = models.IntegerField(default=0, editable=False)
    standard_language = models.ForeignKey('self', null=True, blank=True, editable=False)

    # Fields for the big DMR migration.
    needs_sync = models.BooleanField(default=True, editable=False)
    new_subtitle_language = models.ForeignKey('subtitles.SubtitleLanguage',
                                              related_name='old_subtitle_version',
                                              null=True, blank=True,
                                              editable=False)

    def save(self, updates_timestamp=True, *args, **kwargs):
        if 'tern_sync' not in kwargs:
            self.needs_sync = True
        else:
            kwargs.pop('tern_sync')

        if updates_timestamp:
            self.created = datetime.now()
        if self.language:
            assert self.language in VALID_LANGUAGE_CODES, \
                "Subtitle Language %s should be a valid code." % self.language
        super(SubtitleLanguage, self).save(*args, **kwargs)

    class Meta:
        unique_together = (('video', 'language', 'standard_language'),)

    def __unicode__(self):
        if self.is_original and not self.language:
            return 'Original'
        return self.get_language_display()

models.signals.m2m_changed.connect(User.sl_followers_change_handler,
                                   sender=SubtitleLanguage.followers.through)


# SubtitleVersion
class SubtitleVersion(models.Model):
    """
    user -> The legacy data model allowed null users. We do not allow it anymore, but
    for those cases, we've replaced it with the user created on the syncdb commit (see
    apps.auth.CustomUser.get_amara_anonymous.

    """
    language = models.ForeignKey(SubtitleLanguage)
    version_no = models.PositiveIntegerField(default=0)
    datetime_started = models.DateTimeField(editable=False)
    user = models.ForeignKey(User, default=None)
    note = models.CharField(max_length=512, blank=True)
    time_change = models.FloatField(null=True, blank=True, editable=False)
    text_change = models.FloatField(null=True, blank=True, editable=False)
    notification_sent = models.BooleanField(default=False)
    result_of_rollback = models.BooleanField(default=False)
    forked_from = models.ForeignKey("self", blank=True, null=True)
    is_forked=models.BooleanField(default=False)
    # should not be changed directly, but using teams.moderation. as those will take care
    # of keeping the state constant and also updating metadata when needed
    moderation_status = models.CharField(max_length=32, choices=MODERATION_STATUSES,
                                         default=UNMODERATED, db_index=True)

    title = models.CharField(max_length=2048, blank=True)
    description = models.TextField(blank=True, null=True)

    # Fields for the big DMR migration.
    needs_sync = models.BooleanField(default=True, editable=False)
    new_subtitle_version = models.OneToOneField('subtitles.SubtitleVersion',
                                                related_name='old_subtitle_version',
                                                null=True, blank=True,
                                                editable=False)

    class Meta:
        ordering = ['-version_no']
        unique_together = (('language', 'version_no'),)


    def __unicode__(self):
        return u'%s #%s' % (self.language, self.version_no)


def record_workflow_origin(version, team_video):
    """Figure out and record where the given version started out.

    Should be used right after creation.

    This is a giant ugly hack until we get around to refactoring the subtitle
    adding into a pipeline.  I'm sorry.

    In the future this should go away when we refactor the subtitle pipeline
    out, but until then I couldn't stomach copy/pasting this in three or more
    places.

    """
    if team_video and version and not version.get_workflow_origin():
        tasks = team_video.task_set.incomplete()
        tasks = list(tasks.filter(language=version.subtitle_language.language_code)[:1])

        if tasks:
            open_task_type = tasks[0].get_type_display()

            workflow_origin = {
                'Subtitle': 'transcribe',
                'Translate': 'translate',
                'Review': 'review',
                'Approve': 'approve'
            }.get(open_task_type)

            if workflow_origin:
                version.set_workflow_origin(workflow_origin)

def update_followers(sender, instance, created, **kwargs):
    user = instance.user
    lang = instance.language
    if created and user and user.notify_by_email:
        try:
            with transaction.atomic():
                lang.followers.add(user)
        except IntegrityError:
            # User already follows the language.
            pass
        try:
            with transaction.atomic():
                lang.video.followers.add(user)
        except IntegrityError:
            # User already follows the video.
            pass


post_save.connect(Awards.on_subtitle_version_save, SubtitleVersion)
post_save.connect(update_followers, SubtitleVersion)

class SubtitleVersionMetadata(models.Model):
    """This model is used to add extra metadata to SubtitleVersions.

    We could just continually add fields to SubtitleVersion, but that requires
    a new migration each time and bloats the model more and more.  Also, there
    are some pieces of data that are not usually needed, so it makes sense to
    keep them off of the main model.

    """
    KEY_CHOICES = (
        (100, 'reviewed_by'),
        (101, 'approved_by'),
        (200, 'workflow_origin'),
    )
    KEY_NAMES = dict(KEY_CHOICES)
    KEY_IDS = dict([choice[::-1] for choice in KEY_CHOICES])

    WORKFLOW_ORIGINS = ('transcribe', 'translate', 'review', 'approve')

    key = models.PositiveIntegerField(choices=KEY_CHOICES)
    data = models.TextField(blank=True)
    subtitle_version = models.ForeignKey(SubtitleVersion, related_name='metadata')

    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        unique_together = (('key', 'subtitle_version'),)
        verbose_name_plural = 'subtitle version metadata'

    def __unicode__(self):
        return u'%s - %s' % (self.subtitle_version, self.get_key_display())

    def get_data(self):
        if self.get_key_display() in ['reviewed_by', 'approved_by']:
            return User.objects.get(pk=int(self.data))
        else:
            return self.data


# Subtitle
class Subtitle(models.Model):
    version = models.ForeignKey(SubtitleVersion, null=True)
    subtitle_id = models.CharField(max_length=32, blank=True)
    subtitle_order = models.FloatField(null=True)
    subtitle_text = models.CharField(max_length=1024, blank=True)
    # in seconds. if no start time is set, should be null.
    start_time_seconds = models.FloatField(null=True, db_column='start_time')
    # storing both so we don't need to migrate everyone at once
    start_time = models.IntegerField(null=True, default=None, db_column='start_time_ms')
    # in seconds. if no end time is set, should be null.
    end_time_seconds = models.FloatField(null=True, db_column='end_time')
    # storing both so we don't need to migrate everyone at once
    end_time = models.IntegerField(null=True, default=None, db_column='end_time_ms')
    start_of_paragraph = models.BooleanField(default=False)

    class Meta:
        ordering = ['subtitle_order']
        unique_together = (('version', 'subtitle_id'),)


    def __unicode__(self):
        if self.pk:
            return u"(%4s) %s %s -> %s -  = %s -- Version %s" % (
                self.subtitle_order, self.subtitle_id, self.start_time,
                self.end_time,  self.subtitle_text, self.version_id)


# SubtitleMetadata
START_OF_PARAGRAPH = 1

SUBTITLE_META_CHOICES = (
    (START_OF_PARAGRAPH, 'Start of pargraph'),
)


class SubtitleMetadata(models.Model):
    subtitle = models.ForeignKey(Subtitle)
    key = models.PositiveIntegerField(choices=SUBTITLE_META_CHOICES)
    data = models.CharField(max_length=255)

    created = models.DateTimeField(editable=False, auto_now_add=True)
    modified = models.DateTimeField(editable=False, auto_now=True)

    class Meta:
        ordering = ('created',)
        verbose_name_plural = 'subtitles metadata'


# Action
from django.template.loader import render_to_string

class ActionRenderer(object):

    def __init__(self, template_name):
        self.template_name = template_name

    def render(self, item):

        if item.action_type == Action.ADD_VIDEO:
            info = self.render_ADD_VIDEO(item)
        elif item.action_type == Action.CHANGE_TITLE:
            info = self.render_CHANGE_TITLE(item)
        elif item.action_type == Action.COMMENT:
            info = self.render_COMMENT(item)
        elif item.action_type == Action.ADD_VERSION and item.new_language:
            info = self.render_ADD_VERSION(item)
        elif item.action_type == Action.ADD_VIDEO_URL:
            info = self.render_ADD_VIDEO_URL(item)
        elif item.action_type == Action.ADD_TRANSLATION:
            info = self.render_ADD_TRANSLATION(item)
        elif item.action_type == Action.SUBTITLE_REQUEST:
            info = self.render_SUBTITLE_REQUEST(item)
        elif item.action_type == Action.APPROVE_VERSION:
            info = self.render_APPROVE_VERSION(item)
        elif item.action_type == Action.REJECT_VERSION:
            info = self.render_REJECT_VERSION(item)
        elif item.action_type == Action.MEMBER_JOINED:
            info = self.render_MEMBER_JOINED(item)
        elif item.action_type == Action.MEMBER_LEFT:
            info = self.render_MEMBER_LEFT(item)
        elif item.action_type == Action.REVIEW_VERSION:
            info = self.render_REVIEW_VERSION(item)
        elif item.action_type == Action.ACCEPT_VERSION:
            info = self.render_ACCEPT_VERSION(item)
        elif item.action_type == Action.DECLINE_VERSION:
            info = self.render_DECLINE_VERSION(item)
        elif item.action_type == Action.DELETE_VIDEO:
            info = self.render_DELETE_VIDEO(item)
        elif item.action_type == Action.EDIT_URL:
            info = self.render_EDIT_URL(item)
        elif item.action_type == Action.DELETE_URL:
            info = self.render_DELETE_URL(item)
        else:
            info = ''

        context = {
            'info': info,
            'item': item
        }

        return render_to_string(self.template_name, context)

    def _base_kwargs(self, item):
        data = {'language_url': '', 'new_language':''}
        # deleted videos event have no video obj
        if item.video:
            data['video_url']= item.video.get_absolute_url()
            data['video_name'] = unicode(item.video)
        if item.new_language:
            data['new_language'] = item.new_language.get_language_code_display()
            data['language_url'] = item.new_language.get_absolute_url()
        if item.user:
            data["user_url"] = reverse("profiles:profile", kwargs={"user_id":item.user.id})
            data["user"] = item.user
        return data

    def render_REVIEW_VERSION(self, item):
        kwargs = self._base_kwargs(item)
        msg = fmt(_('  reviewed <a href="%(language_url)s">%(new_language)s</a> subtitles for <a href="%(video_url)s"> %(video_name)s</a>'), **kwargs)
        return msg

    def render_ACCEPT_VERSION(self, item):
        kwargs = self._base_kwargs(item)
        msg = fmt(_('  accepted <a href="%(language_url)s">%(new_language)s</a> subtitles for <a href="%(video_url)s">%(video_name)s</a>'), **kwargs)
        return msg

    def render_REJECT_VERSION(self, item):
        kwargs = self._base_kwargs(item)
        msg = fmt(_('  rejected <a href="%(language_url)s">%(new_language)s</a> subtitles for <a href="%(video_url)s">%(video_name)s</a>'), **kwargs)
        return msg

    def render_APPROVE_VERSION(self, item):
        kwargs = self._base_kwargs(item)
        msg = fmt(_('  approved <a href="%(language_url)s">%(new_language)s</a> subtitles for <a href="%(video_url)s">%(video_name)s</a>'), **kwargs)
        return msg

    def render_DECLINE_VERSION(self, item):
        kwargs = self._base_kwargs(item)
        msg = fmt(_('  declined <a href="%(language_url)s">%(new_language)s</a> subtitles for <a href="%(video_url)s">%(video_name)s</a>'), **kwargs)
        return msg

    def render_DELETE_VIDEO(self, item):
        kwargs = self._base_kwargs(item)
        kwargs['title'] = item.new_video_title
        msg = fmt(_('  deleted a video: "%(title)s"'), **kwargs)
        return msg

    def render_ADD_VIDEO(self, item):
        if item.user:
            msg = _(u'added <a href="%(video_url)s">&#8220;%(video_name)s&#8221;</a> to Amara')
        else:
            msg = _(u'<a href="%(video_url)s">%(video_name)s</a> added to Amara')

        return fmt(msg, **self._base_kwargs(item))

    def render_CHANGE_TITLE(self, item):
        if item.user:
            msg = _(u'changed title for <a href="%(video_url)s">%(video_name)s</a>')
        else:
            msg = _(u'Title was changed for <a href="%(video_url)s">%(video_name)s</a>')

        return fmt(msg, **self._base_kwargs(item))

    def render_COMMENT(self, item):
        kwargs = self._base_kwargs(item)

        if item.new_language:
            kwargs['comments_url'] = '%s#comments' % item.new_language.get_absolute_url()
        else:
            kwargs['comments_url'] = '%s#comments' % kwargs['video_url']

        if item.new_language:
            if item.user:
                msg = _(u'commented on <a href="%(comments_url)s">%(new_language)s subtitles</a> for <a href="%(video_url)s">%(video_name)s</a>')
            else:
                msg = _(u'Comment added for <a href="%(comments_url)s">%(new_language)s subtitles</a> for <a href="%(video_url)s">%(video_name)s</a>')
        else:
            if item.user:
                msg = _(u'commented on <a href="%(video_url)s">%(video_name)s</a>')
            else:
                msg = _(u'Comment added for <a href="%(video_url)s">%(video_name)s</a>')

        return fmt(msg, **kwargs)

    def render_ADD_TRANSLATION(self, item):
        kwargs = self._base_kwargs(item)

        if item.user:
            msg = _(u'started <a href="%(language_url)s">%(new_language)s subtitles</a> for <a href="%(video_url)s">%(video_name)s</a>')
        else:
            msg = _(u'<a href="%(language_url)s">%(new_language)s subtitles</a> started for <a href="%(video_url)s">%(video_name)s</a>')

        return fmt(msg, **kwargs)

    def render_ADD_VERSION(self, item):
        kwargs = self._base_kwargs(item)

        if item.user:
            msg = _(u'edited <a href="%(language_url)s">%(new_language)s subtitles</a> for <a href="%(video_url)s">%(video_name)s</a>')
        else:
            msg = _(u'<a href="%(language_url)s">%(new_language)s subtitles</a> edited for <a href="%(video_url)s">%(video_name)s</a>')

        return fmt(msg, **kwargs)

    def render_ADD_VIDEO_URL(self, item):
        if item.user:
            msg = _(u'added new URL for <a href="%(video_url)s">%(video_name)s</a>')
        else:
            msg = _(u'New URL added for <a href="%(video_url)s">%(video_name)s</a>')

        return fmt(msg, **self._base_kwargs(item))

    def render_MEMBER_JOINED(self, item):
        return fmt(_("joined the %(team)s team as a %(role)s"),
                   team=item.team, role=item.member.role)

    def render_MEMBER_LEFT(self, item):
        return fmt(_("left the %(team)s team"), team=item.team)

    def render_EDIT_URL(self, item):
        kwargs = self._base_kwargs(item)
        # de-serialize urls from json
        data = {}
        try:
            data = json.loads(item.new_video_title)
        except Exception, e:
            logger.error('Unable to parse urls: {0}'.format(e))
        kwargs['old_url'] = data.get('old_url', 'unknown')
        kwargs['new_url'] = data.get('new_url', 'unknown')
        msg = _('  changed primary url from <a href="%(old_url)s">%(old_url)s</a> to <a href="%(new_url)s">%(new_url)s</a>')
        return fmt(msg, **kwargs)

    def render_DELETE_URL(self, item):
        kwargs = self._base_kwargs(item)
        kwargs['title'] = item.new_video_title
        msg = _('  deleted url <a href="%(title)s">%(title)s</a>')
        return fmt(msg, **kwargs)

class ActionManager(models.Manager):
    def for_user(self, user):
        return self.filter(Q(user=user) | Q(team__in=user.teams.all())).distinct()

    def for_user_team_activity(self, user):
        return self.extra(
            tables=['teams_teammember'],
            where=['teams_teammember.team_id = videos_action.team_id',
                   'teams_teammember.user_id=%s'],
            params=[user.id]).exclude(user=user)

    def for_user_video_activity(self, user):
        return self.extra(
            tables=['auth_customuser_videos'],
            where=['auth_customuser_videos.video_id = videos_action.video_id',
                   'auth_customuser_videos.customuser_id=%s'],
            params=[user.id]).exclude(user=user)

    def for_video(self, video):
        return (Action.objects.filter(video=video)
                .select_related('user', 'video', 'new_language',
                                'new_language__video'))

class Action(models.Model):
    ADD_VIDEO = 1
    CHANGE_TITLE = 2
    COMMENT = 3
    ADD_VERSION = 4
    ADD_VIDEO_URL = 5
    ADD_TRANSLATION = 6
    SUBTITLE_REQUEST = 7
    APPROVE_VERSION = 8
    MEMBER_JOINED = 9
    REJECT_VERSION = 10
    MEMBER_LEFT = 11
    REVIEW_VERSION = 12
    ACCEPT_VERSION = 13
    DECLINE_VERSION = 14
    DELETE_VIDEO = 15
    EDIT_URL = 16
    DELETE_URL = 17
    TYPES = (
        (ADD_VIDEO, _(u'add video')),
        (CHANGE_TITLE, _(u'change title')),
        (COMMENT, _(u'comment')),
        (ADD_VERSION, _(u'add version')),
        (ADD_TRANSLATION, _(u'add translation')),
        (ADD_VIDEO_URL, _(u'add video url')),
        (SUBTITLE_REQUEST, _(u'request subtitles')),
        (APPROVE_VERSION, _(u'approve version')),
        (MEMBER_JOINED, _(u'add contributor')),
        (MEMBER_LEFT, _(u'remove contributor')),
        (REJECT_VERSION, _(u'reject version')),
        (REVIEW_VERSION, _(u'review version')),
        (ACCEPT_VERSION, _(u'accept version')),
        (DECLINE_VERSION, _(u'decline version')),
        (DELETE_VIDEO, _(u'delete video')),
        (EDIT_URL, _(u'edit url')),
        (DELETE_URL, _(u'delete url')),
    )
    TYPES_CATEGORIES = dict(
        videos = [(x[0], x[1]) for x in TYPES if x[0] in
                 [ADD_VIDEO, COMMENT, ADD_VERSION, ADD_VIDEO_URL,
                  APPROVE_VERSION, REJECT_VERSION, ACCEPT_VERSION,
                  DECLINE_VERSION, EDIT_URL,DELETE_URL]],
        team = [(x[0], x[1]) for x in TYPES if x[0] in
                [MEMBER_LEFT, MEMBER_JOINED, DELETE_VIDEO]])
    renderer = ActionRenderer('videos/_action_tpl.html')
    renderer_for_video = ActionRenderer('videos/_action_tpl_video.html')

    user = models.ForeignKey(User, null=True, blank=True)
    video = models.ForeignKey(Video, null=True, blank=True)
    language = models.ForeignKey(SubtitleLanguage, blank=True, null=True)
    new_language = models.ForeignKey('subtitles.SubtitleLanguage', blank=True, null=True)
    team = models.ForeignKey("teams.Team", blank=True, null=True)
    member = models.ForeignKey("teams.TeamMember", blank=True, null=True)
    comment = models.ForeignKey(Comment, blank=True, null=True)
    action_type = models.IntegerField(choices=TYPES)
    # we also store the video's title for deleted videos
    new_video_title = models.CharField(max_length=2048, blank=True)
    created = models.DateTimeField(db_index=True)

    objects = ActionManager()

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'

    def __unicode__(self):
        u = self.user and self.user.__unicode__() or 'Anonymous'
        return u'%s: %s(%s)' % (u, self.get_action_type_display(), self.created)

    def render(self, renderer=None):
        if not renderer:
            renderer = self.renderer

        return renderer.render(self)

    def render_for_video(self):
        return self.render(self.renderer_for_video)

    def is_add_video_url(self):
        return self.action_type == self.ADD_VIDEO_URL

    def is_add_version(self):
        return self.action_type == self.ADD_VERSION

    def is_member_joined(self):
        return self.action_type == self.MEMBER_JOINED

    def is_comment(self):
        return self.action_type == self.COMMENT

    def is_change_title(self):
        return self.action_type == self.CHANGE_TITLE

    def is_add_video(self):
        return self.action_type == self.ADD_VIDEO

    def type(self):
        if self.comment_id:
            return 'commented'
        return 'edited'

    def time(self):
        if self.created.date() == date.today():
            format = 'g:i A'
        else:
            format = 'g:i A, j M Y'
        return date_format(self.created, format)

    def uprofile(self):
        try:
            return self.user.profile_set.all()[0]
        except IndexError:
            pass

    @classmethod
    def create_member_left_handler(cls, team, user):
        action = cls(team=team, user=user)
        action.created = datetime.now()
        action.action_type = cls.MEMBER_LEFT
        action.save()

    @classmethod
    def create_new_member_handler(cls, member):
        action = cls(team=member.team, user=member.user)
        action.created = datetime.now()
        action.action_type = cls.MEMBER_JOINED
        action.member = member
        action.save()

    @classmethod
    def change_title_handler(cls, video, user):
        action = cls(new_video_title=video.title, video=video)
        action.user = user.is_authenticated() and user or None
        action.created = datetime.now()
        action.action_type = cls.CHANGE_TITLE
        action.save()

    @classmethod
    def create_comment_handler(cls, sender, instance, created, **kwargs):
        if created:
            from subtitles.models import SubtitleLanguage as NewSubtitleLanguage
            model_class = instance.content_type.model_class()
            obj = cls(user=instance.user)
            obj.comment = instance
            obj.created = instance.submit_date
            obj.action_type = cls.COMMENT
            if issubclass(model_class, Video):
                obj.video_id = instance.object_pk
            if issubclass(model_class, NewSubtitleLanguage):
                obj.new_language_id = instance.object_pk
                obj.video = instance.content_object.video
            obj.save()

    @classmethod
    def create_caption_handler(cls, instance, timestamp):
        user = instance.author
        video = instance.video
        language = instance.subtitle_language

        obj = cls(user=user, video=video, new_language=language)

        if instance.version_number == 0:
            obj.action_type = cls.ADD_TRANSLATION
        else:
            obj.action_type = cls.ADD_VERSION

        obj.created = timestamp
        obj.save()

    @classmethod
    def create_video_handler(cls, video, user=None):
        obj = cls(video=video)
        obj.action_type = cls.ADD_VIDEO
        obj.user = user
        obj.created = video.created or datetime.now()
        obj.save()

    @classmethod
    def delete_video_handler(cls, video, team, user=None):
        action = cls(team=team)
        action.new_video_title = video.title_display()
        action.action_type = cls.DELETE_VIDEO
        action.user = user
        action.created = datetime.now()
        action.save()

    @classmethod
    def create_video_url_handler(cls, video, video_url):
        cls.objects.create(
            action_type=cls.ADD_VIDEO_URL,
            video=video,
            user=video_url.added_by,
            created=video_url.created,
        )

    @classmethod
    def create_approved_video_handler(cls, version, moderator,  **kwargs):
        obj = cls(video=version.video)
        obj.new_language = version.subtitle_language
        obj.user = moderator
        obj.action_type = cls.APPROVE_VERSION
        obj.created = kwargs.get('datetime_started' , datetime.now())
        obj.save()

    @classmethod
    def create_rejected_video_handler(cls, version, moderator,  **kwargs):
        obj = cls(video=version.video)
        obj.new_language = version.subtitle_language
        obj.user = moderator
        obj.action_type = cls.REJECT_VERSION
        obj.created = datetime.now()
        obj.save()

    @classmethod
    def create_reviewed_video_handler(cls, version, moderator,  **kwargs):
        obj = cls(video=version.video)
        obj.new_language = version.language
        obj.user = moderator
        obj.action_type = cls.REVIEW_VERSION
        obj.created = datetime.now()
        obj.save()

    @classmethod
    def create_accepted_video_handler(cls, version, moderator,  **kwargs):
        obj = cls(video=version.video)
        obj.new_language = version.subtitle_language
        obj.user = moderator
        obj.action_type = cls.ACCEPT_VERSION
        obj.created = datetime.now()
        obj.save()

    @classmethod
    def create_declined_video_handler(cls, version, moderator,  **kwargs):
        obj = cls(video=version.video)
        obj.new_language = version.subtitle_language
        obj.user = moderator
        obj.action_type = cls.DECLINE_VERSION
        obj.created = datetime.now()
        obj.save()


    @classmethod
    def create_subrequest_handler(cls, sender, instance, created, **kwargs):
        if created:
            obj = cls.objects.create(
                user=instance.user,
                video=instance.video,
                action_type=cls.SUBTITLE_REQUEST,
                created=datetime.now()
            )

            instance.action = obj
            instance.save()

class VideoUrlManager(models.Manager):
    def get_queryset(self):
        return VideoUrlQuerySet(self.model, using=self._db)

class VideoUrlQuerySet(query.QuerySet):
    def get(self, **kwargs):
        if 'url' in kwargs:
            url = url_escape(kwargs.pop('url'))
            kwargs['url_hash'] = url_hash(url)
        return super(VideoUrlQuerySet, self).get(**kwargs)

    def filter(self, **kwargs):
        if 'url' in kwargs:
            url = url_escape(kwargs.pop('url'))
            kwargs['url_hash'] = url_hash(url)
        return super(VideoUrlQuerySet, self).filter(**kwargs)

# VideoUrl
class VideoUrl(models.Model):
    video = models.ForeignKey(Video)
    # Type is a character code that specifies the video type.  Types defined
    # in the videos app are 1 char long.  Other apps can create their own
    # types and register them with the video_type_registrar.  In that case the
    # type should be 2 chars long with the first char being unique for the
    # app.
    type = models.CharField(max_length=2)
    url = models.URLField(max_length=URL_MAX_LENGTH)
    url_hash = models.CharField(max_length=32)
    videoid = models.CharField(max_length=50, blank=True)
    primary = models.BooleanField(default=False)
    original = models.BooleanField(default=False)
    created = models.DateTimeField()
    added_by = models.ForeignKey(User, null=True, blank=True)
    # this is the owner if the video is from a third party website
    # shuch as Youtube or Vimeo username
    owner_username = models.CharField(max_length=255, blank=True, null=True)
    # Team.id value copied from TeamVideo.team.  It's only here because we
    # need to use it in our unique constraint.
    #
    # We use an IntegerField instead of a ForeignKey because this makes the
    # unique constraint work properly with non-team videos.  If it was a NULL
    # valued ForeignKey, then mysql would not enforce the constraint.  So
    # instead, we use an IntegerField set equal to 0.
    team_id = models.IntegerField(blank=True, default=0)

    objects = VideoUrlManager()

    class Meta:
        ordering = ("video", "-primary",)
        unique_together = ("url_hash", "team_id", "type")

    def __unicode__(self):
        return self.url

    def is_html5(self):
        return self.type == VIDEO_TYPE_HTML5

    def is_youtube(self):
        return self.type == VIDEO_TYPE_YOUTUBE

    def get_type_display(self):
        for (type_, label) in video_type_choices():
            if self.type == type_:
                return label
        return _('Unknown video type')

    @models.permalink
    def get_absolute_url(self):
        return ('videos:video_url', [self.video.video_id, self.pk])

    def unique_error_message(self, model_class, unique_check):
        if unique_check[0] == 'url':
            vu_obj = VideoUrl.objects.get(url=self.url)
            return mark_safe(fmt(
                _('This URL already <a href="%(url)s">exists</a> as its own video in our system. You can\'t add it as a secondary URL.'),
                url=vu_obj.get_absolute_url()))
        return super(VideoUrl, self).unique_error_message(model_class, unique_check)

    def created_as_time(self):
        #for sorting in js
        return time.mktime(self.created.timetuple())

    def make_primary(self, user=None):
        # create activity item
        old_url = self.video.get_primary_videourl_obj()
        # reset existing urls to non-primary
        VideoUrl.objects.filter(video=self.video).exclude(pk=self.pk).update(
            primary=False)
        # set this one to primary
        self.primary = True
        self.save(updates_timestamp=False)
        signals.video_url_made_primary.send(sender=self, old_url=old_url,
                                            user=user)

    def remove(self, user):
        """Remove this URL from our video.

        This method deletes the URL object and stores a DELETE_URL action to
        log the change.

        Args:
            user: user removing the URL

        Raises:
            IntegrityError: called when the primary URL is deleted
        """

        if self.primary:
            msg = ugettext("Can't remove the primary video URL")
            raise IntegrityError(msg)

        signals.video_url_deleted.send(sender=self, user=user)
        self.delete()

    def get_video_type_class(self):
        try:
            return video_type_registrar[self.type]
        except KeyError:
            vt = video_type_registrar.video_type_for_url(self.url)
            self.type = vt.abbreviation
            self.save()
            return tv

    def get_video_type(self):
        if hasattr(self, '_video_type'):
            return self._video_type
        vt_class = self.get_video_type_class()
        self._video_type = vt_class(self.url)
        return self._video_type

    def kaltura_id(self):
        if self.type == 'K':
            return self.get_video_type().kaltura_id()
        else:
            return None

    def save(self, updates_timestamp=True, *args, **kwargs):
        assert self.type != '', "Can't set an empty type"
        if updates_timestamp:
            self.created = datetime.now()
        self.url = url_escape(self.url)
        self.url_hash = url_hash(self.url)
        super(VideoUrl, self).save(*args, **kwargs)

def video_url_remove_handler(sender, instance, **kwargs):
    print('Invalidating cache')
    video_cache.invalidate_cache(instance.video.video_id)


models.signals.pre_save.connect(create_video_id, sender=Video)
models.signals.pre_delete.connect(video_delete_handler, sender=Video)
pre_delete.connect(video_cache.on_video_url_delete, VideoUrl)


# VideoFeed
class VideoFeed(models.Model):
    url = models.URLField()
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, blank=True, null=True)
    team = models.ForeignKey("teams.Team", blank=True, null=True)
    last_update = models.DateTimeField(null=True)

    YOUTUBE_PAGE_SIZE = 25

    def __unicode__(self):
        return self.url

    @staticmethod
    def now():
        return datetime.now()

    def domain(self):
        return urlparse.urlparse(self.url).netloc

    def update(self):
        importer = VideoImporter(self.url, self.user, self.team)
        new_videos = importer.import_videos(
            import_next=self.last_update is None)

        self.last_update = VideoFeed.now()
        self.save()
        # create videos last-to-first so that the latest video is at the top
        # of the list when viewing the imported videos
        for video in reversed(new_videos):
            ImportedVideo.objects.create(feed=self, video=video)
        signals.feed_imported.send(sender=self, new_videos=new_videos)
        return new_videos

    def count_imported_videos(self):
        return self.importedvideo_set.count()

class ImportedVideo(models.Model):
    feed = models.ForeignKey(VideoFeed)
    video = models.OneToOneField(Video)

    class Meta:
        ordering = ('-id',)

class VideoTypeUrlPatternManager(models.Manager):
    def patterns_for_type(self, type):
        cache_key = 'videotypepattern:{0}'.format(type)
        patterns = cache.get(cache_key)
        if patterns is None:
            patterns = self.filter(type=type)
            cache.set(cache_key, patterns)
        return patterns

class VideoTypeUrlPattern(models.Model):
    type = models.CharField(max_length=2)
    url_pattern = models.URLField(max_length=255, unique=True)
    objects = VideoTypeUrlPatternManager()
