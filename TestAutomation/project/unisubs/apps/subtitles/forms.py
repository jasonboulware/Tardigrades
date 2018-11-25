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

import chardet
from itertools import izip

import babelsubs
from django import forms
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext

from activity.models import ActivityRecord
from externalsites.models import SyncHistory
from subtitles import pipeline
from subtitles.shims import is_dependent
from subtitles.models import ORIGIN_UPLOAD, SubtitleLanguage
from subtitles.permissions import user_can_change_subtitle_language
from teams.models import Task
from teams.permissions import (
    can_perform_task, can_create_and_edit_subtitles,
    can_create_and_edit_translations
)
from videos.tasks import video_changed_tasks
from ui.forms import AmaraClearableFileInput, LanguageField
from utils.text import fmt
from utils.subtitles import load_subtitles
from utils.translation import (ALL_LANGUAGE_CHOICES,
                               get_language_choices,
                               get_language_label)


SUBTITLE_FILESIZE_LIMIT_KB = 512
SUBTITLE_FILE_FORMATS = babelsubs.get_available_formats()

class SubtitlesUploadForm(forms.Form):
    draft = forms.FileField(widget=AmaraClearableFileInput, required=True)
    complete = forms.BooleanField(initial=False, required=False)

    language_code = forms.ChoiceField(required=True,
                                      choices=())
    primary_audio_language_code = forms.ChoiceField(required=False,
                                                    choices=())
    from_language_code = forms.ChoiceField(required=False,
                                           choices=(),
                                           initial='')

    def __init__(self, user, video, allow_transcription=True, *args, **kwargs):
        allow_all_languages = kwargs.pop('allow_all_languages', False)
        self.video = video
        self.user = user
        self._sl_created = False

        super(SubtitlesUploadForm, self).__init__(*args, **kwargs)

        if allow_all_languages:
            all_languages = ALL_LANGUAGE_CHOICES
        else:
            all_languages = get_language_choices(with_empty=True)
        self.fields['language_code'].choices = all_languages
        self.fields['primary_audio_language_code'].choices = all_languages

        choices = [
            (language_code, get_language_label(language_code))
            for language_code in video.languages_with_versions()
        ]
        if allow_transcription:
            choices.append(('', 'None (Direct from Video)'))

        self.fields['from_language_code'].choices = choices


    # Validation for various restrictions on subtitle uploads.
    def _verify_not_writelocked(self, subtitle_language):
        writelocked = (subtitle_language.is_writelocked and
                       subtitle_language.writelock_owner != self.user)
        if writelocked:
            raise forms.ValidationError(_(
                u"Sorry, we can't upload your subtitles because work on "
                u"this language is already in progress."))

    def _verify_no_translation_conflict(self, subtitle_language,
                                        from_language_code):
        existing_from_language = subtitle_language.get_translation_source_language()
        existing_from_language_code = (
            existing_from_language and existing_from_language.language_code) or ''

        # If the user said this is a translation, but the language already
        # exists and *isn't* a translation, fail.
        if from_language_code:
            language_is_not_a_translation = (not existing_from_language_code)
            if language_is_not_a_translation and subtitle_language.get_tip():
                raise forms.ValidationError(_(
                    u"The language already exists and is not a translation."))
            # If it's marked as a translation from a different language, don't
            # allow that until our UI can handle showing different reference
            # languages
            elif existing_from_language_code and existing_from_language_code != from_language_code:
                raise forms.ValidationError(fmt(
                    _(u"The language already exists as a "
                      u"translation from %(source_lang)s."),
                    source_lang=existing_from_language.get_language_code_display()))

    def _verify_no_blocking_subtitle_translate_tasks(self, team_video,
                                                     language_code):
        tasks = list(
            team_video.task_set.incomplete_subtitle_or_translate().filter(
                language__in=[language_code, '']
            )
        )[:1]

        if tasks:
            task = tasks[0]

            # If this language is already assigned to someone else, fail.
            if (task.assignee and task.assignee != self.user):
                raise forms.ValidationError(_(
                    u"Sorry, we can't upload your subtitles because another "
                    u"user is already assigned to this language."))

            # If this language is unassigned, and the user can't assign herself
            # to it, fail.
            if (not task.assignee and not can_perform_task(self.user, task)):
                raise forms.ValidationError(_(
                    u"Sorry, we can't upload your subtitles because you do not "
                    u"have permission to claim this language."))

    def _verify_no_blocking_review_approve_tasks(self, team_video,
                                                 language_code):
        tasks = team_video.task_set.incomplete_review_or_approve().filter(
            language=language_code
        ).exclude(assignee=self.user).exclude(assignee__isnull=True)

        if tasks.exists():
            raise forms.ValidationError(_(
                u"Sorry, we can't upload your subtitles because a draft for "
                u"this language is already in moderation."))

    def _verify_translation_subtitle_counts(self, from_language_code):
        if from_language_code and hasattr(self, '_parsed_subtitles'):
            from_count = len(self.from_sv.get_subtitles())
            current_count = len(self._parsed_subtitles.get_subtitles())

            if current_count > from_count:
                raise forms.ValidationError(fmt(
                    _(u"Sorry, we couldn't upload your file because "
                      u"the number of lines in your translation "
                      u"(%(translation_lines)s) doesn't match the "
                      u"original (%(source_lines)s)."),
                    translation_lines=current_count,
                    source_lines=from_count))

    def clean_draft(self):
        data = self.cleaned_data['draft']

        if data.size > SUBTITLE_FILESIZE_LIMIT_KB * 1024:
            raise forms.ValidationError(fmt(
                _(u'File size must be less than %(size)s kb.'),
                size=SUBTITLE_FILESIZE_LIMIT_KB))

        parts = data.name.rsplit('.', 1)
        self.extension = parts[-1].lower()
        if self.extension not in babelsubs.get_available_formats():
            raise forms.ValidationError(fmt(_(
                u'Unsupported format. Please upload one of '
                u'the following: %(formats)s'),
                formats=", ".join(SUBTITLE_FILE_FORMATS)))

        text = data.read()
        encoding = chardet.detect(text)['encoding']

        if not encoding:
            raise forms.ValidationError(_(u'Can not detect file encoding'))

        # For xml based formats we can't just convert to unicode, as the parser
        # will complain that the string encoding doesn't match the encoding
        # declaration in the xml file if it's not utf-8.
        is_xml = self.extension in ('dfxp', 'ttml', 'xml')
        decoded = force_unicode(text, encoding) if not is_xml else text

        try:
            # we don't know the language code yet, since we are early in the
            # clean process.  Set it to blank for now and we'll set it to the
            # correct value in save()
            self._parsed_subtitles = load_subtitles('', decoded,
                                                    self.extension)
        except TypeError, e:
            raise forms.ValidationError(e)
        except ValueError, e:
            raise forms.ValidationError(e)

        data.seek(0)

        return data

    def clean(self):
        from_language_code = self.cleaned_data.get('from_language_code')
        language_code = self.cleaned_data['language_code']
        subtitle_language = self.video.subtitle_language(language_code)

        if from_language_code:
            # If this is a translation, we'll retrieve the source
            # language/version here so we can use it later.
            self.from_sl = self.video.subtitle_language(from_language_code)
            if self.from_sl is None:
                raise forms.ValidationError(fmt(
                    _(u'Invalid from language: %(language)s'),
                    language=get_language_label(from_language_code)))
            self.from_sv = self.from_sl.get_tip(public=True)
            if self.from_sv is None:
                raise forms.ValidationError(fmt(
                    _(u'%(language)s has no public versions'),
                    language=get_language_label(from_language_code)))
        else:
            self.from_sl = None
            self.from_sv = None

        # If this SubtitleLanguage already exists, we need to verify a few
        # things about it before we let the user upload a set of subtitles to
        # it.
        if subtitle_language:
            # Verify that it's not writelocked.
            self._verify_not_writelocked(subtitle_language)

            # Make sure there are no translation conflicts.  Basically, fail if
            # any of the following are true:
            #
            # 1. The user specified that this was a translation, but the
            #    existing SubtitleLanguage is *not* a translation.
            # 2. The user specified that this was a translation, and the
            #    existing language is a translation, but of a different language
            #    than the user gave.
            self._verify_no_translation_conflict(subtitle_language,
                                                 from_language_code)

        # If we are translating from another version, check that the number of
        # subtitles matches the source.
        self._verify_translation_subtitle_counts(from_language_code)

        workflow = self.video.get_workflow()

        if not workflow.user_can_edit_subtitles(self.user, language_code):
            raise forms.ValidationError(_(
                u"Sorry, we can't upload your subtitles because this "
                u"language is moderated."))

        # Videos that are part of a team have a few more restrictions.
        team_video = self.video.get_team_video()
        if team_video:
            # You can only upload to a language with a subtitle/translate task
            # open if that task is assigned to you, or if it's unassigned and
            # you can assign yourself.
            self._verify_no_blocking_subtitle_translate_tasks(team_video,
                                                              language_code)

            # You cannot upload at all to a language that has a review or
            # approve task open.
            self._verify_no_blocking_review_approve_tasks(team_video,
                                                          language_code)


        return self.cleaned_data


    def _find_title_description_metadata(self, language_code):
        """Find the title, description, and metadata that should be used.

        Uploads have no way to set the title, description, and metadata
        so just set them to the previous version's or the video's.

        """
        subtitle_language = self.video.subtitle_language(language_code)
        title, description = self.video.title, self.video.description
        metadata = self.video.get_metadata()
        from_previous_version = False
        if subtitle_language:
            previous_version = subtitle_language.get_tip()
            if previous_version:
                from_previous_version = True
                title = previous_version.title
                description = previous_version.description
                metadata = previous_version.get_metadata()

        return title, description, metadata, from_previous_version

    def _find_parents(self, from_language_code):
        """Find the parents that should be used for this upload.

        Until the new UI is in place we need to fake translations by setting
        parentage.

        """
        parents = []

        if from_language_code:
            from_language = self.video.subtitle_language(from_language_code)
            from_version = from_language.get_tip(full=True)
            parents = [from_version]

        return parents

    def _save_primary_audio_language_code(self):
        palc = self.cleaned_data['primary_audio_language_code']
        if palc:
            self.video.primary_audio_language_code = palc
            self.video.save()

    def save(self):
        # If the primary audio language code was given, we adjust it on the
        # video NOW, before saving the subtitles, so that the pipeline can take
        # it into account when determining task types.
        self._save_primary_audio_language_code()

        language_code = self.cleaned_data['language_code']
        from_language_code = self.cleaned_data['from_language_code']
        complete = self.cleaned_data['complete']


        subtitles = self._parsed_subtitles
        subtitles.set_language(language_code)
        if from_language_code:
            # If this is a translation, its subtitles should use the timing data
            # from the source.  We know that the source has at least as many
            # subtitles as the new version, so we can just match them up
            # first-come, first-serve.
            source_subtitles = self.from_sv.get_subtitles()
            i = 0
            # instead of translating to subtitle_items, we're updating the
            # dfxp elements in place. This guarantees no monkey business with
            # escaping / styling
            for old, new in izip(source_subtitles.subtitle_items(), subtitles.get_subtitles()):
                subtitles.update(i, from_ms=old.start_time, to_ms=old.end_time)
                i += 1
        else:
            # Otherwise we can just use the subtitles the user uploaded as-is.
            # No matter what, text files that aren't translations cannot be
            # complete because they don't have timing data.
            if self.extension == 'txt':
                complete = False

        # Only pre-populate those if team does not have
        # the setting
        get_title_description_metadata = True
        team_video = self.video.get_team_video()
        if team_video:
            for f in team_video.team.settings.features():
                if f.key_name == "enable_require_translated_metadata":
                    get_title_description_metadata = False
                    break

        title, description, metadata, previous_version = self._find_title_description_metadata(language_code)
        if not (get_title_description_metadata or previous_version):
            title, description, metadata = "", "", {}

        parents = self._find_parents(from_language_code)

        version = pipeline.add_subtitles(
            self.video, language_code, subtitles,
            title=title, description=description, author=self.user,
            parents=parents, committer=self.user, complete=complete,
            metadata=metadata, origin=ORIGIN_UPLOAD)

        # Handle forking SubtitleLanguages that were translations when
        # a standalone version is uploaded.
        #
        # For example: assume there is a French translation of English.
        # Uploading a "straight from video" version of French should fork it.
        sl = version.subtitle_language
        if not from_language_code and is_dependent(sl):
            sl.fork()

        # TODO: Pipeline this.
        video_changed_tasks.delay(sl.video_id, version.id)

        return version


    def get_errors(self):
        output = {}
        for key, value in self.errors.items():
            output[key] = '\n'.join([force_unicode(i) for i in value])
        return output

