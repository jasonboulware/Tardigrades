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
import logging
from datetime import datetime

from django.conf import settings
from django.db.models import Sum, Q
from django.utils import translation
from django.utils.translation import ugettext as _

from subtitles import models as new_models
from teams.models import Task, Workflow, Team, BillingRecord
from teams.moderation_const import APPROVED, UNMODERATED, WAITING_MODERATION
from teams.permissions import (
    can_create_and_edit_subtitles, can_create_and_edit_translations,
    can_publish_edits_immediately, can_review, can_approve, can_add_version,
)
from teams.signals import (
    api_language_new, api_language_edited, api_video_edited
)
from utils import send_templated_email
from utils.forms import flatten_errorlists
from utils.subtitles import create_new_subtitles
from utils.translation import get_user_languages_from_request
from videos import models
from videos.models import record_workflow_origin, Subtitle
from videos.tasks import (
    video_changed_tasks, subtitles_complete_changed
)
from widget import video_cache
from widget.base_rpc import BaseRpc
from widget.forms import  FinishReviewForm, FinishApproveForm
from widget.models import SubtitlingSession

from functools import partial
from subtitles import pipeline
from subtitles.models import ORIGIN_LEGACY_EDITOR
from babelsubs.storage import SubtitleSet, diff


yt_logger = logging.getLogger("youtube-ei-error")

ALL_LANGUAGES = settings.ALL_LANGUAGES
LANGUAGES_MAP = dict(ALL_LANGUAGES)

def get_general_settings(request):
    general_settings = {
        'writelock_expiration' : new_models.WRITELOCK_EXPIRATION,
        'embed_version': '',
        'languages': ALL_LANGUAGES,
        'metadata_languages': settings.METADATA_LANGUAGES
    }
    if request.user.is_authenticated():
        general_settings['username'] = request.user.username
    return general_settings

def add_general_settings(request, dict):
    dict.update(get_general_settings(request))

