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

from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.db import models
from django.db import transaction
from django.db.models import Q
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext, ungettext

from auth.models import CustomUser as User
from codefield import CodeField, Code
from comments.models import Comment
from mysqltweaks import query
from teams.models import Team, TeamVisibility, VideoVisibility
from teams.permissions import can_view_activity
from teams.permissions_const import (ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER,
                                     ROLE_CONTRIBUTOR, ROLE_NAMES)
from utils import dates
from utils import translation
from utils.text import fmt
from videos.models import Video

import json
import logging
logger = logging.getLogger(__name__)

# Track progress on migrating the old activity records
class ActivityMigrationProgress(models.Model):
    last_migrated_id = models.IntegerField()

# Couple of models that we use to track extra info related to activity records
class VideoDeletion(models.Model):
    url = models.URLField(max_length=512, blank=True)
    title = models.CharField(max_length=2048, blank=True)

class URLEdit(models.Model):
    old_url = models.URLField(max_length=512, blank=True)
    new_url = models.URLField(max_length=512, blank=True)

class SubtitleLanguageChange(models.Model):
    old_language = models.CharField(max_length=512, blank=True)

class TeamSettingsChangeInfo(models.Model):
    # Settings changes as a JSON encoded dict
    changes = models.TextField()

    SETTINGS_CHANGE_LABELS = {
        'team_visibility': _('Team Visibility'),
        'video_visibility': _('Video Visibility'),
        # is_visible is no longer a Team field, but we still need to suport
        # activity records about it
        'is_visible': _('Videos Public'),
    }
    SETTINGS_ENUMS = {
        'team_visibility': TeamVisibility,
        'video_visibility': VideoVisibility,
    }

    @classmethod
    def create_from_dict(cls, changes):
        return cls.objects.create(changes=json.dumps(changes))

    def get_changes(self):
        return json.loads(self.changes)

    def format_changes(self):
        """Get a list of changes to display to the user

        Returns:
            List of strings to displa to the user, for example:
                - Videos public changed to true
                - 13 miscellaneous settings changed

        """
        rv = []
        misc_count = 0
        for name, value in self.get_changes().items():
            if name in self.SETTINGS_CHANGE_LABELS:
                rv.append(fmt(ugettext(u'%(setting)s changed to %(value)s'),
                              setting=self.SETTINGS_CHANGE_LABELS[name],
                              value=self.format_value(name, value)))
            else:
                misc_count += 1
        if misc_count:
            rv.append(fmt(ungettext(
                u'%(count)s miscellaneous setting changed',
                u'%(count)s miscellaneous settings changed',
                misc_count), count=misc_count))
        return rv

    def format_value(self, name, value):
        if value == True:
            return ugettext('true')
        elif value == False:
            return ugettext('false')
        elif name in self.SETTINGS_ENUMS:
            return self.SETTINGS_ENUMS[name].lookup_slug(value).label
        else:
            return unicode(value)

class ActivityType(Code):
    # Model that the related_obj_id field points to
    related_model = None
    # Is this type still in active use?
    active = True

    def get_message(self, record, user):
        """Get the message to display in activity logs."""
        raise NotImplementedError()

    # TODO: remove this once the old team activity page is removed
    def get_old_message(self, record, user):
        """Remove the username from the message."""
        raise NotImplementedError()

    def get_action_name(self):
        """Get a short action name for display

        This is displayed on the video activity table, and should be pretty
        short.  Some examples are "edited", "commented", and "made primary".
        """
        return 'unknown'

    def get_related_obj(self, related_obj_id):
        ModelClass = self.related_model
        if ModelClass is None or related_obj_id is None:
            return None
        else:
            try:
                return (ModelClass.objects.all()
                        .select_related()
                        .get(id=related_obj_id))
            except ObjectDoesNotExist:
                logger.warn("Missing related object for activity record: {}".format(related_obj_id))
                return None

class ActivityMessageDict(object):
    """Helper class to format our messages.

    It knows how to fetch data for several standard keys that we use in our messages.
    """
    def __init__(self, record):
        self.record = record

    def __getattr__(self, key):
        if key == 'record':
            return self.record
        elif key == 'language_url':
            return self.record.get_language_url()
        elif key == 'language':
            return self.record.get_language_code_display()
        elif key == 'video_url':
            return self.record.get_video_url()
        elif key == 'video':
            return self.record.get_video_title()
        elif key == 'team':
            return self.record.team
        elif key == 'user':
            if self.record.user is None:
                return _("Somebody (possibly automatically)")
            else:
                return self.record.user.display_username
        else:
            # Like the fmt() function, display something in the message rather
            # than raise an exception
            return key