class SubtitlesForm(forms.Form):
    """Form that operates on a video's subtitles.

    This is the base class for forms on the video subtitles page.
    """
    def __init__(self, user, video, subtitle_language, subtitle_version, *args, **kwargs):
        super(SubtitlesForm, self).__init__(*args, **kwargs)

        self.user = user
        self.video = video
        self.subtitle_language = subtitle_language
        self.subtitle_version = subtitle_version
        self.language_code = subtitle_language.language_code
        self.setup_fields()

    def setup_fields(self):
        pass

    def check_permissions(self):
        """Check the user has permission to use the form."""
        raise NotImplementedError()

    def submit(self, request):
        """Handle form submission."""
        with transaction.atomic():
            if self.subtitle_language.is_writelocked:
                messages.error(request, _(u'Subtitles are currently being edited'))
                return
            self.do_submit(request)
        video_changed_tasks.delay(self.video.pk)

class DeleteSubtitlesForm(SubtitlesForm):
    VERIFY_STRING = _(u'Yes, I want to delete this language')
    verify = forms.CharField(label=_(u'Are you sure?'), required=False)

    def setup_fields(self):
        self.fields['verify'].help_text = fmt(
            ugettext(
                _(u'Type "%(words)s" if you are sure you wish to continue')),
            words=self.VERIFY_STRING)

    def bullets(self):
        workflow = self.video.get_workflow()
        return workflow.delete_subtitles_bullets(self.language_code)

    def check_permissions(self):
        workflow = self.video.get_workflow()
        return workflow.user_can_delete_subtitles(
            self.user, self.language_code)

    def clean_verify(self):
        if self.cleaned_data['verify'] != self.VERIFY_STRING:
            raise forms.ValidationError(self.fields['verify'].help_text)

    def clean(self):
        if not self.check_permissions():
            raise forms.ValidationError(
                ugettext(u'You do not have permission to delete the subtitles')
            )
        return self.cleaned_data

    def do_submit(self, request):
        self.subtitle_language.nuke_language()
        messages.success(request, _(u'Subtitles deleted'))