class Rpc(BaseRpc):
    # Logging
    def log_session(self, request,  log):
        send_templated_email(
            settings.WIDGET_LOG_EMAIL,
            'Subtitle save failure',
            'widget/session_log_email.txt',
            { 'log_pk': dialog_log.pk },
            fail_silently=False)
        return { 'response': 'ok' }

    def log_youtube_ei_failure(self, request, page_url):
        user_agent = request.META.get('HTTP_USER_AGENT', '(Unknown)')
        yt_logger.error(
            "Youtube ExternalInterface load failure",
            extra={
                'request': request,
                'data': {
                    'user_agent': user_agent,
                    'page_url': page_url }
                })
        return { 'response': 'ok' }


    # Widget
    def _check_visibility_policy_for_widget(self, request, video_id):
        """Return an error if the user cannot see the widget, None otherwise."""

        visibility_policy = video_cache.get_visibility_policies(video_id)

        if not visibility_policy.get("is_public", True):
            team = Team.objects.get(id=visibility_policy['team_id'])

            if not team.is_member(request.user):
                return {"error_msg": _("Video embedding disabled by owner")}

    def _get_video_urls_for_widget(self, video_url, video_id):
        """Return the video URLs, 'cleaned' video id, and error."""

        try:
            video_urls = video_cache.get_video_urls(video_id)
        except models.Video.DoesNotExist:
            video_cache.invalidate_video_id(video_url)

            try:
                video_id = video_cache.get_video_id(video_url)
            except Exception as e:
                return None, None, {"error_msg": unicode(e)}

            video_urls = video_cache.get_video_urls(video_id)

        return video_urls, video_id, None

    def _find_remote_autoplay_language(self, request):
        language = None
        if not request.user.is_authenticated() or request.user.preferred_language == '':
            language = translation.get_language_from_request(request)
        else:
            language = request.user.preferred_language
        return language if language != '' else None

    def _get_subtitles_for_widget(self, request, base_state, video_id, is_remote):
        # keeping both forms valid as backwards compatibility layer
        lang_code = base_state and base_state.get("language_code", base_state.get("language", None))

        if base_state is not None and lang_code is not None:
            lang_pk = base_state.get('language_pk', None)

            if lang_pk is  None:
                lang_pk = video_cache.pk_for_default_language(video_id, lang_code)

            return self._autoplay_subtitles(request.user, video_id, lang_pk,
                                            base_state.get('revision', None))
        else:
            if is_remote:
                autoplay_language = self._find_remote_autoplay_language(request)
                language_pk = video_cache.pk_for_default_language(video_id, autoplay_language)

                if autoplay_language is not None:
                    return self._autoplay_subtitles(request.user, video_id,
                                                    language_pk, None)

    def show_widget(self, request, video_url, is_remote, base_state=None, additional_video_urls=None):
        try:
            video_id = video_cache.get_video_id(video_url)
        except Exception as e:
            # for example, private youtube video or private widgets
            return {"error_msg": unicode(e)}

        if video_id is None:
            return None

        error = self._check_visibility_policy_for_widget(request, video_id)

        if error:
            return error

        video_urls, video_id, error = self._get_video_urls_for_widget(video_url, video_id)

        if error:
            return error

        resp = {
            'video_id' : video_id,
            'subtitles': None,
            'video_urls': video_urls,
            'is_moderated': video_cache.get_is_moderated(video_id),
            'filename': video_cache.get_download_filename(video_id),
        }

        if additional_video_urls is not None:
            for url in additional_video_urls:
                video_cache.associate_extra_url(url, video_id)

        add_general_settings(request, resp)

        if request.user.is_authenticated():
            resp['username'] = request.user.username

        resp['drop_down_contents'] = video_cache.get_video_languages(video_id)
        resp['my_languages'] = get_user_languages_from_request(request)
        resp['subtitles'] = self._get_subtitles_for_widget(request, base_state,
                                                           video_id, is_remote)
        return resp

    def track_subtitle_play(self, request, video_id):
        # NOTE: we used to use this method to track when subtitles were
        # played from amara or other sites, however it wasn't very useful
        # since most other sites din't use it.  So when we switched to the new
        # statistics system we just removed the functionality.

        return { 'response': 'ok' }

    # Start Dialog (aka "Subtitle Into" Dialog)
    def _get_blocked_languages(self, team_video, user):
        # This is yet another terrible hack for the tasks system.  I'm sorry.
        #
        # Normally the in-progress languages will be marked as disabled in the
        # language_summary call, but that doesn't happen for languages that
        # don't have SubtitleLanguage objects yet, i.e. ones that have a task
        # but haven't been started yet.
        #
        # This function returns a list of languages that should be disabled ON
        # TOP OF the already-disabled ones.
        #
        # Here's a kitten to cheer you up:
        #
        #                     ,_
        #            (\(\      \\
        #            /.. \      ||
        #            \Y_, '----.//
        #              )        /
        #              |   \_/  ;
        #               \\ |\`\ |
        #          jgs  ((_/(_(_/
        if team_video:
            tasks = team_video.task_set.incomplete()

            if user.is_authenticated():
                tasks = tasks.exclude(assignee=user)

            return list(tasks.values_list('language', flat=True))
        else:
            return []

    def fetch_start_dialog_contents(self, request, video_id):
        my_languages = get_user_languages_from_request(request)
        my_languages.extend([l[:l.find('-')] for l in my_languages if l.find('-') > -1])
        video = models.Video.objects.get(video_id=video_id)
        team_video = video.get_team_video()
        languages = (new_models.SubtitleLanguage.objects.having_public_versions()
                                                        .filter(video=video))
        video_languages = [language_summary(l, team_video, request.user) for l
                           in languages]

        original_language = video.primary_audio_language_code

        tv = video.get_team_video()
        writable_langs = list(tv.team.get_writable_langs()) if tv else []

        blocked_langs = self._get_blocked_languages(team_video, request.user)

        return {
            'my_languages': my_languages,
            'video_languages': video_languages,
            'original_language': original_language,
            'limit_languages': writable_langs,
            'is_moderated': video.is_moderated,
            'blocked_languages': blocked_langs
        }


    # Fetch Video ID and Settings
    def fetch_video_id_and_settings(self, request, video_id):
        is_original_language_subtitled = self._subtitle_count(video_id) > 0
        general_settings = {}
        add_general_settings(request, general_settings)

        return {
            'video_id': video_id,
            'is_original_language_subtitled': is_original_language_subtitled,
            'general_settings': general_settings
        }


    def get_timing_mode(self, language, user):
        """
        Decides if allows forking. Criteria:
        - hard coded ted teams can't fork, ever
        - Non team videos, can fork, always
        - For team videos, the user must have permission to subtitle
        (not only translate)
        """
        team_video = language.video.get_team_video()
        _TED_TEAMS = ['ted', 'ted-transcribe']
        if team_video and team_video.team.slug.lower() in _TED_TEAMS:
            return 'off'
        elif team_video and not can_create_and_edit_subtitles(user, team_video, language):
            return 'off'
        else:
            return 'on'


    # Start Editing
    def _check_team_video_locking(self, user, video_id, language_code):
        """Check whether the a team prevents the user from editing the subs.

        Returns a dict appropriate for sending back if the user should be
        prevented from editing them, or None if the user can safely edit.

        """
        video = models.Video.objects.get(video_id=video_id)
        check_result = can_add_version(user, video, language_code)
        if check_result:
            return None
        else:
            return {
                "can_edit": False,
                "locked_by": check_result.locked_by,
                "message": check_result.message
            }

    def _get_version_to_edit(self, language, session):
        """Return a version (and other info) that should be edited.

        When subtitles are going to be created or edited for a given language,
        we need to have a "base" version to work with.  This function returns
        this base version along with its number and a flag specifying whether it
        is an edit (as opposed to a brand new set of subtitles).

        """
        version_for_subs = language.get_tip(public=False)

        if not version_for_subs:
            version_for_subs = None
            version_number = 0
        else:
            version_number = version_for_subs.version_number + 1

        return version_for_subs, version_number


    def start_editing(self, request, video_id, language_code,
                      subtitle_language_pk=None, base_language_code=None,
                      original_language_code=None, mode=None):
        """Called by subtitling widget when subtitling or translation is to commence on a video.

        Does a lot of things, some of which should probably be split out into
        other functions.

        """

        # TODO: remove whenever blank SubtitleLanguages become illegal.

        # Find the subtitle language we'll be editing (if available).
        language, locked = self._get_language_for_editing(
            request, video_id, language_code, subtitle_language_pk, base_language_code)

        if locked:
            return locked

        version = language.get_tip(public=False)

        # Ensure that the user is not blocked from editing this video by team
        # permissions.
        locked = self._check_team_video_locking(
            request.user, video_id, language_code)
        if locked:
            return locked

        # just lock the video *after* we verify if team moderation happened
        language.writelock(request.user)
        language.save()

        # Create the subtitling session and subtitle version for these edits.

        # we determine that a it's a translation if:
        # - the front end specifically said to translate from (base_language_code)
        # - The language has another source in it's lineage and it is not marked as forking
        translated_from_code  = None
        translated_from = None

        if base_language_code:
            translated_from_code = base_language_code
        elif language.is_forked == False:
            translated_from_code = language.get_translation_source_language_code()

        if translated_from_code:
            translated_from = language.video.subtitle_language(translated_from_code)

        session = self._make_subtitling_session(request, language, translated_from_code, video_id)
        version_for_subs, version_number = self._get_version_to_edit(language, session)

        args = {'session': session}

        if version_for_subs:
            args['version'] = version_for_subs
            session.parent = version_for_subs
            session.save()
        else:
            args['language'] = language

        subtitles = self._subtitles_dict(**args)
        # this is basically how it worked before. don't ask.
        subtitles['forked'] = base_language_code is None

        return_dict = { "can_edit": True,
                        "session_pk": session.pk,
                        "timing_mode": self.get_timing_mode(language, request.user),
                        "subtitles": subtitles }

        # If this is a translation, include the subtitles it's based on in the response.
        if translated_from:
            version = translated_from.get_tip(public=True)

            if not version:
                return { "can_edit": False, "locked_by": "", "message": "You cannot translate from a version that is incomplete" }

            original_subtitles = self._subtitles_dict(version=version)
            return_dict['original_subtitles'] = original_subtitles

        # If we know the original language code for this video, make sure it's
        # saved and there's a SubtitleLanguage for it in the database.
        #
        # Remember: the "original language" is the language of the video, NOT
        # the language these subs are a translation of (if any).
        if original_language_code:
            self._save_original_language(video_id, original_language_code)

        # Writelock this language for this video before we successfully return.
        video_cache.writelock_add_lang(video_id, language.language_code)

        return return_dict


    # Resume Editing
    def resume_editing(self, request, session_pk):
        try:
            session = SubtitlingSession.objects.get(pk=session_pk)
        except SubtitlingSession.DoesNotExist:
            return {'response': 'cannot_resume'}

        language = session.language
        error = self._check_team_video_locking(request.user, session.video.video_id, language.language_code)

        if error:
            return {'response': 'cannot_resume'}

        if language.can_writelock(request.user) and \
                session.parent_version == language.version():

            language.writelock(request.user)

            version_for_subs, version_number = self._get_version_to_edit(language, session)

            args = {'session': session}

            if version_for_subs is None:
                args['language'] = language
            else:
                args['version'] = version_for_subs

            subtitles = self._subtitles_dict(**args)

            return_dict = { "response": "ok",
                            "can_edit" : True,
                            "session_pk" : session.pk,
                            "timing_mode": self.get_timing_mode(session.language, request.user),
                            "subtitles" : subtitles }

            if session.base_language:
                return_dict['original_subtitles'] = \
                    self._subtitles_dict(version=session.base_language.get_tip())

            return return_dict
        else:
            return { 'response': 'cannot_resume' }


    # Locking
    def release_lock(self, request, session_pk):
        language = SubtitlingSession.objects.get(pk=session_pk).language
        if language.can_writelock(request.user):
            language.release_writelock()
            language.save()
            video_cache.writelocked_langs_clear(language.video.video_id)
        return { "response": "ok" }

    def regain_lock(self, request, session_pk):
        language = SubtitlingSession.objects.get(pk=session_pk).language
        if not language.can_writelock(request.user):
            return { 'response': 'unlockable' }
        else:
            language.writelock(request.user)
            video_cache.writelock_add_lang(
                language.video.video_id, language.language_code)
            return { 'response': 'ok' }

    # Permissions
    def can_user_edit_video(self, request, video_id):
        """Return a dictionary of information about what the user can do with this video.

        The response will contain can_subtitle and can_translate attributes.

        """
        video = models.Video.objects.get(video_id=video_id)
        team_video = video.get_team_video()

        if not team_video:
            can_subtitle = True
            can_translate = True
        else:
            can_subtitle = can_create_and_edit_subtitles(request.user, team_video)
            can_translate = can_create_and_edit_translations(request.user, team_video)

        return { 'response': 'ok',
                 'can_subtitle': can_subtitle,
                 'can_translate': can_translate, }


    # Finishing and Saving
    def _get_user_message_for_save(self, user, language, is_complete):
        """Return the message that should be sent to the user regarding this save.

        This may be a message saying that the save was successful, or an error message.

        The message displayed to the user  has a complex requirement / outcomes
        1) Subs will go live in a moment. Works for unmoderated subs and for D and H
        D. Transcript, post-publish edit by moderator with the power to approve. Will go live immediately.
        H. Translation, post-publish edit by moderator with the power to approve. Will go live immediately.
        2) Subs must be completed before being submitted to moderators. Works for A and E
        A. Transcript, incomplete (checkbox not ticked). Must be completed before being submitted to moderators.
        E. Translation, incomplete (some lines missing). Must be completed before being submitted to moderators.
        3) Subs will be submitted for review/approval. Works for B, C, F, and G
        B. Transcript, complete (checkbox ticked). Will be submitted to moderators promptly for approval or rejection.
        C. Transcript, post-publish edit by contributor. Will be submitted to moderators promptly for approval or rejection.
        F. Translation, complete (all the lines filled). Will be submitted to moderators promptly for approval or rejection.
        G. Translation, post-publish edit by contributor. Will be submitted to moderators promptly for approval or rejection.

        TODO: Localize this?

        """
        message_will_be_live_soon = "Your changes have been saved. It may take a moment for your subtitles to appear."
        message_will_be_submited = ("This video is moderated by %s."
                                    "Your changes will be reviewed by the "
                                    "team's moderators.")
        message_incomplete = ("These subtitles are incomplete. "
                              "They will not be submitted for publishing "
                              "until they've been completed.")

        under_moderation = language.video.is_moderated

        _user_can_publish =  True
        team_video = language.video.get_team_video()
        if under_moderation and team_video:
            # videos are only supposed to have one team video
            _user_can_publish = can_publish_edits_immediately(team_video, user, language.language_code)

        # this is case 1
        if under_moderation and not _user_can_publish:
            if is_complete:
                # case 3
                return message_will_be_submited % team_video.team.name
            else:
                # case 2
                return message_incomplete
        else:
            return message_will_be_live_soon

    def _save_tasks_for_save(self, request, save_for_later, language,
                             new_version, is_complete, task_id, task_type,
                             task_notes, task_approved):
        """Handle any outstanding tasks for this save.  May return an error.

        save_for_later is the most important argument here.  It determines
        whether any tasks will actually be completed.

        """

        team_video = language.video.get_team_video()

        if not save_for_later:
            # If we've just saved a completed subtitle language, we may need to
            # complete a subtitle or translation task.
            if is_complete:
                if team_video:
                    tasks = team_video.task_set.incomplete().filter(
                        type__in=(Task.TYPE_IDS['Subtitle'],
                                Task.TYPE_IDS['Translate']),
                        language=language.language_code
                    )
                    for task in tasks:
                        task.complete()

        # If the user is specifically performing a review/approve task we should
        # handle it.
        if task_id:
            if task_type == 'review':
                handle = self._save_review
            elif task_type == 'approve':
                handle = self._save_approve

            error = handle(request, save_for_later, task_id, task_notes,
                           task_approved, new_version=new_version)
            if error:
                return error

    def _get_new_version_for_save(self, subtitles, language, session, user, new_title, new_description, new_metadata, save_for_later=None):
        """Return a new subtitle version for this save, or None if not needed."""

        new_version = None
        previous_version = language.get_tip(public=False)

        if previous_version:
            title_changed = (new_title is not None
                             and new_title != previous_version.title)
            desc_changed = (new_description is not None
                            and new_description != previous_version.description)
            metadata_changed = (new_metadata is not None
                                and new_metadata != previous_version.get_metadata())
        else:
            title_changed = new_title is not None
            desc_changed = new_description is not None
            metadata_changed = new_metadata is not None

        subtitle_set = None
        subs_length = 0
        if isinstance(subtitles, basestring):
            subtitle_set = SubtitleSet(language.language_code, subtitles)
        elif isinstance(subtitles, SubtitleSet):
            subtitle_set = subtitles
        if subtitle_set:
            subs_length = len(subtitle_set)

        # subtitles have changed if only one of the version is empty
        # or if the versions themselves differ
        if not previous_version and not subtitle_set:
            subtitles_changed = False
        elif not previous_version or not subtitle_set:
            subtitles_changed = True
        else:
            subtitles_changed = diff(previous_version.get_subtitles(), subtitle_set)['changed']

        should_create_new_version = (
            subtitles_changed or title_changed or desc_changed or
            metadata_changed)

        if should_create_new_version:
            new_version, should_create_task = self._create_version(
                session.language, user,
                new_title=new_title,
                new_description=new_description,
                new_metadata=new_metadata,
                subtitles=subtitles,
                session=session)

            incomplete = not new_version.is_synced() or save_for_later

            # Record the origin of this set of subtitles.
            #
            # We need to record it *before* creating review/approve tasks (if
            # any) because that means these subs were from a post-publish edit
            # or something similar.  If we record the origin after creating the
            # review task it'll be marked as originating from review, which
            # isn't right because these subs had to come from something else.
            #
            # :(
            record_workflow_origin(new_version, new_version.video.get_team_video())

            if (not incomplete) and should_create_task:
                self._create_review_or_approve_task(new_version)

        return new_version

    def _update_language_attributes_for_save(self, language, completed, session, forked):
        """Update the attributes of the language as necessary and save it.

        Will also send the appropriate API notification if needed.

        """
        must_trigger_api_language_edited = False

        if completed is not None:
            if language.subtitles_complete != completed:
                must_trigger_api_language_edited = True
            language.subtitles_complete = completed

        # this means all 'original languages' will be marked as forks
        # but this is cool for now because all those languages should
        # be shown on the transcribe dialog. if there's a base language,
        # that means we should always show the translate dialog.
        if forked or session.base_language is None:
            language.is_forked = True

        language.save()
        if forked:
            pipeline._fork_dependents(language)

        if must_trigger_api_language_edited:
            language.video.save()
            api_language_edited.send(language)

    def save_finished(self, request, user, session, subtitles, new_title=None,
                      completed=None, forked=False, new_description=None,
                      new_metadata=None, task_id=None, task_notes=None,
                      task_approved=None, task_type=None,
                      save_for_later=None):
        # TODO: lock all this in a transaction please!

        language = session.language

        new_version = self._get_new_version_for_save(
            subtitles, language, session, user, new_title,
            new_description, new_metadata, save_for_later)

        language.release_writelock()

        # do this here, before _update_language_a... changes it ;)
        complete_changed = bool(completed ) != language.subtitles_complete
        self._update_language_attributes_for_save(language, completed, session, forked)

        if new_version:
            video_changed_tasks.delay(language.video.id, new_version.id)
        else:
            video_changed_tasks.delay(language.video.id)
            api_video_edited.send(language.video)
            if completed and complete_changed:
                # not a new version, but if this just got marked as complete
                # we want to push this to the third parties:
                subtitles_complete_changed(language.pk)

        user_message = self._get_user_message_for_save(user, language, language.subtitles_complete)

        error = self._save_tasks_for_save(
                request, save_for_later, language, new_version, language.subtitles_complete,
                task_id, task_type, task_notes, task_approved)

        if error:
            return error

        return { 'response': 'ok', 'user_message': user_message }

    def finished_subtitles(self, request, session_pk, subtitles=None,
                           new_title=None, completed=None, forked=False,
                           throw_exception=False, new_description=None,
                           new_metadata=None,
                           task_id=None, task_notes=None, task_approved=None,
                           task_type=None, save_for_later=None):
        """Called when a user has finished a set of subtitles and they should be saved.

        TODO: Rename this to something verby, like "finish_subtitles".

        """
        session = SubtitlingSession.objects.get(pk=session_pk)

        if not request.user.is_authenticated():
            return { 'response': 'not_logged_in' }
        if not session.language.can_writelock(request.user):
            return { "response" : "unlockable" }
        if not session.matches_request(request):
            return { "response" : "does not match request" }

        if throw_exception:
            raise Exception('purposeful exception for testing')

        return self.save_finished(
            request, request.user, session, subtitles, new_title, completed,
            forked, new_description, new_metadata, task_id, task_notes,
            task_approved, task_type, save_for_later)

    def _create_review_or_approve_task(self, subtitle_version):
        team_video = subtitle_version.video.get_team_video()
        lang = subtitle_version.subtitle_language.language_code
        workflow = Workflow.get_for_team_video(team_video)

        if workflow.review_allowed:
            type = Task.TYPE_IDS['Review']
            can_do = partial(can_review, allow_own=True)
        elif workflow.approve_allowed:
            type = Task.TYPE_IDS['Approve']
            can_do = can_approve
        else:
            return None

        # TODO: Dedupe this and Task._find_previous_assignee

        # Find the assignee.
        #
        # For now, we'll assign the review/approval task to whomever did
        # it last time (if it was indeed done), but only if they're
        # still eligible to perform it now.
        last_task = team_video.task_set.complete().filter(
            language=lang, type=type
        ).order_by('-completed')[:1]

        assignee = None
        if last_task:
            candidate = last_task[0].assignee
            if candidate and can_do(team_video, candidate, lang):
                assignee = candidate

        task = Task(team=team_video.team, team_video=team_video,
                    assignee=assignee, language=lang, type=type)

        task.set_expiration()
        task.new_subtitle_version = subtitle_version

        if task.get_type_display() in ['Review', 'Approve']:
            task.new_review_base_version = subtitle_version

        task.save()

    def _moderate_language(self, language, user):
        """Return the right visibility for a version based on the given session.

        Also may possibly return a Task object that needs to be saved once the
        subtitle_version is ready.

        Also perform any ancillary tasks that are appropriate, assuming the
        version actually gets created later.

        Also :(

        """
        team_video = language.video.get_team_video()

        if not team_video:
            return 'public', False

        team = team_video.team
        workflow = team.get_workflow()

        # If there are any open team tasks for this video/language, it needs to
        # be kept under moderation.
        tasks = team_video.task_set.incomplete().filter(
                Q(language=language.language_code)
              | Q(type=Task.TYPE_IDS['Subtitle'])
        )

        if tasks:
            for task in tasks:
                if task.type == Task.TYPE_IDS['Subtitle']:
                    if not task.language:
                        task.language = language.language_code
                        task.save()

            return ('public', False) if not team.workflow_enabled else ('private', False)

        if not workflow.requires_tasks:
            return 'public', False
        elif language.old_has_version:
            # If there are already active subtitles for this language, we're
            # dealing with an edit.
            if can_publish_edits_immediately(team_video, user, language.language_code):
                # The user may have the rights to immediately publish edits to
                # subtitles.  If that's the case we mark them as approved and
                # don't need a task.
                return 'public', False
            else:
                # Otherwise it's an edit that needs to be reviewed/approved.
                return 'private', True
        else:
            # Otherwise we're dealing with a new set of subtitles for this
            # language.
            return 'private', True

    def _create_version(self, language, user=None, new_title=None, new_description=None, new_metadata=None, subtitles=None, session=None):
        latest_version = language.get_tip(public=False)

        visibility, should_create_task = self._moderate_language(language, user)

        kwargs = dict(visibility=visibility)

        # it's a title/description update
        # we can do this better btw
        # TODO: improve-me plz
        if (new_title or new_description) and not subtitles and latest_version:
            subtitles = latest_version.get_subtitles()

        if user is not None:
            kwargs['author'] = user

        if new_title is not None:
            kwargs['title'] = new_title
        elif latest_version:
            kwargs['title'] = latest_version.title
        else:
            kwargs['title'] = language.video.title

        if new_description is not None:
            kwargs['description'] = new_description
        elif latest_version:
            kwargs['description'] = latest_version.description
        else:
            kwargs['description'] = language.video.description
        kwargs['metadata'] = new_metadata

        if subtitles is None:
            subtitles = []

        kwargs['video'] = language.video
        kwargs['language_code'] = language.language_code
        kwargs['subtitles'] = subtitles
        kwargs['origin'] = ORIGIN_LEGACY_EDITOR

        if session and session.base_language:
            base_language_code = session.base_language.language_code
            base_subtitle_language = language.video.subtitle_language(base_language_code)

            if base_language_code:
                kwargs['parents'] = [base_subtitle_language.get_tip(full=True)]

        version = pipeline.add_subtitles(**kwargs)

        return version, should_create_task

    def fetch_subtitles(self, request, video_id, language_pk):
        cache = video_cache.get_subtitles_dict(
            video_id, language_pk, None,
            lambda version: self._subtitles_dict(version=version))
        return cache

    def get_widget_info(self, request):
        return {
            'all_videos': models.Video.objects.count(),
            'videos_with_captions': models.Video.objects.exclude(subtitlelanguage=None).count(),
            'translations_count': models.SubtitleLanguage.objects.filter(is_original=False).count()
        }

    def _make_subtitling_session(self, request, language, base_language_code, video_id, version=None):
        try:
            base_language = new_models.SubtitleLanguage.objects.get(video__video_id=video_id,
                                                            language_code=base_language_code)
        except new_models.SubtitleLanguage.DoesNotExist:
            base_language = None

        session = SubtitlingSession(
            language=language,
            base_language=base_language,
            parent_version=version)

        if request.user.is_authenticated():
            session.user = request.user

        session.save()
        return session

    # Review
    def fetch_review_data(self, request, task_id):
        task = Task.objects.get(pk=task_id)
        return {'response': 'ok', 'body': task.body}

    def _save_review(self, request, save_for_later, task_id=None, body=None,
                     approved=None, new_version=None):
        """
        If the task performer has edited this version, then we need to
        set the task's version to the new one that he has edited.
        """
        data = {'task': task_id, 'body': body, 'approved': approved}

        form = FinishReviewForm(request, data)

        if form.is_valid():
            task = form.cleaned_data['task']
            task.body = form.cleaned_data['body']
            task.approved = form.cleaned_data['approved']

            # If there is a new version, update the task's version.
            if new_version:
                task.new_subtitle_version = new_version

            task.save()

            if not save_for_later:
                if task.approved in Task.APPROVED_FINISHED_IDS:
                    task.complete()

            task.new_subtitle_version.subtitle_language.release_writelock()
            task.new_subtitle_version.subtitle_language.followers.add(request.user)

            video_changed_tasks.delay(task.team_video.video_id)
        else:
            return {'error_msg': _(u'\n'.join(flatten_errorlists(form.errors)))}


    # Approval
    def fetch_approve_data(self, request, task_id):
        task = Task.objects.get(pk=task_id)
        return {'response': 'ok', 'body': task.body}

    def _save_approve(self, request, save_for_later, task_id=None, body=None,
                      approved=None, new_version=None):
        """
        If the task performer has edited this version, then we need to
        set the task's version to the new one that he has edited.
        """
        data = {'task': task_id, 'body': body, 'approved': approved}

        form = FinishApproveForm(request, data)

        if form.is_valid():
            task = form.cleaned_data['task']
            task.body = form.cleaned_data['body']
            task.approved = form.cleaned_data['approved']

            # If there is a new version, update the task's version.
            if new_version:
                task.new_subtitle_version = new_version

            task.save()

            if not save_for_later:
                if task.approved in Task.APPROVED_FINISHED_IDS:
                    task.complete()

            task.new_subtitle_version.subtitle_language.release_writelock()

            video_changed_tasks.delay(task.team_video.video_id)
        else:
            return {'error_msg': _(u'\n'.join(flatten_errorlists(form.errors)))}


    def _find_base_language(self, base_language):
        if base_language:
            video = base_language.video
            if base_language.is_original or base_language.is_forked:
                return base_language
            else:
                if base_language.standard_language:
                    return base_language.standard_language
                else:
                    return video.subtitle_language()
        else:
            return None

    def _needs_new_sub_language(self, language, base_language):
        if language.standard_language and not base_language:
            # forking existing
            return False
        elif language.is_forked and base_language:
            return True
        else:
            return language.standard_language != base_language

    def _get_language_for_editing(self, request, video_id, language_code,
                                  subtitle_language_pk=None, base_language_code=None):
        """Return the subtitle language to edit or a lock response."""

        video = models.Video.objects.get(video_id=video_id)

        editable = False
        created  = False

        if subtitle_language_pk is not None:
            language = new_models.SubtitleLanguage.objects.get(pk=subtitle_language_pk)
        else:
            # we can tell which language it is from the language code
            candidates = video.newsubtitlelanguage_set.filter(language_code=language_code)
            if not candidates.exists():
                # no languages with the language code, we must create one
                language = new_models.SubtitleLanguage(
                    video=video, language_code=language_code,
                    created=datetime.now())

                language.is_forked = not base_language_code and video.newsubtitlelanguage_set.exists()

                language.save()
                created = True
            else:
                for candidate in candidates:
                    if base_language_code == candidate.get_translation_source_language_code():
                        # base language matches, break me
                        language = candidate
                        break
                # if we reached this point, we have no good matches
                language = candidates[0]

        editable = language.can_writelock(request.user)

        if editable:
            if created:
                api_language_new.send(language)
            return language, None
        else:
            return None, { "can_edit": False,
                           "locked_by": unicode(language.writelock_owner) }

    def _save_original_language(self, video_id, language_code):
        video = models.Video.objects.get(video_id=video_id)

        if not video.primary_audio_language_code:
            video.primary_audio_language_code = language_code
            video.save()


    def _autoplay_subtitles(self, user, video_id, language_pk, version_number):
        cache =  video_cache.get_subtitles_dict(video_id, language_pk,
                                                version_number,
                                                lambda version: self._subtitles_dict(version=version))

        if cache and cache.get("language", None) is not None:
            cache['language_code'] = cache['language'].language
            cache['language_pk'] = cache['language'].pk

        return cache

    def _subtitles_dict(self, version=None, language=None, session=None):
        if not language and not version:
            raise ValueError("You need to specify either language or version")

        latest_version = language.get_tip() if language else None
        is_latest = False

        if not version and not latest_version:
            version_number = 0
            language_code = language.language_code
            subtitles = create_new_subtitles(language_code).to_xml()
            is_latest = True
            metadata = language.get_metadata()
            for key in language.video.get_metadata():
                if key not in metadata:
                    metadata[key] = ''
        else:
            version = version or latest_version
            version_number = version.version_number
            subtitles = version.get_subtitles().to_xml()
            language = version.subtitle_language
            language_code = language.language_code
            metadata = version.get_metadata()
            for key in version.video.get_metadata():
                if key not in metadata:
                    metadata[key] = ''

        if latest_version is None or version_number >= latest_version.version_number:
            is_latest = True

        if session:
            translated_from = session.base_language
        else:
           translated_from = language.get_translation_source_language()

        return self._make_subtitles_dict(
            subtitles,
            language,
            language.pk,
            language.is_primary_audio_language(),
            None if translated_from is not None else language.subtitles_complete,
            version_number,
            is_latest,
            translated_from,
            language.get_title(public=False),
            language.get_description(public=False),
            language.is_rtl(),
            language.video.is_moderated,
            metadata,
        )

