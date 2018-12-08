# -*- coding: utf-8 -*-
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

"""Django models represention subtitles."""

import collections
import itertools
import json
import logging
from datetime import datetime, date, timedelta


from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.db import models, IntegrityError
from django.db.models import query, Q, Count
from django.utils.functional import cached_property
from django.utils.translation import ugettext
from django.utils.translation import ugettext_lazy as _

from subtitles import cache
from subtitles import shims
from auth.models import CustomUser as User
from videos import metadata
from videos.models import Video
import videos.tasks
from babelsubs.storage import SubtitleSet
from babelsubs.storage import calc_changes
from babelsubs.generators.html import HTMLGenerator
from babelsubs import load_from
from subtitles import signals
from utils import dates
from utils.compress import compress, decompress
from utils.subtitles import create_new_subtitles
from utils.text import fmt
from utils import translation

WRITELOCK_EXPIRATION = 30 # 30 seconds
DEFAULT_SOFT_LIMIT_LINES = 2
DEFAULT_SOFT_LIMIT_CPL = 42
DEFAULT_SOFT_LIMIT_CPS = 21
DEFAULT_SOFT_LIMIT_MIN_DURATION = 700
DEFAULT_SOFT_LIMIT_MAX_DURATION = 7000

logger = logging.getLogger(__name__)



# Utility functions -----------------------------------------------------------
def mapcat(fn, iterable):
    """Mapcatenate.

    Map the given function over the given iterable.  Each mapping should result
    in an interable itself.  Concatenate these results.

    E.g.:

        foo = lambda i: [i, i+1]
        mapcatenate(foo, [20, 200, 2000])
        [20, 21, 200, 201, 2000, 2001]

    """
    return itertools.chain.from_iterable(itertools.imap(fn, iterable))

def ensure_stringy(val):
    """Ensure the given value is a stringy type, like str or unicode.

    If not, a ValidationError will be raised.

    This method is necessary because Django will often do the wrong thing when
    you pass a non-stringy object to a CharField (it will str() the object which
    probably isn't what you want).

    """
    if val == None:
        return

    if not isinstance(val, basestring):
        raise ValidationError('Value must be a string.')

def graphviz(video):
    """Return the dot code for a Graphviz visualization of a video's history."""

    lines = []

    lines.append("digraph video_%s {" % video.video_id)
    lines.append("rankdir = BT;")

    def _name(sv):
        return '%s%d' % (sv.language_code, sv.version_number)

    for sl in video.newsubtitlelanguage_set.all():
        for sv in sl.subtitleversion_set.full():
            lines.append('%s[label="%s"];' % (_name(sv), _name(sv)))

    for sl in video.newsubtitlelanguage_set.all():
        for sv in sl.subtitleversion_set.full():
            for pv in sv.parents.full():
                lines.append("%s -> %s;" % (_name(pv), _name(sv)))

    lines.append("}")

    return lines

def print_graphviz(video_id):
    video = Video.objects.get(video_id=video_id)
    print '\n'.join(graphviz(video))


# Lineage functions -----------------------------------------------------------
def lineage_to_json(lineage):
    return json.dumps(lineage)

def json_to_lineage(json_lineage):
    return json.loads(json_lineage)

def get_lineage(parents):
    """Return a lineage map for a version that has the given parents."""
    lineage = {}

    # The new version's lineage should be the result of merging the parents'
    # lineages, taking the later version whenever there's a conflict, and adding
    # the parent versions themselves to the map.
    for parent in parents:
        l, v = parent.language_code, parent.version_number

        if l not in lineage or lineage[l] < v:
            lineage[l] = v

        for l, v in parent.lineage.items():
            if l not in lineage or lineage[l] < v:
                lineage[l] = v

    return lineage

# SubtitleLanguages -----------------------------------------------------------
class SubtitleLanguagageQuerySet(query.QuerySet):
    def fetch_and_join(self, public_tips=False, private_tips=False,
                       video=None):
        """Fetch languages and join them to related models.

        This method is an efficient way to fetch languages under a couple
        circumstances:
            - You know the video for the language
            - You know that you will fetch the tip versions for the language

        fetch_and_join() fetches all tips using 1 query, where usually you
        would issue a query per language.

        :param public_tips: set the public tip cache for fetched languages
        :param private_tips: set the private tip cache for fetched languages
        :param video: set the cached video for all languages/versions fetched
        :returns: list of SubtitleLanguage objects
        """
        langs = list(self)
        if video is not None:
            for lang in langs:
                lang.video = video

        def join_tips(base_qs, cache_name):
            qs = base_qs.filter(subtitle_language__in=langs)
            version_map = dict((v.subtitle_language_id, v) for v in qs)
            for lang in langs:
                version = version_map.get(lang.id)
                lang.set_tip_cache(cache_name, version)
                if version is not None:
                    lang.optimize_loaded_version(version)

        if public_tips:
            join_tips(SubtitleVersion.objects.public_tips(), 'public')
        if private_tips:
            join_tips(SubtitleVersion.objects.private_tips(), 'extant')

        return langs

    #  _   _                ______       ______
    # | | | |               | ___ \      |  _  \
    # | |_| | ___ _ __ ___  | |_/ / ___  | | | |_ __ __ _  __ _  ___  _ __  ___
    # |  _  |/ _ \ '__/ _ \ | ___ \/ _ \ | | | | '__/ _` |/ _` |/ _ \| '_ \/ __|
    # | | | |  __/ | |  __/ | |_/ /  __/ | |/ /| | | (_| | (_| | (_) | | | \__ \
    # \_| |_/\___|_|  \___| \____/ \___| |___/ |_|  \__,_|\__, |\___/|_| |_|___/
    #                                                      __/ |
    #                                                     |___/
    #
    # These methods use custom SQL to try to speed up queries to avoid
    # denormalizing the data model.
    #
    # These methods are not fun, and they are not pretty, but they ARE fast.
    #
    # Prepare yourself.
    def having_versions(self):
        """Return a QS of SLs that have at least 1 version.

        TODO: See if we need to denormalize this into a field.  I don't think we
        will (and would strongly prefer not to (see the has_version/had_version
        mess we were in before)).

        """
        return self.extra(where=[
            """
            EXISTS (
                SELECT 1
                  FROM subtitles_subtitleversion AS sv
                 WHERE sv.subtitle_language_id = subtitles_subtitlelanguage.id
               AND NOT sv.visibility_override = 'deleted'
            )
            """,
        ])

    def not_having_versions(self):
        """Return a QS of SLs that have zero versions.

        TODO: See if we need to denormalize this into a field.  I don't think we
        will (and would strongly prefer not to (see the has_version/had_version
        mess we were in before)).

        """
        return self.extra(where=[
            """
            NOT EXISTS (
                SELECT 1
                  FROM subtitles_subtitleversion AS sv
                 WHERE sv.subtitle_language_id = subtitles_subtitlelanguage.id
               AND NOT sv.visibility_override = 'deleted'
            )
            """,
        ])


    def having_nonempty_versions(self):
        """Return a QS of SLs that have at least 1 version with 1 or more subtitles."""
        return self.extra(where=[
            """
            EXISTS
            (SELECT 1
               FROM subtitles_subtitleversion AS sv
              WHERE sv.subtitle_language_id = subtitles_subtitlelanguage.id
            AND NOT sv.visibility_override = 'deleted'
                AND sv.subtitle_count > 0)
            """,
        ])

    def not_having_nonempty_versions(self):
        """Return a QS of SLs that have zero versions with 1 or more subtitles."""
        return self.extra(where=[
            """
            NOT EXISTS
            (SELECT 1
               FROM subtitles_subtitleversion AS sv
              WHERE sv.subtitle_language_id = subtitles_subtitlelanguage.id
            AND NOT sv.visibility_override = 'deleted'
                AND sv.subtitle_count > 0)
            """,
        ])


    def having_nonempty_tip(self):
        """Return a QS of SLs that have a tip version with 1 or more subtitles."""
        return self.extra(where=[
            """
            EXISTS (
                SELECT 1
                FROM subtitles_subtitleversion AS sv
                WHERE sv.version_number = (
                    SELECT MAX(sv2.version_number)
                    FROM subtitles_subtitleversion sv2
                    WHERE sv2.subtitle_language_id=subtitles_subtitlelanguage.id
                    AND sv2.visibility_override != 'deleted'
                )
                AND sv.subtitle_count > 0
                AND sv.subtitle_language_id=subtitles_subtitlelanguage.id
            )
            """,
        ])

    def not_having_nonempty_tip(self):
        """Return a QS of SLs that do not have a tip version with 1 or more subtitles."""
        return self.extra(where=[
            """
            NOT EXISTS (
                SELECT 1
                FROM subtitles_subtitleversion AS sv
                WHERE sv.version_number = (
                    SELECT MAX(sv2.version_number)
                    FROM subtitles_subtitleversion sv2
                    WHERE sv2.subtitle_language_id=subtitles_subtitlelanguage.id
                    AND sv2.visibility_override != 'deleted'
                )
                AND sv.subtitle_count > 0
                AND sv.subtitle_language_id=subtitles_subtitlelanguage.id
            )
            """,
        ])


    def having_public_versions(self):
        """Return a QS of SLs that have at least 1 publicly-visible versions.

        TODO: See if we need to denormalize this into a field.  I don't think we
        will (and would strongly prefer not to (see the has_version/had_version
        mess we were in before)).

        """
        return self.extra(where=[
            """
            EXISTS (
                SELECT 1
                  FROM subtitles_subtitleversion AS sv
                 WHERE sv.subtitle_language_id = subtitles_subtitlelanguage.id
               AND NOT sv.visibility_override = 'deleted'
               AND NOT sv.visibility_override = 'private'
               AND NOT (sv.visibility = 'private' AND sv.visibility_override = '')
            )
            """,
        ])

    def not_having_public_versions(self):
        """Return a QS of SLs that have zero publicly-visible versions.

        TODO: See if we need to denormalize this into a field.  I don't think we
        will (and would strongly prefer not to (see the has_version/had_version
        mess we were in before)).

        """
        return self.extra(where=[
            """
            NOT EXISTS (
                SELECT 1
                  FROM subtitles_subtitleversion AS sv
                 WHERE sv.subtitle_language_id = subtitles_subtitlelanguage.id
               AND NOT sv.visibility_override = 'deleted'
               AND NOT sv.visibility_override = 'private'
               AND NOT (sv.visibility = 'private' AND sv.visibility_override = '')
            )
            """,
        ])

    def video_count(self):
        qs = self.extra(select={
            'video_count': 'count(distinct(video_id))',
        })
        return qs.values_list('video_count', flat=True)[0]