class VideoAdded(ActivityType):
    slug = 'video-added'
    label = _('Video Added')

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_('<strong>{user}</strong> added a video: '
                        '<a href="{video_url}">{video}</a>')), 
            user=data.user,
            video=data.video,
            video_url=data.video_url
            )

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_('added a video: <a href="{video_url}">{video}</a>')),
            video=data.video,
            video_url=data.video_url
            )

    def get_action_name(self):
        return _('added')

class VideoTitleChanged(ActivityType):
    slug = 'video-title-changed'
    label = _('Video title changed')

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_('<strong>{user}</strong> edited the title for: '
            '<a href="{video_url}">{video}</a>')),
            user=data.user,
            video=data.video,
            video_url=data.video_url
            )

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_('edited the title for: <a href="{video_url}">{video}</a>')),
            video=data.video,
            video_url=data.video_url
            )

    def get_action_name(self):
        return _('changed title')

class CommentAdded(ActivityType):
    slug = 'comment-added'
    label = _('Comment added')
    related_model = Comment

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        if record.language_code:
            return format_html(
                mark_safe(_(u'<strong>{user}</strong> commented on <a href="'
                '{language_url}">{language} subtitles</a> for <a href="{video_url}">'
                '{video}</a>')),
                user=data.user,
                language=data.language,
                language_url=data.language_url,
                video=data.video,
                video_url=data.video_url
                )
        else:
            return format_html(
                mark_safe(_(u'<strong>{user}</strong> commented on <a href="'
                '{video_url}">{video}</a>')),
                user=data.user,
                video=data.video,
                video_url=data.video_url
                )

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        if record.language_code:
            return format_html(
                mark_safe(_(u'commented on <a href="{language_url}">{language} '
                'subtitles</a> for <a href="{video_url}">{video}</a>')),
                language=data.language,
                language_url=data.language_url,
                video=data.video,
                video_url=data.video_url,
                team=data.team
                )
        else:
           return format_html(
                mark_safe(_(u'commented on <a href="{video_url}">{video}</a>')),
                video=data.video,
                video_url=data.video_url
                )

    def get_action_name(self):
        return _('commented')

class VersionAdded(ActivityType):
    slug = 'version-added'
    label = _('Version added')

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_(u'<strong>{user}</strong> edited <a href="{language_url}">'
            '{language} subtitles</a> for <a href="{video_url}">{video}</a>')),
            user=data.user,
            language=data.language,
            language_url=data.language_url,
            video=data.video,
            video_url=data.video_url
            )

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_(u'edited <a href="{language_url}">{language} subtitles</a>'
            ' for <a href="{video_url}">{video}</a>')),
            language=data.language,
            language_url=data.language_url,
            video=data.video,
            video_url=data.video_url
            )

    def get_action_name(self):
        return _('edited')

class VideoURLAdded(ActivityType):
    slug = 'video-url-added'
    label = _('Video URL added')
    related_model = URLEdit

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_(u'<strong>{user}</strong> added new URL for <a href="'
            '{video_url}">{video}</a>')),
            user=data.user,
            video=data.video,
            video_url=data.video_url
            )

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_(u'added new URL for <a href="{video_url}">{video}</a>')),
            video=data.video,
            video_url=data.video_url
            )

    def get_action_name(self):
        return _('added URL')

class TranslationAdded(ActivityType):
    slug = 'translation-added'
    label = _('Translation URL added')
    # Not tracked since around the DMR changes. We haven't had a new instance
    # of this since 2013
    active = False

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(mark_safe(_('<strong>{user}</strong> added a translation')),
                user=data.user)

    def get_old_message(self, record, user):
        return _('added a translation')

    def get_action_name(self):
        return _('translated')

class SubtitleRequestCreated(ActivityType):
    slug = 'subtitle-request-created'
    label = _('Subtitle request created')
    # I'm not sure exactly what this was supposed to be used for.  We have 0
    # instances of this in the dbase
    active = False

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(mark_safe(_('<strong>{user}</strong> created a subtitle request')),
                user=data.user)

    def get_message(self, record, user):
        return _('created a subtitle request')

    def get_action_name(self):
        return _('requested')