class ChangeSubtitleLanguageForm(SubtitlesForm):
    new_language = LanguageField(label=_(u'Subtitle Language'))

    def check_permissions(self):
        return user_can_change_subtitle_language(self.user, self.video)

    def clean(self):
        if not self.check_permissions():
            raise forms.ValidationError(
                ugettext(u'You do not have permission to change the subtitle language')
            )
        return self.cleaned_data

    def do_submit(self, request):
        old_language_code = self.subtitle_language.language_code
        try:
            self.subtitle_language.change_language_code(self.cleaned_data['new_language'])
            self.subtitle_language.video.clear_language_cache()
        except ValidationError:
            messages.error(request, ugettext(u'Invalid language code.'))
        except IntegrityError:
            messages.error(request, ugettext(u'Subtitles already exist for this language.'))
        else:
            ActivityRecord.objects.create_for_subtitle_language_changed(
                    self.user, self.subtitle_language, old_language_code)

class RollbackSubtitlesForm(SubtitlesForm):
    def check_permissions(self):
        workflow = self.video.get_workflow()
        return workflow.user_can_edit_subtitles(
            self.user, self.language_code)

    def do_submit(self, request):
        if self.subtitle_version.next_version():
            pipeline.rollback_to(
                self.video, self.language_code,
                version_number=self.subtitle_version.version_number,
                rollback_author=self.user)
            messages.success(request, ugettext(u'Rollback successful'))
        else:
            messages.error(request,
                           ugettext(u'Can not rollback to the last version'))

class ResyncSubtitlesForm(SubtitlesForm):
    def check_permissions(self):
        return True

    def do_submit(self, request):
        if SyncHistory.objects.force_retry_language_for_user(self.subtitle_language, self.user):
            messages.success(request, ugettext(u'Resync started, this may take a few minutes'))
        else:
            messages.error(request,
                           ugettext(u'Error while attempting to resync'))

class SubtitlesNotesForm(SubtitlesForm):
    body = forms.CharField(label='', required=True,
                           widget=forms.Textarea(attrs={
                               'placeholder': _("Post new note"),
                               'rows': 3,
                           }))

    def check_permissions(self):
        workflow = self.video.get_workflow()
        return workflow.user_can_post_notes(self.user, self.language_code)

    def do_submit(self, request):
        notes = self.video.get_workflow().get_editor_notes(self.user,
                                                           self.language_code)
        notes.post(self.user, self.cleaned_data['body'])