class SubtitleLanguage(models.Model):
    """SubtitleLanguages are the equivalent of a 'branch' in a VCS.

    These exist mostly to coordiante access to a language amongst users.  Most
    of the actual data for the subtitles is stored in the version themselves.

    """
    # Basic Data
    video = models.ForeignKey(Video, related_name='newsubtitlelanguage_set')
    language_code = models.CharField(max_length=16,
                                     choices=translation.ALL_LANGUAGE_CHOICES)
    created = models.DateTimeField(editable=False)

    # Should be True if the latest version for this set of subtitles covers all
    # of the video, False otherwise.  This is set and handled entirely
    # independently of versions though.
    subtitles_complete = models.BooleanField(default=False)

    # This field is a temporary shim until we move to the new user interface.
    # A "forked" language is one that was originally a translation but has since
    # been changed to be a standalone language.
    is_forked = models.BooleanField(default=False)

    soft_limit_lines = models.IntegerField(null=True, blank=True, default=None)
    soft_limit_min_duration = models.IntegerField(null=True, blank=True, default=None)
    soft_limit_max_duration = models.IntegerField(null=True, blank=True, default=None)
    soft_limit_cps = models.IntegerField(null=True, blank=True, default=None)
    soft_limit_cpl = models.IntegerField(null=True, blank=True, default=None)

    # Writelocking
    writelock_time = models.DateTimeField(null=True, blank=True,
                                          editable=False)
    writelock_owner = models.ForeignKey(User, null=True, blank=True,
                                        editable=False,
                                        related_name='writelocked_newlanguages')
    writelock_session_key = models.CharField(max_length=255, blank=True,
                                             editable=False)

    followers = models.ManyToManyField(User, blank=True,
            related_name='new_followed_languages', editable=False)

    # Manager
    objects = SubtitleLanguagageQuerySet.as_manager()

    class Meta:
        unique_together = [('video', 'language_code')]
        permissions = (
            ('access_restricted_subtitle_format', "Can access restricted subtitle format"),
            )

    @classmethod
    def calc_completed_languages(cls, video_list, prioritize=None, names=False):
        """Calculate completed languages for a list of videos.

        Arguments:
            video_list: list of Videos or PKs
            prioritize: list of languages to put at the top of the list
            names: return language names instead of codes

        Returns:
            dict mapping video PKs to a list of language codes
        """
        qs = (cls.objects
              .filter(subtitles_complete=True, video_id__in=video_list)
              .values_list('video_id', 'language_code'))
        completed_languages = collections.defaultdict(list)
        for video_id, language in qs:
            completed_languages[video_id].append(language)
        if prioritize:
            for language_list in completed_languages.values():
                list_size = len(language_list)
                language_list.sort(
                    key=(lambda lc: prioritize.index(lc) if lc in prioritize
                         else list_size))
        if names:
            for language_list in completed_languages.values():
                language_list[:] = [
                    translation.get_language_label(lc)
                    for lc in language_list
                ]
        return completed_languages

    def __init__(self, *args, **kwargs):
        super(SubtitleLanguage, self).__init__(*args, **kwargs)
        self._tip_cache = {}
        self._translation_source_version_cache = {}
        self._frozen = False

    def get_soft_limits(self):
        """
        Get soft limits for the editor.

        These are things like characters per second (CPS) where we display
        warnings if the user exceeds them
        """
        return {
            'lines': (self.soft_limit_lines or
                      DEFAULT_SOFT_LIMIT_LINES),
            'cpl': (self.soft_limit_cpl or
                    DEFAULT_SOFT_LIMIT_CPL),
            'cps': (self.soft_limit_cps or
                    DEFAULT_SOFT_LIMIT_CPS),
            'min_duration': (self.soft_limit_min_duration or
                             DEFAULT_SOFT_LIMIT_MIN_DURATION),
            'max_duration': (self.soft_limit_max_duration or
                             DEFAULT_SOFT_LIMIT_MAX_DURATION),
        }

    # Writelocking
    @property
    def is_writelocked(self):
        """Return whether this language is writelocked for subtitling."""
        if self.writelock_time == None:
            return False
        delta = datetime.now() - self.writelock_time
        seconds = delta.days * 24 * 60 * 60 + delta.seconds
        return seconds < WRITELOCK_EXPIRATION

    def can_writelock(self, user):
        """Return whether a user with the session key can writelock this language."""
        return self.writelock_owner == user or not self.is_writelocked

    def writelock(self, user, save=True):
        """Writelock this language for subtitling and save it.

        This method does NO permission checking.  If you want that you'll need
        to use can_writelock() yourself before calling this (probably in
        a transaction).

        `user` is the User who should own the lock.

        `save` determines whether this method will save the SubtitleLanguage for
        you.  Pass False if you want to handle saving yourself.

        """
        if user.is_authenticated():
            self.writelock_owner = user
        else:
            self.writelock_owner = None

        self.writelock_time = datetime.now()

        if save:
            self.save()

    def release_writelock(self, save=True):
        """Writelock this language for subtitling and save it.

        `save` determines whether this method will save the SubtitleLanguage
        for you.  Pass False if you want to handle saving yourself.

        """
        self.writelock_owner = None
        self.writelock_time = None

        if save:
            self.save()

    def get_writelock_owner_name(self):
        """Return the human-readable name of the owner of this language's writelock.

        This assumes that the language actually IS writelocked.  If that's not
        the case this method will return nonsensical data, so you'll need to
        check that first.

        """
        if self.writelock_owner == None:
            return "anonymous"
        else:
            return self.writelock_owner.__unicode__()

    def freeze(self):
        """Suspend sending signals until thaw() is called

        This controls the subtitles_completed and subtitles_added signals.  We
        probably should fold in subtitles_published at some point too.
        """
        if self._frozen:
            return
        self._frozen = True
        self._frozen_signals = {}

    def send_signal(self, signal, **kwargs):
        if not self._frozen:
            signal.send(self, **kwargs)
        else:
            self._frozen_signals[signal] = kwargs

    def thaw(self):
        """Start sending signals again after a call to freeze()"""
        if not self._frozen:
            return
        thawed = self._frozen_signals
        del self._frozen_signals
        self._frozen = False
        for signal, kwargs in thawed.items():
            signal.send(self, **kwargs)

    def mark_complete(self):
        if not self.subtitles_complete:
            self.subtitles_complete = True
            self.save()
        self.send_signal(signals.subtitles_completed)

    def mark_incomplete(self):
        if not self.subtitles_complete:
            return
        self.subtitles_complete = False
        self.save()

    def is_rtl(self):
        return translation.is_rtl(self.language_code)

    def dir(self):
        if self.is_rtl():
            return 'rtl'
        else:
            return 'ltr'

    def __unicode__(self):
        return 'SubtitleLanguage %s / %s / %s' % (
            (self.id or '(unsaved)'), self.video.video_id,
            self.get_language_code_display()
        )

    def save(self, *args, **kwargs):
        if not self.language_code in translation.ALL_LANGUAGE_CODES:
            raise ValidationError(
                "Subtitle Language %s should be a valid code." %
                self.language_code)

        creating = not self.pk

        if creating and not self.created:
            self.created = dates.now()

        super(SubtitleLanguage, self).save(*args, **kwargs)

    def change_language_code(self, language_code):
        # change current language_code
        old_language_code = self.language_code
        try:
            self.language_code = language_code
            self.save()
        except ValidationError as e:
            # raised if an invalid language code is provided
            self.language_code = old_language_code
            logger.error(e, exc_info=True)
            raise e
        except IntegrityError as e:
            self.language_code = old_language_code
            logger.error("Subtitle already exists for this language")
            raise e

        # get all subtitle versions and change their language_codes
        for version in self.get_versions(full=True):
            try:
                version.language_code = language_code
                version.save()
            except AssertionError as e:
                logger.error(e)
                raise e

        # change collab language codes
        self.send_signal(signals.subtitle_language_changed, old_language=old_language_code)

        cache.invalidate_language_cache(self)
        self.clear_tip_cache()
        videos.tasks.video_changed_tasks(self.video.id)

    def title_display(self):
        tip = self.get_tip()
        if tip is not None:
            return tip.title_display()
        else:
            return self.video.title

    def get_tip(self, public=False, full=False):
        """Return the tipmost version of this language (if any).

        If public is given, returns the tipmost version that is visible to the
        general public (if any).

        If full is given, select from ALL versions (public, private, AND
        deleted).  Giving both public and full will result in an error.

        """
        if public and full:
            assert False, "Cannot specify public and full in get_tip()!"

        if public:
            cache_name = 'public'
        elif full:
            cache_name = 'full'
        else:
            cache_name = 'extant'
        if cache_name in self._tip_cache:
            return self._tip_cache[cache_name]

        # cache name is conveniently the same as the SubtitleVersionManager
        # attribute name.
        versions = getattr(SubtitleVersion.objects, cache_name)()
        versions = versions.filter(subtitle_language=self)
        versions = versions.order_by('-version_number')
        versions = versions[:1]

        if versions:
            tip = versions[0]
            self.optimize_loaded_version(tip)
        else:
            tip = None

        self.set_tip_cache(cache_name, tip)
        return tip

    def set_tip_cache(self, cache_name, version):
        """Set the tip cache for this language

        Subsequent calls to get_tip() will used the cached version instead of
        fetching a new one from the DB.

        :param cache_name: one of ('public', 'extant', or 'full')
        :param version: SubtitleVersion object
        """
        self._tip_cache[cache_name] = version

    def _version_qs(self, public, full):
        if public and full:
            raise AssertionError("Cannot specify public and full in "
                                 "get_versions()!")
        if public:
            return self.subtitleversion_set.public()
        elif full:
            return self.subtitleversion_set.full()
        else:
            return self.subtitleversion_set.extant()

    def has_version(self, public=False, full=False):
        return self.get_tip(public, full) is not None

    def get_versions(self, public=False, full=False, newest_first=False):
        """Get a list of versions for this subtitle language

        :param public: if True only return versions visible to the public
        :param full: if True only return deleted versions
        :param newest_first: controls ordering of the versions
        :returns: list of SubtitleVersion objects
        """
        qs = self._version_qs(public, full)
        if newest_first:
            qs = qs.order_by('-version_number')
        else:
            qs = qs.order_by('version_number')
        versions = [self.optimize_loaded_version(v) for v in qs]
        if not public:
            self._set_previous_version_cache(versions, full)
        return versions

    def optimize_versions(self, versions):
        """Do performance speedups for versions of this language

        This method sets up the cache for various attributes of the versions,
        like video/language.

        :returns: list of optimized verions
        """
        return [self.optimize_loaded_version(v) for v in versions]

    def get_version_by_id(self, version_pk, public=False, full=False):
        """Get a version for this subtitle_language

        :returns: SubtitleVersion
        """
        qs = self._version_qs(public, full)
        return self.optimize_loaded_version(qs.get(pk=version_pk))

    def _set_previous_version_cache(self, versions, full):
        previous_version = None
        for v in versions:
            v.cache_previous_version(previous_version, full)
            previous_version = v

    def optimize_loaded_version(self, version):
        """Optimize a verison loaded for this language

        This method caches version.language attribute to be this object.
        Also, if this object has a cached video, then it sets the version's
        cached video as well.
        """
        video_cache_name = SubtitleLanguage.video.cache_name
        if hasattr(self, video_cache_name):
            version.video = getattr(self, video_cache_name)
        version.subtitle_language = self
        return version

    def get_public_tip(self):
        """Return the latest public tip for a particular version.

        This is currently being used on the search templates for videos, since
        we can't specify parameters when calling get_tip + we don't have
        template tags (afaik).

        TODO: see if we can remove this somehow.

        """
        return self.get_tip(public=True)

    def clear_tip_cache(self):
        self._tip_cache = {}

    def first_public_version(self):
        """Returns the very fist version to be made public of none"""
        try:
            return self.subtitleversion_set.public().order_by("version_number")[0]
        except IndexError:
            return None

    def has_public_version(self):
        """Check if there are any public versions for this language."""
        if hasattr(self, '_has_public_version'):
            return self._has_public_version
        return self.get_tip(public=True) is not None

    @classmethod
    def bulk_has_public_version(self, languages):
        """Check for public verisons in a list of languages

        This method will do a single query to check for all languages.
        Afterwards, calling has_public_version() won't require any DB work.
        """
        sql = """\
EXISTS(
    SELECT * FROM subtitles_subtitleversion sv
    WHERE sv.subtitle_language_id = subtitles_subtitlelanguage.id
        AND (sv.visibility_override='public'
            OR (sv.visibility_override = '' AND sv.visibility='public')))"""

        qs = (SubtitleLanguage.objects
              .filter(id__in=[l.id for l in languages])
              .extra(where=[sql])
              .values_list('id', flat=True))
        with_public_versions = set(qs)
        for l in languages:
            l._has_public_version = l.id in with_public_versions

    def is_complete_and_synced(self, public=False):
        """Return whether this language's subtitles are complete and fully synced."""

        if not self.subtitles_complete:
            return False

        version = self.get_tip(public)

        if not version:
            return False

        subtitles = version.get_subtitles()

        return subtitles.fully_synced

    def _sanity_check_parents(self, version, parents):
        r"""Check that the given parents are sane for an SV about to be created.

        There are a few rules checked here.

        First, versions cannot have more than one parent from a single language.
        For example, the following is invalid:

            en fr

            1
            |\
            \ \
             \ 2
              \|
               1

        Second, a parent cannot have a parent that precedes something existing
        in its own lineage.  It's easiest to understand this with an example.
        The following is invalid:

            en fr
            3
            |\
            2 \
            |  \
            1   \
             \   |
              \  |
               2 |
               |/
               1

        This is invalid because English was based off of French version 2, and
        then you tried to say a later version was based on French version 1.

        If English version 3 had been based on French version 2 (or later) that
        would be have been okay.

        """

        # There can be at most one parent from any given language.
        if len(parents) != len(set([v.language_code for v in parents])):
            raise ValidationError(
                "Versions cannot have two parents from the same language!")

        for parent in parents:
            if parent.language_code in version.lineage:
                if parent.version_number < version.lineage[parent.language_code]:
                    raise ValidationError(
                        "Versions cannot have parents that precede parents in "
                        "their lineage!")


    def add_version(self, *args, **kwargs):
        """Add a SubtitleVersion to the tip of this language.

        You probably don't need this.  You probably want
        apps.subtitles.pipeline.add_subtitles instead.

        Does not check any writelocking -- that's up to the pipeline.

        """
        kwargs['subtitle_language'] = self
        kwargs['language_code'] = self.language_code
        kwargs['video'] = self.video

        tip = self.get_tip(full=True)

        version_number = ((tip.version_number + 1) if tip else 1)
        kwargs['version_number'] = version_number

        parents = (kwargs.pop('parents', None) or [])

        if tip:
            parents.append(tip)

        kwargs['lineage'] = get_lineage(parents)

        ensure_stringy(kwargs.get('title'))
        ensure_stringy(kwargs.get('description'))
        metadata = kwargs.pop('metadata', None)
        sv = SubtitleVersion(*args, **kwargs)

        sv.set_subtitles(kwargs.get('subtitles', None))
        self._sanity_check_parents(sv, parents)

        sv.full_clean()
        sv.save(metadata=metadata)

        for p in parents:
            sv.parents.add(p)

        cache.invalidate_language_cache(self)
        self.clear_tip_cache()
        self.send_signal(signals.subtitles_added, version=sv)
        return sv

    def get_metadata(self, public=True):
        tip = self.get_tip(public)
        if tip:
            return tip.get_metadata()
        else:
            # no versions yet, take the metadata from our video, but use empty
            # strings for the values
            video_metadata = self.video.get_metadata()
            for key in video_metadata:
                video_metadata[key] = ''
            return video_metadata

    def get_metadata_for_display(self):
        return self.get_metadata().convert_for_display()

    def is_synced(self, public=True):
        value = cache.get_is_synced(self, public)
        if value is None:
            value = self.get_tip(public=public).is_synced()
            cache.set_is_synced(self, public, value)
        return value

    def nuke_language(self):
        """Delete all SubtitleVersions for this language, as well as all
        SubtitleVersions for dependent languages.
        """
        # delete dependent languages first
        languages = [self] + self.get_dependent_subtitle_languages()
        for lang in languages:
            for sv in lang.subtitleversion_set.extant().all():
                sv.unpublish(delete=True, signal=False)
            signals.subtitles_deleted.send(lang)
            from teams.signals import api_language_deleted
            api_language_deleted.send(lang)
        self.subtitles_complete = False
        self.save()
        Video.cache.invalidate_by_pk(self.video_id)

    def update_signoff_counts(self):
        """Update the denormalized signoff count fields and save."""

        cs = self.collaborator_set.all()

        self.official_signoff_count = len(
            [c for c in cs if c.signoff and c.signoff_is_official])

        self.unofficial_signoff_count = len(
            [c for c in cs if c.signoff and (not c.signoff_is_official)])

        self.pending_signoff_count = len(
            [c for c in cs if (not c.signoff)])

        self.pending_signoff_expired_count = len(
            [c for c in cs if (not c.signoff) and c.expired])

        self.pending_signoff_unexpired_count = len(
            [c for c in cs if (not c.signoff) and (not c.expired)])

        self.save()

    def get_description(self, public=True):
        v = self.get_tip(public=public)

        if v:
            return v.description

        return self.video.description

    def get_title(self, public=True):
        v = self.get_tip(public=public)

        if v:
            return v.title

        return self.video.title


    def version_count(self):
        if hasattr(self, '_version_count'):
            return self._version_count
        else:
            self._version_count = self.subtitleversion_set.count()
            return self._version_count

    def get_subtitle_count(self):
        tip = self.get_tip()
        if tip:
            return tip.get_subtitle_count()
        return 0

    def is_primary_audio_language(self):
        return self.video.primary_audio_language_code == self.language_code

    def versions_for_user(self, user):
        workflow = self.video.get_workflow()
        if workflow.user_can_view_private_subtitles(user, self.language_code):
            return self.subtitleversion_set.extant()
        else:
            return self.subtitleversion_set.public()

    def version(self, public_only=True, version_number=None):
        """Return a SubtitleVersion of this language matching the arguments.

        Returns None if no versions match.

        Cannot return deleted versions.  If you need a deleted version you need
        to look it up another way.

        """
        assert self.pk, "Can't find a version for a language that hasn't been saved"

        qs = self.subtitleversion_set
        qs = qs.public() if public_only else qs.extant()

        if version_number != None:
            qs = qs.filter(version_number=version_number)
        else:
            qs = qs.order_by('-version_number')

        try:
            return qs[:1].get()
        except SubtitleVersion.DoesNotExist:
            return None


    def get_translation_source_language_code(self, ignore_forking=False):
        """
        Returns the language code of the language that served as the
        source language for this translation, or None if no languages
        are found on the lineage.

        In some cases, you might want to ignore the is_forked attribute. For
        example, on the new editor, you want to see the language this was
        translated from, even if it was forked. Unless that's your very specific
        use case, just leave `ignore_forking` as False.

        Right now, we're only allowing for 1 source language, but that
        could be revisited in the future.

        """
        source_language = self.get_translation_source_language(
            ignore_forking=ignore_forking
        )
        return source_language.language_code if source_language else None


    def get_translation_source_language(self, ignore_forking=False):
        """
        Returns the new SubtitleLanguage object that served as the
        source language for this translation, or None if no languages
        are found on the lineage.

        Right now, we're only allowing for 1 source language, but that
        could be revisited in the future.

        """
        source_version = self.get_translation_source_version(
            ignore_forking=ignore_forking)

        return source_version.subtitle_language if source_version else None


    def get_translation_source_version(self, ignore_forking=False):
        '''
        Returns the new SubtitleVersion object that served as the
        source for this translation, or None if no versions
        are found on the lineage.

        Right now, we're only allowing for 1 version, but that
        could be revisited in the future.
        '''
        cache_key = ignore_forking
        if cache_key in self._translation_source_version_cache:
            return self._translation_source_version_cache[cache_key]
        version = self._get_translation_source_version(ignore_forking)
        self._translation_source_version_cache[cache_key] = version
        return version

    def clear_translation_source_cache(self):
        self._translation_source_version_cache = {}

    def _get_translation_source_version(self, ignore_forking=False):
        if not ignore_forking and self.is_forked:
            return None

        qs = SubtitleVersion.objects.raw("""\
SELECT parents.*
FROM subtitles_subtitleversion children
JOIN subtitles_subtitleversion_parents pmap
    ON children.id=pmap.from_subtitleversion_id
JOIN subtitles_subtitleversion parents
    ON parents.id=pmap.to_subtitleversion_id
WHERE children.subtitle_language_id=%s AND parents.subtitle_language_id != %s
ORDER BY children.version_number DESC
LIMIT 1;""", (self.id, self.id))
        try:
            return qs[0]
        except IndexError:
            return None

    def get_dependent_subtitle_languages(self, direct=False):
        """Return a list of SLs that are dependents/translations of this.

        If direct is given, only direct dependents will be returned.  Direct
        dependents are languages that were directly translated from this one.
        Indirect dependents have a language in between.  For example:

            en -> fr -> de

            >>> en.get_dsl(direct=False)
            [fr, de]

            >>> en.get_dsl(direct=True)
            [fr]

        Note that this is NOT going to be very performant.

        This is a shim for the existing UI.  Once the new one comes this
        monstrosity will be torn out.

        """
        # Start with all the subtitle languages for the video.
        sls = self.video.newsubtitlelanguage_set

        # Exclude this one.
        sls = sls.exclude(id=self.id)

        # Exclude those that are already forked.  They can't be dependents.
        sls = sls.exclude(is_forked=True)

        # Realize the query to get the list of remaining SubtitleLanguages that
        # could possibly be dependents.  Hopefully there shouldn't be too many.
        sls = list(sls)

        # Check the lineage maps for the candidates to determine if they're
        # dependents.
        results = []
        for sl in sls:
            tip = sl.get_tip()
            if tip and self.language_code in tip.lineage:
                results.append(sl)

        # Direct translations are restricted to those that come directly from
        # the source language (this).
        if direct:
            lc = self.language_code
            results = [sl for sl in results
                       if sl.get_translation_source_language_code() == lc]

        return results


    def fork(self):
        """Fork this language."""

        self.is_forked = True
        self.save()


    def editor_url(self):
        return reverse('subtitles:subtitle-editor', kwargs={
            'video_id': self.video.video_id,
            'language_code': self.language_code,
        })

    @models.permalink
    def get_absolute_url(self):
        return ('videos:translation_history',
                [self.video.video_id, self.language_code or 'unknown', self.pk])

    @property
    def old_has_version(self):
        # FIXME: remove this once we get rid of the RPC code that uses it
        """
        http://amara.readthedocs.org/en/latest/model-refactor.html#id4
        """
        return SubtitleLanguage.objects.having_nonempty_versions().filter(
                video=self.video).exists()

    def user_is_follower(self, user):
        return self.followers.filter(id=user.id).exists()

    def notification_list(self, exclude=None):
        qs = self.followers.filter(notify_by_email=True, is_active=True)

        if exclude:
            if not isinstance(exclude, (list, tuple)):
                exclude = [exclude]
            qs = qs.exclude(pk__in=[u.pk for u in exclude if u])
        return qs

    def in_progress(self):
        """Return whether this SubtitleLanguage is "in progress".

        Moderated teams:

            It's in progress if it has an unapproved draft

        Unmoderated teams:

            It's in progress if it has subs but not marked as complete

        """
        if self.video.is_moderated:
            if self.get_tip().is_private():
                return True
        else:
            if not self.subtitles_complete and \
                    self.get_tip().get_subtitle_count() > 0:
                return True

        return False

    @property
    def is_imported_from_youtube_and_not_worked_on(self):
        versions = self.subtitleversion_set.full()
        if versions.count() > 1 or versions.count() == 0:
            return False

        version = versions[0]

        if version.note == 'From youtube':
            return True

        return False

    @classmethod
    def count_completed_subtitles(cls, videos):
        """Count the completed subtitles for a set of videos

        Returns: dict mapping video.id to (incomplete_count, completed_count)
        """
        qs = (cls.objects.all().filter(video__in=videos)
              .values('video_id', 'subtitles_complete')
              .annotate(count=Count('id')))
        count_map = {
            (d['video_id'], d['subtitles_complete']): d['count']
            for d in qs
        }
        return {
            video.id: (count_map.get((video.id, False), 0),
                       count_map.get((video.id, True), 0))
            for video in videos
        }