class VersionApproved(ActivityType):
    slug = 'version-approved'
    label = _('Version approved')

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_('<strong>{user}</strong> approved <a href="{language_url}">'
            '{language}</a> subtitles for <a href="{video_url}">{video}</a>')),
            user=data.user,
            language=data.language,
            language_url=data.language_url,
            video=data.video,
            video_url=data.video_url
            )

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_('approved <a href="{language_url}">{language}</a> subtitles'
            ' for <a href="{video_url}">{video}</a>')),
            language=data.language,
            language_url=data.language_url,
            video=data.video,
            video_url=data.video_url
            )

    def get_action_name(self):
        return _('approved')

class MemberJoined(ActivityType):
    slug = 'member-joined'
    label = _('Member Joined')

    # For the related_obj_id field, we store an integer code for the role.
    # Map member role values to those codes
    role_to_code = {
        ROLE_OWNER: 1,
        ROLE_ADMIN: 2,
        ROLE_MANAGER: 3,
        ROLE_CONTRIBUTOR: 4,
    }
    code_to_role = { v: k for (k, v) in role_to_code.items() }

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_("<strong>{user}</strong> joined the {team} team as a {role}")),
            user=data.user, team=data.team, role=self.get_role_name(record.related_obj_id))

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            _("joined the {team} team as a {role}"),
            team=data.team, role=self.get_role_name(record.related_obj_id))

    def get_action_name(self):
        return _('joined')

    def get_related_obj(self, related_obj_id):
        try:
            return self.code_to_role[related_obj_id]
        except KeyError:
            return None

    def get_role_name(self, related_obj_id):
        role = self.get_related_obj(related_obj_id)
        return ROLE_NAMES.get(role, _('Unknown role'))

class VersionRejected(ActivityType):
    slug = 'version-rejected'
    label = _('Version Rejected')

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_('<strong>{user}</strong> rejected <a href="{language_url}">'
            '{language}</a> subtitles for <a href="{video_url}">{video}</a>')),
            user=data.user,
            language=data.language,
            language_url=data.language_url,
            video=data.video,
            video_url=data.video_url,
            )

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_('rejected <a href="{language_url}">{language}</a> subtitles'
            ' for <a href="{video_url}">{video}</a>')),
            language=data.language,
            language_url=data.language_url,
            video=data.video,
            video_url=data.video_url,
            )

    def get_action_name(self):
        return _('rejected')

class MemberLeft(ActivityType):
    slug = 'member-left'
    label = _('Member Left')

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_("<strong>{user}</strong> left the {team} team")),
            user=data.user,
            team=data.team
            )

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(_("left the {team} team"), team=data.team)

    def get_action_name(self):
        return _('left')

class VersionReviewed(ActivityType):
    slug = 'version-reviewed'
    label = _('Version Reviewed')
    # Probably related to tasks, but never used.  There are 0 instances in our
    # production dbase
    active = False

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_('<strong>{user}</strong> reviewed <a href="{language_url}">'
            '{language}</a> subtitles for <a href="{video_url}">{video}</a>')),
            user=data.user,
            language=data.language,
            language_url=data.language_url,
            video=data.video,
            video_url=data.video_url
            )

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_('reviewed <a href="{language_url}">{language}</a> subtitles'
            ' for <a href="{video_url}">{video}</a>')),
            language=data.language,
            language_url=data.language_url,
            video=data.video,
            video_url=data.video_url
            )

    def get_action_name(self):
        return _('reviewed')

class VersionAccepted(ActivityType):
    slug = 'version-accepted'
    label = _('Version Accepted')

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_('<strong>{user}</strong> accepted <a href="{language_url}">'
            '{language}</a> subtitles for <a href="{video_url}">{video}</a>')),
            user=data.user,
            language=data.language,
            language_url=data.language_url,
            video=data.video,
            video_url=data.video_url
            )

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_('accepted <a href="{language_url}">{language}</a>'
            ' subtitles for <a href="{video_url}">{video}</a>')),
            language=data.language,
            language_url=data.language_url,
            video=data.video,
            video_url=data.video_url
            )

    def get_action_name(self):
        return _('accepted')