def language_summary(language, team_video=-1, user=None):
    """Return a dictionary of info about the given SubtitleLanguage.

    The team video can be given to avoid an extra database lookup.

    """
    if team_video == -1:
        team_video = language.video.get_team_video()

    translation_source = language.get_translation_source_language()
    is_translation = bool(translation_source)
    summary = {
        'pk': language.pk,
        'language': language.language_code,
        'dependent': is_translation,
        'subtitle_count': language.get_subtitle_count(),
        'in_progress': language.is_writelocked,
        'disabled_from': False }

    if team_video:
        tasks = team_video.task_set.incomplete().filter(language=language.language_code)
        if tasks:
            task = tasks[0]
            summary['disabled_to'] = user and user != task.assignee

    latest_version = language.get_tip()

    if latest_version and language.is_complete_and_synced() and 'disabled_to' not in summary:
        # Languages with existing subtitles cannot be selected as a "to"
        # language in the "add new translation" dialog.  If you want to work on
        # that language, select it and hit "Improve these Subtitles" instead.
        summary['disabled_to'] = True
    elif not latest_version or not latest_version.has_subtitles:
        # Languages with *no* existing subtitles cannot be selected as a "from"
        # language in the "add new translation" dialog.  There's nothing to work
        # from!
        summary['disabled_from'] = True


    if is_translation:
        summary['standard_pk'] = translation_source.pk
        summary['translated_from'] = translation_source.language_code
    summary['is_complete'] = language.subtitles_complete
    summary['is_public'] = True if language.get_public_tip() else False

    return summary