# SubtitleVersions ------------------------------------------------------------
class SubtitleVersionQuerySet(query.QuerySet):
    def private_tips(self):
        tip_where = """\
subtitles_subtitleversion.version_number = (
    SELECT MAX(version_number)
    FROM subtitles_subtitleversion sv2
    WHERE sv2.subtitle_language_id =
           subtitles_subtitleversion.subtitle_language_id AND
           sv2.visibility_override != 'deleted')"""
        return self.extra(where=[tip_where])

    def public_tips(self):
        public_tip_where = """\
subtitles_subtitleversion.version_number = (
    SELECT MAX(version_number)
    FROM subtitles_subtitleversion sv2 
    WHERE ((sv2.visibility = 'public' AND sv2.visibility_override = '') OR
           sv2.visibility_override = 'public') AND
           sv2.subtitle_language_id =
           subtitles_subtitleversion.subtitle_language_id)"""
        return self.extra(where=[public_tip_where])

    def subtitle_count(self):
        qs = self.extra(select={
            'subs_total': 'SUM(subtitles_subtitleversion.subtitle_count)'
        }, where=[
            'subtitles_subtitleversion.version_number = ('
            'SELECT MAX(version_number) '
            'FROM subtitles_subtitleversion sv2 '
            'WHERE sv2.subtitle_language_id = '
            'subtitles_subtitleversion.subtitle_language_id)'])
        return qs.values_list('subs_total', flat=True)[0]