class VersionDeclined(ActivityType):
    slug = 'version-declined'
    label = _('Version Declined')

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_('<strong>{user}</strong> declined <a href="{language_url}">'
            '{language}</a> subtitles for <a href="{video_url}">{video}</a>')),
            user=data.user,
            language=data.language,
            language_url=data.language_url,
            video=data.video,
            video_url=data.video_url
            )

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        return format_html(
            mark_safe(_('declined <a href="{language_url}">{language}</a>'
            ' subtitles for <a href="{video_url}">{video}</a>')),
            language=data.language,
            language_url=data.language_url,
            video=data.video,
            video_url=data.video_url
            )

    def get_action_name(self):
        return _('declined')

class SubtitleLanguageChanged(ActivityType):
    slug='language-changed'
    label = _('Language Changed')
    related_model = SubtitleLanguageChange

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        change = record.get_related_obj()
        if change:
            return format_html(
                mark_safe(_('<strong>{user}</strong> changed a subtitle language for <a '
                'href="{video_url}">{video}</a> from {old_language} to  <a href="'
                '{language_url}">{language}</a>')),
                old_language=change.old_language,
                user=data.user,
                language=data.language,
                language_url=data.language_url,
                video=data.video,
                video_url=data.video_url
                )
        else:
            return format_html(
                mark_safe(_('<strong>{user}</strong> changed a subtitle language for <a '
                'href="{video_url}">{video}</a> to <a href="{language_url}">'
                '{language}</a>')),
                user=data.user,
                language=data.language,
                language_url=data.language_url,
                video=data.video,
                video_url=data.video_url
                )

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        change = record.get_related_obj()
        if change:
            return format_html(
                mark_safe(_('changed a subtitle language for <a href="{video_url}">{video}'
                '</a> from {old_language} to <a href="{language_url}">{language}</a>')),
                old_language=change.old_language,
                language=data.language,
                language_url=data.language_url,
                video=data.video,
                video_url=data.video_url
                )
        else:
            return format_html(
                mark_safe(_('changed a subtitle language for <a href="{video_url}">{video}'
                '</a> to <a href="{language_url}">{language}</a>')),
                language=data.language,
                language_url=data.language_url,
                video=data.video,
                video_url=data.video_url
                )

    def get_action_name(self):
        return _('changed subtitle language')

class VideoDeleted(ActivityType):
    slug = 'video-deleted'
    label = _('Video deleted')
    related_model = VideoDeletion

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        deletion = record.get_related_obj()
        if deletion is not None:
            title = deletion.title
        else:
            title = _('Unknown video')
        return format_html(
            mark_safe(_('<strong>{user}</strong> deleted a video: {title}')),
            user=data.user, title=title)

    def get_old_message(self, record, user):
        deletion = record.get_related_obj()
        if deletion is not None:
            title = deletion.title
        else:
            title = _('Unknown video')
        return format_html(_('deleted a video: {title}'), title=title)

    def get_action_name(self):
        return _('deleted')

class VideoURLEdited(ActivityType):
    slug = 'video-url-edited'
    label = _('Video URL edited')
    related_model = URLEdit

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        url_edit = record.get_related_obj()
        if url_edit is not None:
            return format_html(
                mark_safe(_('<strong>{user}</strong> changed primary url from <a '
                'href="{old_url}">{old_url}</a> to <a href="{new_url}">{new_url}</a>')),
                user=data.user,
                old_url=url_edit.old_url,
                new_url=url_edit.new_url)
        else:
            return format_html(
                mark_safe(_('<strong>{user}</strong> changed the primary url')),
                user=data.user)

    def get_old_message(self, record, user):
        url_edit = record.get_related_obj()
        if url_edit is not None:
            return format_html(
                mark_safe(_('changed primary url from <a href="{old_url}">{old_url}</a> '
                'to <a href="{new_url}">{new_url}</a>')),
                old_url=url_edit.old_url,
                new_url=url_edit.new_url)
        else:
            return _('changed the primary url')

    def get_action_name(self):
        return _('made URL primary')

class VideoURLDeleted(ActivityType):
    slug = 'video-url-deleted'
    label = _('Video URL deleted')
    related_model = URLEdit

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        url_edit = record.get_related_obj()
        return format_html(
            mark_safe(_('<strong>{user}</strong> deleted url <a href="{old_url}">{old_url}</a>')),
            user=data.user, old_url=url_edit.old_url)

    def get_old_message(self, record, user):
        url_edit = record.get_related_obj()
        return format_html(
            mark_safe(_('deleted url <a href="{old_url}">{old_url}</a>')),
            old_url=url_edit.old_url)

    def get_action_name(self):
        return _('deleted URL')