class SubtitleVersionManager(models.Manager):
    use_for_related_fields = False

    # ---------------------------- IMPORTANT ----------------------------------
    #
    # Django Managers contain proxy methods to querysets like .filter() and
    # such.  DO NOT USE THEM.  They will bypass the full/extant/public methods
    # that perform the appropriate filtering.
    #
    # So instead of:
    #
    #     sl.subtitleversion_set.filter(...)
    #
    # You should do:
    #
    #     sl.subtitleversion_set.full().filter(...)
    #
    # Normally we'd disable all these proxy methods so we could find all the
    # places where they're used, and it would be safe and break loudly instead
    # of silently doing unsafe things.  Unfortunately Django's Model class uses
    # these proxy methods instead of going through get_queryset(), so we're out
    # of luck.

    # These three methods are your main entry point into SubtitleVersion querysets.
    def full(self):
        """Return a queryset of ALL versions (including deleted ones)."""
        return self.get_queryset()

    def extant(self):
        """Return a queryset of all non-deleted versions."""
        return (self.get_queryset()
                    .exclude(visibility_override='deleted'))

    def public(self):
        """Return a queryset of all publicly-visible versions."""
        return (self.get_queryset()
                    .exclude(visibility='private', visibility_override='')
                    .exclude(visibility_override='private')
                    .exclude(visibility_override='deleted'))

    def all(self):
        assert False, ('all() is disabled on SubtitleVersion sets.  '
                       'Use full(), extant(), or public() instead.')

    def fetch_for_languages(self, languages, select_related=None,
                            prefetch_related=None, order_by=None,
                            public_only=False, video=None):
        """Fetch all versions for a list of languages

        This method is an efficient way to fetch all versions for a list of
        languages.  It caches several things to avoid future DB queries:
            - The public/private tip of each language
            - The language object for each version
            - The video for each language/version (if given)

        Arguments:
            languages: list of languages to fetch versions for
            select_related: list of select_related names for the
                SubtitleVersion query
            prefetch_related: list of prefetch_related names for the
                SubtitleVersion query
            order_by: Change the ordering of the versions
            public_only: Only fetch public versions
            video: Video to set for all versions/languages.  Use this if you
                know that they all belong to a single video to avoid some DB
                queries.

        Returns:
            dict mapping language IDs -> version objects
        """
        rv = dict((l.id, []) for l in languages)
        language_map = dict((l.id, l) for l in languages)
        if public_only:
            version_qs = self.public()
        else:
            version_qs = self.full()
        version_qs = version_qs.filter(subtitle_language__in=languages)
        if select_related:
            version_qs = version_qs.select_related(*select_related)
        if prefetch_related:
            version_qs = version_qs.prefetch_related(*prefetch_related)
        if order_by:
            version_qs = version_qs.order_by(order_by)
        for version in version_qs:
            language = language_map[version.subtitle_language_id]
            version.subtitle_language = language
            rv[version.subtitle_language_id].append(version)
            if video is not None:
                version.video = video
        def last_version(version_list):
            if version_list:
                return max(version_list, key=lambda v: v.version_number)
            else:
                return None
        for language in languages:
            if video is not None:
                language.video = video
            # set the tip cache
            if public_only:
                language.set_tip_cache('public',
                                       last_version(rv[language.id]))
            else:
                extant = [v for v in rv[language.id] if not v.is_deleted()]
                public = [v for v in extant if v.is_public()]
                if not public_only:
                    language.set_tip_cache('extant', last_version(extant))
                language.set_tip_cache('public', last_version(public))
        return rv