class VideoMovedToTeam(ActivityType):
    slug = 'video-moved-to-team'
    label = _('Video moved to team')
    related_model = Team

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        team = record.get_related_obj()
        if team is None:
            return format_html(
                mark_safe(_('<strong>{user}</strong> moved <a href="{video_url}">'
                '{video}</a> to {team}')),
                user=data.user,
                video=data.video,
                video_url=data.video_url,
                team=data.team
                )
        elif user is not None and can_view_activity(team, user):
            from_team_url = reverse('teams:dashboard', args=(team.slug,))
            return format_html(
                mark_safe(_('<strong>{user}</strong> moved <a href="{video_url}">{video}</a>'
                ' to {team} from <a href="{from_team_url}">{from_team}</a>')),
                from_team_url=from_team_url, from_team=team.name,
                user=data.user,
                video=data.video,
                video_url=data.video_url,
                team=data.team
                )
        else:
            return format_html(
                mark_safe(_('<strong>{user}</strong> moved <a href="{video_url}">{video}</a>'
                ' to {team} from another team')),
                user=data.user,
                video=data.video,
                video_url=data.video_url,
                team=data.team
                )

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        team = record.get_related_obj()
        if team is None:
            return format_html(
                mark_safe(_('moved <a href="{video_url}">{video}</a> to {team}')),
                video=data.video,
                video_url=data.video_url,
                team=data.team
                )
        elif user is not None and can_view_activity(team, user):
            from_team_url = reverse('teams:dashboard', args=(team.slug,))
            return format_html(
                mark_safe(_('moved <a href="{video_url}">{video}</a> to {team} from '
                '<a href="{from_team_url}">{from_team}</a>')),
                from_team_url=from_team_url, from_team=team.name,
                video=data.video,
                video_url=data.video_url,
                team=data.team
                )
        else:
            return format_html(
                mark_safe(_('moved <a href="{video_url}">{video}</a> to {team} from '
                'another team')),
                video=data.video,
                video_url=data.video_url,
                team=data.team
                )

    def get_action_name(self):
        return _('moved video to team')

class VideoMovedFromTeam(ActivityType):
    slug = 'video-moved-from-team'
    label = _('Video moved from team')
    related_model = Team

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        team = record.get_related_obj()
        if team is None:
            return format_html(
                mark_safe(_('<strong>{user}</strong> removed <a href="{video_url}">{video}</a>'
                ' from {team}')),
                user=data.user,
                video=data.video,
                video_url=data.video_url,
                team=data.team
                )
        elif user is not None and can_view_activity(team, user):
            to_team_url = reverse('teams:dashboard', args=(team.slug,))
            return format_html(
                mark_safe(_('<strong>{user}</strong> moved <a href="{video_url}">{video}</a>'
                ' from {team} to <a href="{to_team_url}">{to_team}</a>')),
                to_team_url=to_team_url, to_team=team.name,
                user=data.user,
                video=data.video,
                video_url=data.video_url,
                team=data.team
                )
        else:
            return format_html(
                mark_safe(_('<strong>{user}</strong> moved <a href="{video_url}">{video}</a>'
                ' from {team} to another team')),
                user=data.user,
                video=data.video,
                video_url=data.video_url,
                team=data.team
                )

    def get_old_message(self, record, user):
        data = ActivityMessageDict(record)
        if team is None:
            return format_html(
                mark_safe(_('removed <a href="{video_url}">{video}</a> from {team}')),
                video=data.video,
                video_url=data.video_url,
                team=data.team
                )
        elif user is not None and can_view_activity(team, user):
            to_team_url = reverse('teams:dashboard', args=(team.slug,))
            return format_html(
                mark_safe(_('moved <a href="{video_url}">{video}</a> from {team} to '
                '<a href="{to_team_url}">{to_team}</a>')),
                to_team_url=to_team_url, to_team=team.name,
                video=data.video,
                video_url=data.video_url,
                team=data.team
                )
        else:
            return format_html(
                mark_safe(_('moved <a href="{video_url}">{video}</a> from {team} to '
                'another team')),
                video=data.video,
                video_url=data.video_url,
                team=data.team
                )

    def get_action_name(self):
        return _('moved video from team')