ORIGIN_API = 'api'
ORIGIN_IMPORTED = 'imported'
ORIGIN_PROVIDER = 'provider'
ORIGIN_LEGACY_EDITOR = 'web-legacy-editor'
ORIGIN_ROLLBACK = 'rollback'
ORIGIN_SCRIPTED = 'scripted'
ORIGIN_TERN = 'tern'
ORIGIN_UPLOAD = 'upload'
ORIGIN_WEB_EDITOR = 'web-editor'
ORIGIN_MANAGEMENT_PAGE = 'management-page'

SUBTITLE_VERSION_ORIGINS = (
    (ORIGIN_API, _("API")),
    (ORIGIN_LEGACY_EDITOR, _("Edited (legacy editor)")),
    (ORIGIN_IMPORTED, _("Imported")),
    (ORIGIN_PROVIDER, _("Provider")),
    (ORIGIN_ROLLBACK, _("Rollback")),
    (ORIGIN_SCRIPTED, _("Scripted")),
    (ORIGIN_TERN, _("Tern")),
    (ORIGIN_UPLOAD, _("Uploaded")),
    (ORIGIN_WEB_EDITOR, _("Edited")),
    (ORIGIN_MANAGEMENT_PAGE, _("Management Page")),
)

class SubtitleVersion(models.Model):
    """SubtitleVersions are the equivalent of a 'changeset' in a VCS.

    They are designed with a few key principles in mind.

    First, SubtitleVersions should be mostly immutable.  Once written they
    should never be changed, unless a team needs to publish or unpublish them.
    Any other changes should simply create a new version.

    Second, SubtitleVersions are self-contained.  There's a little bit of
    denormalization going on with the video and language_code fields, but this
    makes it much easier for a SubtitleVersion to stand on its own and will
    improve performance overall.

    Because they're (mostly) immutable, the denormalization is less of an issue
    than it would be otherwise.

    You should only create new SubtitleVersions through the `add_version` method
    of SubtitleLanguage instances.  This will ensure consistency and handle
    updating the parentage and version numbers correctly.

    """
    parents = models.ManyToManyField('self', symmetrical=False, blank=True)

    video = models.ForeignKey(Video, related_name='newsubtitleversion_set')
    subtitle_language = models.ForeignKey(SubtitleLanguage)
    language_code = models.CharField(max_length=16,
                                     choices=translation.ALL_LANGUAGE_CHOICES)

    # If you just want to *check* the visibility of a version you probably want
    # to use the is_public and is_private methods instead, which handle the
    # logic of visibility + visibility_override.
    visibility = models.CharField(max_length=10,
                                  choices=(('public', 'public'),
                                           ('private', 'private'),),
                                  default='public')

    # Visibility override can be used by team admins to force a specific type of
    # visibility for a version.  If set, it takes precedence over, but does not
    # affect, the main visibility field.
    visibility_override = models.CharField(max_length=10, blank=True,
                                           choices=(('public', 'public'),
                                                    ('private', 'private'),
                                                    ('deleted', 'deleted'),),
                                           default='')

    version_number = models.PositiveIntegerField(default=1)

    author = models.ForeignKey(User, related_name='newsubtitleversion_set',
                               default=settings.ANONYMOUS_USER_ID)

    title = models.CharField(max_length=2048, blank=True)
    description = models.TextField(blank=True)
    note = models.CharField(max_length=512, blank=True, default='')

    # If this version is a rollback we record the version number of its source.
    # Note that there are three possible values here:
    #
    # None: This version is not a rollback.
    # 0: This version is a rollback, but we don't know the source (legacy data).
    # 1+: This version is a rollback and the source is version N.
    #
    # You should probably just use is_rollback and get_rollback_source to work
    # with this value.
    rollback_of_version_number = models.PositiveIntegerField(null=True,
                                                             blank=True,
                                                             default=None)

    # Keeps tab of how this SV was originated (uploads, api, etc)
    origin = models.CharField(max_length=255, choices=SUBTITLE_VERSION_ORIGINS,
                              blank=True, default='')
    # Denormalized count of the number of subtitles this version contains, for
    # easier filtering later.
    subtitle_count = models.PositiveIntegerField(default=0)

    created = models.DateTimeField(editable=False)

    meta_1_content = metadata.MetadataContentField()
    meta_2_content = metadata.MetadataContentField()
    meta_3_content = metadata.MetadataContentField()

    # Subtitles are stored in a text blob, serialized as base64'ed zipped XML
    # (oh the joys of Django).  Use the subtitles property to get and set them.
    # You shouldn't be touching this field.
    serialized_subtitles = models.TextField()

    # Lineage is stored as a blob of JSON to save on DB rows.  You shouldn't
    # need to touch this field yourself, use the lineage property.
    serialized_lineage = models.TextField(blank=True)

    objects = SubtitleVersionManager.from_queryset(SubtitleVersionQuerySet)()

    def title_display(self):
        if self.title and self.title.strip():
            return self.title
        else:
            # fall back to the video title, but prevent infinite loops if we
            # are the primary audio language
            return self.video.title

    def is_for_primary_audio_language(self):
        return self.video.primary_audio_language_code == self.language_code

    def get_subtitles(self):
        """Return the SubtitleSet for this version.

        A SubtitleSet will always be returned.  It may be empty if there are no
        subtitles.

        """
        # We cache the parsed subs for speed.
        if self._subtitles == None:
            self._subtitles = load_from(decompress(self.serialized_subtitles),
                    type='dfxp').to_internal()
            # force the subtitles to have the correct language code.  For a
            # while we had a bug where we always set to to "en"
            self._subtitles.set_language(self.language_code)

        return self._subtitles

    def set_subtitles(self, subtitles):
        """Set the SubtitleSet for this version.

        You have a few options here:

        * Passing None will set the subtitles to an empty set.
        * Passing a SubtitleSet will set the subtitles to that set.
        * Passing a string of XML will treat it as DXFP and set it directly.
        * Passing a vanilla list (or any iterable) of subtitle tuples will
          create a SubtitleSet from that.

        """
        # TODO: Fix the language code to use the proper standard.
        if subtitles == None:
            subtitles = create_new_subtitles(self.language_code)
        elif isinstance(subtitles, str) or isinstance(subtitles, unicode):
            subtitles = SubtitleSet(self.language_code, initial_data=subtitles)
        elif isinstance(subtitles, SubtitleSet):
            pass
        else:
            try:
                i = iter(subtitles)
                subtitles = SubtitleSet.from_list(self.language_code, i)
            except TypeError:
                raise TypeError("Cannot create SubtitleSet from type %s"
                                % str(type(subtitles)))

        self.subtitle_count = len(subtitles)
        self.serialized_subtitles = compress(subtitles.to_xml())

        # We cache the parsed subs for speed.
        self._subtitles = subtitles


    def get_lineage(self):
        # We cache the parsed lineage for speed.
        if self._lineage == None:
            if self.serialized_lineage:
                self._lineage = json_to_lineage(self.serialized_lineage)
            else:
                self._lineage = {}

        return self._lineage

    def set_lineage(self, lineage):
        self.serialized_lineage = lineage_to_json(lineage)
        self._lineage = lineage

    lineage = property(get_lineage, set_lineage)

    class Meta:
        unique_together = [('video', 'subtitle_language', 'version_number'),
                           ('video', 'language_code', 'version_number')]


    def __init__(self, *args, **kwargs):
        """Create a new SubtitleVersion.

        You probably don't need this.  You probably want
        apps.subtitles.pipeline.add_subtitles instead.  Or at the very least you
        want the add_version method of SubtitleLanguage instances.

        `subtitles` can be given in any of the forms supported by set_subtitles.

        `lineage` should be a Python dictionary describing the lineage of this
        version.

        """
        # This is a bit clumsy, but we need to handle the subtitles kwarg like
        # this for it to work properly.  If it's given, we set the subtitles
        # appropriately after we create the version object.  If it's not given,
        # we *don't* set the subtitles at all -- we just let the
        # serialized_subtitles field stay as it is.
        has_subtitles = 'subtitles' in kwargs
        subtitles = kwargs.pop('subtitles', None)

        lineage = kwargs.pop('lineage', None)

        self.duration = kwargs.pop('duration', None)
        super(SubtitleVersion, self).__init__(*args, **kwargs)
        self._subtitles = None
        if has_subtitles:
            self.set_subtitles(subtitles)

        self._lineage = None
        if lineage != None:
            self.lineage = lineage

    def __unicode__(self):
        return u'SubtitleVersion %s / %s / %s v%s' % (
            (self.id or '(unsaved)'), self.video.video_id,
            self.get_language_code_display(), self.version_number
        )

    def clean(self):
        if self.rollback_of_version_number != None:
            if self.rollback_of_version_number >= self.version_number:
                raise ValidationError(
                    "The version number of a rollback's source must be less "
                    "than version number of the rollback itself!")

    def save(self, *args, **kwargs):
        creating = not self.pk
        video_needs_save = False
        metadata = kwargs.pop('metadata', None)

        if creating and not self.created:
            self.created = dates.now()
        if metadata is not None:
            self.update_metadata(metadata, commit=False)
            video_needs_save = True

        # Sanity checking of the denormalized data.
        assert self.language_code == self.subtitle_language.language_code, \
               "Version language code does not match Language language code!"

        assert self.video_id == self.subtitle_language.video_id, \
               "Version video does not match Language video!"

        assert self.visibility in ('public', 'private',), \
            "Version visibility must be either 'public' or 'private'!"
        super(SubtitleVersion, self).save(*args, **kwargs)

        if self.is_public() and self.is_for_primary_audio_language():
            self._set_video_data()
        if video_needs_save:
            self.video.save()

    def is_rtl(self):
        return translation.is_rtl(self.language_code)

    def dir(self):
        if self.is_rtl():
            return 'rtl'
        else:
            return 'ltr'

    def get_version_display(self):
        return fmt(ugettext(u'%(subtitle_language)s (version %(number)s)'),
                   subtitle_language=self.get_language_code_display(),
                   number=self.version_number)

    def get_ancestors(self):
        """Return all ancestors of this version.  WARNING: MAY EAT YOUR DB!

        Returning all ancestors of a version is very database-intensive, because
        we need to walk each relation.  It will make roughly l^b database calls,
        where l is the length of a branch of history and b is the "branchiness".

        You probably don't need this.  You probably want to use the lineage
        instead.  This is mostly here for sanity tests.

        """
        def _ancestors(version):
            return [version] + list(mapcat(_ancestors, version.parents.full()))

        return set(mapcat(_ancestors, self.parents.full()))

    def get_subtitle_count(self):
        # TODO: babelsubs now supports len() on SubtitleSet instances
        return len([s for s in self.get_subtitles().subtitle_items()])

    def get_changes(self):
        """Return (time_change, text_change).

        Beware.

        This was ported over from the old data model as a hack.  There are
        probably lots of cases where it doesn't work right.

        What we *really* need to do is sit down and come up with a scheme for
        diffing subtitle versions meaningfully.  Until then, we have this
        monstrosity.  Godspeed.

        """
        # TODO: Time only changes aren't quite right.

        if hasattr(self, '_time_change') and hasattr(self, '_text_change'):
            return (self._time_change, self._text_change)

        parent = self.previous_version()

        if not parent:
            return (1.0, 1.0)

        self._text_change, self._time_change = calc_changes(
            parent.get_subtitles(), self.get_subtitles(),
            HTMLGenerator.MAPPINGS)

        return self._time_change, self._text_change

    @property
    def time_change(self):
        if not hasattr(self, '_time_change'):
            self.get_changes()

        if not self._time_change:
            return '0%'
        else:
            return '%.0f%%' % (self._time_change * 100)

    @property
    def text_change(self):
        if not hasattr(self, '_text_change'):
            self.get_changes()

        if not self._text_change:
            return '0%'
        else:
            return '%.0f%%' % (self._text_change * 100)

    def is_tip(self, public=True):
        if public and not self.is_public():
            return False
        elif self.is_deleted():
            return False

        if public:
            qs = SubtitleVersion.objects.public()
        else:
            qs = SubtitleVersion.objects.extant()

        return not qs.filter(
            subtitle_language_id=self.subtitle_language_id,
            version_number__gt=self.version_number).exists()

    def is_private(self):
        if self.visibility_override in ('public', 'deleted'):
            return False
        elif self.visibility_override == 'private':
            return True
        else:
            return self.visibility == 'private'

    def is_public(self):
        if self.visibility_override == 'public':
            return True
        elif self.visibility_override in ('private', 'deleted'):
            return False
        else:
            return self.visibility == 'public'

    def is_deleted(self):
        return self.visibility_override == 'deleted'

    def is_rollback(self):
        """Return whether this version is a rollback of another version."""

        return self.rollback_of_version_number != None

    def get_rollback_source(self, full):
        """Return the SubtitleVersion that is the source for this rollback, or None.

        If full is given, deleted source versions will be returned.  Otherwise
        None will be returned if the source version has been deleted.

        """
        n = self.rollback_of_version_number
        if n == 0 or n == None:
            # Non-rollbacks and legacy rollbacks have no source.
            return None
        else:
            qs = self.sibling_set.full() if full else self.sibling_set.extant()
            try:
                return qs.get(version_number=n)
            except SubtitleVersion.DoesNotExist:
                # This can occur when full=False and the source version is
                # deleted.  In this case we just return None.
                return None


    @property
    def sibling_set(self):
        """Return a manager of a version's sibling versions, including itself.

        Sibling versions are versions for the same video and language.

        Since this returns a SubtitleVersionManager you can filter it further
        with .public() and so on.

        """
        return self.subtitle_language.subtitleversion_set

    def update_metadata(self, new_metadata, commit=True):
        metadata.update_child_and_video(self, self.video, new_metadata,
                                        commit)

    def get_metadata(self):
        return metadata.get_child_metadata(
            self, self.video,
            fallback_to_video=self.is_for_primary_audio_language())

    def get_metadata_for_display(self):
        return self.get_metadata().convert_for_display()

    # Metadata
    # This is basically a shim for the broken-ass tasks system that should go
    # away once we tear that out.  See the corresponding model of the same
    # name in videos.models for more information.
    def _get_metadata(self, key):
        """Return the metadata for this version for the given key, or None."""
        if self.metadata.all()._result_cache is not None:
            # We've already fetched the metadata objects, probably because of
            # a prefetch_related() call.  Use those instead of doing another
            # query.
            for m in self.metadata.all():
                if m.key == SubtitleVersionMetadata.KEY_IDS[key]:
                    return m.get_data()
            return None
        try:
            m = self.metadata.get(key=SubtitleVersionMetadata.KEY_IDS[key])
            return m.get_data()
        except SubtitleVersionMetadata.DoesNotExist:
            return None


    def get_reviewed_by(self):
        """Return the User that reviewed this version, or None.  Hits the DB."""
        return self._get_metadata('reviewed_by')

    def get_approved_by(self):
        """Return the User that approved this version, or None.  Hits the DB."""
        return self._get_metadata('approved_by')

    def get_workflow_origin(self):
        """Return the step of the workflow where this version originated, or None.

        Hits the DB.

        May be None if this version didn't come from any workflow step.

        """
        return self._get_metadata('workflow_origin')


    def _set_metadata(self, key, value):
        v, created = SubtitleVersionMetadata.objects.get_or_create(
                        subtitle_version=self,
                        key=SubtitleVersionMetadata.KEY_IDS[key])
        v.data = value
        v.save()


    def set_reviewed_by(self, user):
        """Set the User that reviewed this version."""
        self.subtitle_language.followers.add(user)
        self._set_metadata('reviewed_by', user.pk)

    def set_approved_by(self, user):
        """Set the User that approved this version."""
        self._set_metadata('approved_by', user.pk)

    def set_workflow_origin(self, origin):
        """Set the step of the workflow that this version originated in."""
        self._set_metadata('workflow_origin', origin)

    def _optimize_sibling_version(self, sibling):
        """Optimize siblings return in next_version()/previous_version()

        This method checks if we have a video/language cached and if so,
        caches that for the sibling version as well.
        """
        video_cache_name = SubtitleVersion.video.cache_name
        language_cache_name = SubtitleVersion.subtitle_language.cache_name
        if hasattr(self, video_cache_name):
            sibling.video = getattr(self, video_cache_name)
        if hasattr(self, language_cache_name):
            sibling.language = getattr(self, language_cache_name)
        return sibling

    def next_version(self, full=False):
        """Return the next SubtitleVersion.

        By default this does not return deleted versions.  If full is given
        deleted versions will be returned.

        """
        qs = self.sibling_set.full() if full else self.sibling_set.extant()
        qs = (qs.filter(version_number__gt=self.version_number)
              .order_by('version_number'))
        try:
            return self._optimize_sibling_version(qs[0])
        except IndexError:
            return None

    def _previous_version_cache_name(self, full):
        if full:
            return '_previous_version_full'
        else:
            return '_previous_version'

    def cache_previous_version(self, version, full=False):
        """Cache the previous version."""
        setattr(self, self._previous_version_cache_name(full), version)

    def previous_version(self, full=False):
        """Return the previous SubtitleVersion.


        By default this does not return deleted versions.  If full is given
        deleted versions will be returned.

        """
        cache_attr_name = self._previous_version_cache_name(full)
        if hasattr(self, cache_attr_name):
            return getattr(self, cache_attr_name)

        qs = self.sibling_set.full() if full else self.sibling_set.extant()
        qs = (qs.filter(version_number__lt=self.version_number)
              .order_by('-version_number'))
        try:
            previous_version = self._optimize_sibling_version(qs[0])
        except IndexError:
            previous_version = None
        setattr(self, cache_attr_name, previous_version)
        return previous_version

    def revision_time(self):
        today = date.today()
        yesterday = today - timedelta(days=1)
        d = self.created.date()
        if d == today:
            return 'Today'
        elif d == yesterday:
            return 'Yesterday'
        else:
            d = d.strftime('%m/%d/%Y')
        return d

    @property
    def has_subtitles(self):
        return self.subtitle_count is not 0

    def is_synced(self):
        return self.get_subtitles().fully_synced

    def is_synced_and_has_content(self):
        subtitle_items = self.get_subtitles().subtitle_items()
        if not subtitle_items:
            return False
        for item in subtitle_items:
            if (item.start_time is None or
                    item.end_time is None or
                    item.text == ''):
                return False
        return True

    def publish(self):
        """Make this version publicly viewable."""

        was_public = self.is_public()
        self.visibility = 'public'
        self.save()
        if not was_public and self.is_tip():
            self.subtitle_language.set_tip_cache('public', self)
        if self.is_for_primary_audio_language():
            self._set_video_data()

    def _set_video_data(self):
        changed = False
        if self.title:
            changed = True
            self.video.title = self.title
        if self.description:
            changed = True
            self.video.description = self.description
        if self.duration and not self.video.duration:
            changed = True
            self.video.duration = self.duration
        if self.video.get_metadata() != self.get_metadata():
            self.video.update_metadata(self.get_metadata(), commit=False)
            changed = True
        if changed:
            self.video.save()

    def unpublish(self, delete=False, signal=True):
        """Unpublish this version.

        :param delete: when set, flag the languages as deleted rather than
        private
        :param signal: when set we will emit the public_tip_changed() or
        subtitles_deleted signal
        """
        if signal:
            was_tip = self.is_tip()

        self.visibility_override = 'deleted' if delete else 'private'
        self.save()
        if signal and was_tip:
            self.subtitle_language.clear_tip_cache()
            new_tip = version=self.subtitle_language.get_tip(public=True)
            if new_tip is None:
                signals.subtitles_deleted.send(self.subtitle_language)

    @models.permalink
    def get_absolute_url(self):
        return ('videos:subtitleversion_detail',
                [self.video.video_id, self.language_code, self.subtitle_language.pk,
                 self.pk])

    def get_absolute_download_url(self, format="vtt", filename="subtitles"):
        return "{}://{}{}".format(settings.DEFAULT_PROTOCOL,
                                  settings.HOSTNAME,
                                  reverse("subtitles:download", kwargs={"video_id": self.video.video_id,
                                                                        "language_code": self.language_code,
                                                                        "version_number": self.version_number,
                                                                        "filename": filename,
                                                                        "format": format}))

class SubtitleVersionMetadata(models.Model):
    """This model is used to add extra metadata to SubtitleVersions.

    This is basically a shim for the broken-ass tasks system that should go away
    once we tear that out.  See the corresponding model of the same name in
    videos.models for more information.

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

class SubtitleNoteBase(models.Model):
    video = models.ForeignKey(Video, related_name='+')
    language_code = models.CharField(max_length=16,
                                     choices=translation.ALL_LANGUAGE_CHOICES)
    user = models.ForeignKey(User, related_name='+', null=True)
    body = models.TextField()
    created = models.DateTimeField(default=datetime.now)

    class Meta:
        abstract = True

    def get_username(self):
        return unicode(self.user)

class SubtitleNote(SubtitleNoteBase):
    pass