class TeamSettingsChanged(ActivityType):
    slug = 'team-settings-changed'
    label = _('Team settings changed')
    related_model = TeamSettingsChangeInfo

    def get_message(self, record, user):
        data = ActivityMessageDict(record)
        change_info = record.get_related_obj()
        return format_html(
            mark_safe(_('<strong>{user}</strong> changed team settings: {changes}')),
            user=data.user,
            changes=', '.join(change_info.format_changes()))

    def get_old_message(self, record, user):
        change_info = record.get_related_obj()
        return format_html(
            _('changed team settings: {changes}'),
            changes=', '.join(change_info.format_changes()))

    def get_action_name(self):
        return _('changed team setting')

activity_choices = [
    VideoAdded, VideoTitleChanged, CommentAdded, VersionAdded, VideoURLAdded,
    TranslationAdded, SubtitleRequestCreated, VersionApproved, MemberJoined,
    VersionRejected, MemberLeft, VersionReviewed, VersionAccepted,
    VersionDeclined, VideoDeleted, VideoURLEdited, VideoURLDeleted,
    VideoMovedToTeam, VideoMovedFromTeam, TeamSettingsChanged, SubtitleLanguageChanged,
]

class ActivityQuerySet(query.QuerySet):
    def original(self):
        # For some reason, using copied_from__isnull=True results in an extra
        # join.  So we need a custom WHERE clause
        return self.extra(where=[
            'activity_activityrecord.copied_from_id IS NULL',
        ])

    # Split team activity into "team activity" and "team video activity".
    # This is a holdover from the old activity system.  It would be nice to
    # remove this, see #2559.
    TEAM_ACTIVITY_TYPES = ['member-left', 'member-joined']
    def team_activity(self):
        return self.filter(type__in=self.TEAM_ACTIVITY_TYPES)

    def team_video_activity(self):
        return self.exclude(type__in=self.TEAM_ACTIVITY_TYPES)

    def viewable_by_user(self, user):
        if user.is_superuser:
            return self
        q = (Q(team__isnull=True) |
             Q(team__team_visibility=TeamVisibility.PUBLIC))
        if user.is_authenticated():
            q |= Q(team__in=user.teams.all())

        return self.filter(q)

    def for_video(self, video, team=None):
        qs = self.filter(video=video).original()
        if team is None:
            return qs.filter(private_to_team=False)
        else:
            return qs.filter(team=team)

    def for_api_user(self, user):
        # Used for the default API listing.  It would be nice to simplify this
        # see #2557
        return (self
                .filter(Q(user=user) | Q(team__in=user.teams.all()))
                .original()
                .distinct())

    def for_user(self, user):
        return self.filter(user=user).original()

    def for_team(self, team):
        return self.filter(team=team)

class ActivityManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return (ActivityQuerySet(self.model, using=self._db)
                .select_related('user', 'team', 'video'))

    def create(self, type, **attrs):
        return super(ActivityManager, self).create(type=type, **attrs)

    def create_for_video(self, type, video, team=None, **attrs):
        team_video = video.get_team_video()
        if team is None:
            team_id = team_video.team_id if team_video else None
        else:
            team_id = team.id
        return self.create(
            type=type, video=video, team_id=team_id,
            video_language_code=video.primary_audio_language_code, **attrs)

    def create_for_video_added(self, video):
        return self.create_for_video('video-added', video,
                                     user=video.user, created=video.created)

    def create_for_comment(self, video, comment, language_code=''):
        return self.create_for_video(
            'comment-added', video, user=comment.user,
            created=comment.submit_date, related_obj_id=comment.id,
            language_code=language_code)

    def create_for_subtitle_version(self, version):
        return self.create_for_video(
            'version-added', version.video,
            language_code=version.language_code, user=version.author,
            created=version.created)

    def create_for_subtitle_language_changed(self, user, subtitle_language, old_language_code):
        with transaction.atomic():
            change = SubtitleLanguageChange.objects.create(
                        old_language=translation.get_language_label(old_language_code))
            return self.create_for_video('language-changed', subtitle_language.video,
                                         user=user, created=dates.now(),
                                         language_code=subtitle_language.language_code,
                                         related_obj_id=change.id)

    def create_for_video_url_added(self, video_url):
        with transaction.atomic():
            url_edit = URLEdit.objects.create(new_url=video_url.url)
            return self.create_for_video('video-url-added', video_url.video,
                                         user=video_url.added_by,
                                         created=video_url.created,
                                         related_obj_id=url_edit.id)

    def create_for_video_title_edited(self, video, user):
        return self.create_for_video('video-title-changed', video,
                                     user=user,
                                     created=dates.now())

    def create_for_version_approved(self, version, user):
        return self.create_for_video('version-approved', version.video,
                                     user=user,
                                     language_code=version.language_code,
                                     created=dates.now())

    def create_for_version_accepted(self, version, user):
        return self.create_for_video('version-accepted', version.video,
                                     user=user,
                                     language_code=version.language_code,
                                     created=dates.now())

    def create_for_version_rejected(self, version, user):
        return self.create_for_video('version-rejected', version.video,
                                     user=user,
                                     language_code=version.language_code,
                                     created=dates.now())

    def create_for_version_declined(self, version, user):
        return self.create_for_video('version-declined', version.video,
                                     user=user,
                                     language_code=version.language_code,
                                     created=dates.now())

    def create_for_new_member(self, member):
        role_code = MemberJoined.role_to_code[member.role]
        return self.create('member-joined', team=member.team,
                           user=member.user, created=member.created,
                           related_obj_id=role_code)

    def create_for_member_deleted(self, member):
        return self.create('member-left', team=member.team,
                           user=member.user, created=dates.now())

    def create_for_team_settings_changed(self, team, user, changes):
        change_info = TeamSettingsChangeInfo.create_from_dict(changes)
        return self.create('team-settings-changed', team=team,
                           user=user, related_obj_id=change_info.id,
                           created=dates.now())

    def create_for_video_deleted(self, video, user):
        with transaction.atomic():
            team_video = video.get_team_video()
            team_id = team_video.team_id if team_video else None
            url = video.get_video_url()
            video_deletion = VideoDeletion.objects.create(
                title=video.title_display(),
                url=url if url is not None else '')
            return self.create('video-deleted', user=user,
                               created=dates.now(), team_id=team_id,
                               related_obj_id=video_deletion.id)

    def create_for_video_url_made_primary(self, video_url, old_url, user):
        with transaction.atomic():
            url_edit = URLEdit.objects.create(old_url=old_url.url,
                                              new_url=video_url.url)
            return self.create_for_video('video-url-edited', video_url.video,
                                         user=user, created=dates.now(),
                                         related_obj_id=url_edit.id)

    def create_for_video_url_deleted(self, video_url, user):
        with transaction.atomic():
            url_edit = URLEdit.objects.create(old_url=video_url.url)
            return self.create_for_video('video-url-deleted', video_url.video,
                                         user=user, created=dates.now(),
                                         related_obj_id=url_edit.id)

    def create_for_video_moved(self, video, user, from_team=None, to_team=None):
        with transaction.atomic():
            if from_team is not None:
                if to_team is not None:
                    to_team_id = to_team.id
                else:
                    to_team_id = None
                self.create_for_video('video-moved-from-team', video,
                                      user=user, created=dates.now(),
                                      related_obj_id=to_team_id,
                                      team=from_team,
                                      private_to_team=True)
            if to_team is not None:
                if from_team is not None:
                    from_team_id = from_team.id
                else:
                    from_team_id = None
                self.create_for_video('video-moved-to-team', video,
                                      user=user, created=dates.now(),
                                      related_obj_id=from_team_id,
                                      team=to_team,
                                      private_to_team=True)

    def move_video_records_to_team(self, video, team):
        for record in self.filter(video=video, copied_from=None,
                                  private_to_team=False):
            record.move_to_team(team)

class ActivityRecord(models.Model):
    type = CodeField(choices=activity_choices)
    # User activity stream for this record.  Almost always this is the user
    # who performed the action, the exceptions are things like the
    # member-joined record when an admin manually adds a user to a team.
    user = models.ForeignKey(User, blank=True, null=True,
                             related_name='activity')
    # Video activity stream for this record.  This will be NULL for non-video
    # records, like team member join/leave.
    video = models.ForeignKey(Video, blank=True, null=True,
                              related_name='activity')
    # Language code of the video.  We denormalize this field because we use it
    # as a filter and we want to avoid a join in that case
    video_language_code = models.CharField(max_length=16, blank=True,
                                           default='',
                                           choices=translation.ALL_LANGUAGE_CHOICES)
    # Team activity stream for this record.  If a video moves from team to
    # team, we will make a copy of the video activity and have record in each
    # team.  You can use the copied_from field to determine which was the
    # original record.
    team = models.ForeignKey(Team, blank=True, null=True,
                             related_name='activity')
    # Language related to the activity for things like version-added.
    language_code = models.CharField(max_length=16, blank=True, default='',
                                     choices=translation.ALL_LANGUAGE_CHOICES)
    # This works like a generic foreign key.  Depending on the type field, it
    # will reference a different model
    related_obj_id = models.IntegerField(blank=True, null=True)
    created = models.DateTimeField(default=dates.now, db_index=True)
    # When a video moves from team to team, we create copies of each record.
    # The original gets moved to the new team and the copy stays with the old
    # team.
    copied_from = models.ForeignKey('self', blank=True, null=True,
                                    related_name='copies')
    # Make a record private to a team.  This does 2 things: disable the
    # copying behavior above and not include it in the default video listing.
    private_to_team = models.BooleanField(default=False, blank=True)

    objects = ActivityManager.from_queryset(ActivityQuerySet)()

    class Meta:
        ordering = ['-created', '-id']
        index_together = [
            # Team activity stream.  There's often lots of activity per-team,
            # so we add some extra indexes here
            ('team', 'created'),
            ('team', 'user', 'created'),
            ('team', 'type', 'created'),
            ('team', 'language_code', 'created'),
            ('team', 'type', 'video_language_code', 'created'),
            # Video activity stream
            ('video', 'copied_from', 'created'),
            # User activity stream
            ('user', 'copied_from', 'created'),
        ]

    def __unicode__(self):
        return u'ActivityRecord: {}'.format(self.type)

    @classmethod
    def active_type_choices(cls):
        code_list = cls._meta.get_field('type').code_list
        return [ (code.slug, code.label) for code in code_list if code.active ]

    def move_to_team(self, new_team):
        with transaction.atomic():
            # Make a copy of the record for our current team
            if self.team is not None:
                self.make_copy()
            # Move to the new team
            self.team = new_team
            self.save()
            # Delete any old copies on the new team
            if new_team is not None:
                ActivityRecord.objects.filter(copied_from=self,
                                              team_id=new_team.id).delete()

    def make_copy(self):
        copy = ActivityRecord(copied_from=self)
        fields = ['type', 'user_id', 'team_id', 'video_id', 'language_code',
                  'related_obj_id', 'created', ]
        for name in fields:
            setattr(copy, name, getattr(self, name))
        copy.save()
        return copy

    def get_language_code_display(self):
        if self.language_code:
            try:
                language_code_display = translation.get_language_label(self.language_code)
            except KeyError:
                logger.error("Error with language code {} in activity record {}".format(self.id, self.language_code))
                try:
                    language_code_display = translation.get_language_label(self.language_code.lower())
                except KeyError:
                    logger.error("Error with language code {} in activity record {} can not be fixed".format(self.id, self.language_code))
                    language_code_display = 'Unknown language'
            return language_code_display
        else:
            return ''

    def get_video_url(self):
        if self.video:
            url = self.video.get_absolute_url()
            if self.team and self.team.workflow_type != 'O':
                url += "?team={}".format(self.team.slug)
            return url
        else:
            return ''

    def get_language_url(self):
        if self.video and self.language_code:
            url = self.video.get_language_url_with_id(self.language_code)
            if not url:
                return ''
            if self.team and self.team and self.team.workflow_type != 'O':
                url += "?team={}".format(self.team.slug)
            return url
        elif self.video:
            return self.video.get_language_url_with_id(self.language_code)
        else:
            return ''

    def get_video_title(self):
        if self.video:
            return self.video.title_display()
        else:
            return ''

    def get_user_display(self):
        if self.user is None:
            return _("Somebody (possibly automatically)")
        else:
            return self.user.username

    def get_message(self, user=None):
        return self.type_obj.get_message(self, user)

    # TODO: Remove this once the team activity page is updated
    def get_old_message(self, user=None):
        return self.type_obj.get_old_message(self, user)

    def get_action_name(self):
        return self.type_obj.get_action_name()

    def get_url(self):
        """Get the URL for URL-related actions."""
        if self.type_obj.related_model is URLEdit:
            url_edit = self.get_related_obj()
            return url_edit.new_url if url_edit.new_url else url_edit.old_url
        else:
            return None

    def get_related_obj(self):
        if not hasattr(self, '_related_obj_cache'):
            self._related_obj_cache = self.type_obj.get_related_obj(
                self.related_obj_id)
        return self._related_obj_cache
