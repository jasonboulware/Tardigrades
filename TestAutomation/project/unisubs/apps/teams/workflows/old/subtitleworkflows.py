# Amara, universalsubtitles.org
#
# Copyright (C) 2014 Participatory Culture Foundation
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

"""
SubtitleWorkflow classes for old-style teams
"""

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy

from localeurl.utils import universal_url
from messages.models import Message
from subtitles.signals import subtitles_published, subtitles_completed
from teams.models import Task, BillingRecord
from teams.permissions import can_add_version, can_assign_task
from teams.workflows.notes import TeamEditorNotes
from teams.workflows.subtitleworkflows import TeamSubtitlesWorkflow
from utils import send_templated_email
from utils import translation
from utils.text import fmt
from videos.tasks import video_changed_tasks
import subtitles.workflows

def _publish_subtitles_if_needed(subtitle_language, version):
    public_tip = subtitle_language.get_tip(public=True)
    if public_tip:
        subtitles_completed.send(subtitle_language)
        subtitles_published.send(subtitle_language, version=version)
        BillingRecord.objects.insert_record(public_tip)

def _complete_task(user, video, subtitle_language, saved_version, approved):
    team_video = video.get_team_video()
    task = (team_video.task_set
            .incomplete_review_or_approve()
            .get(language=subtitle_language.language_code))
    if task.assignee is None and can_assign_task(task, user):
        task.assignee = user
    elif task.assignee != user:
        raise ValueError("Task not assigned to user")
    task.new_subtitle_version = subtitle_language.get_tip()
    task.approved = approved
    task.complete()
    if saved_version is None:
        if saved_version is None:
            version_id = None
        else:
            version_id = saved_version.id
            video_changed_tasks.delay(team_video.video_id, version_id)

class TaskAction(subtitles.workflows.Action):
    def update_language(self, user, video, subtitle_language, saved_version):
        subtitle_language.subtitles_complete = self.complete
        subtitle_language.save()

class Complete(TaskAction):
    """Used when the initial transcriber/translator completes their work """
    name = 'complete'
    label = ugettext_lazy('Complete')
    in_progress_text = ugettext_lazy('Saving')
    visual_class = 'endorse'
    subtitle_visibility = 'private'
    complete = True
    requires_translated_metadata_if_enabled = True

    def perform(self, user, video, subtitle_language, saved_version):
        try:
            task = (video.get_team_video().task_set
                    .incomplete_subtitle_or_translate()
                    .filter(language=subtitle_language.language_code).get())
        except Task.DoesNotExist:
            # post publish edit, no task is available
            return
        else:
            task.complete()
        _publish_subtitles_if_needed(subtitle_language, saved_version)

class Approve(TaskAction):
    name = 'approve'
    label = ugettext_lazy('Approve')
    in_progress_text = ugettext_lazy('Approving')
    visual_class = 'endorse'
    subtitle_visibility = 'private'
    complete = True
    requires_translated_metadata_if_enabled = True

    def perform(self, user, video, subtitle_language, saved_version):
        _complete_task(user, video, subtitle_language, saved_version,
                       Task.APPROVED_IDS['Approved'])
        _publish_subtitles_if_needed(subtitle_language, saved_version)

class SendBack(TaskAction):
    name = 'send-back'
    label = ugettext_lazy('Send Back')
    in_progress_text = ugettext_lazy('Sending back')
    visual_class = 'send-back'
    subtitle_visibility = 'private'
    complete = False
    requires_translated_metadata_if_enabled = False

    def perform(self, user, video, subtitle_language, saved_version):
        _complete_task(user, video, subtitle_language, saved_version,
                       Task.APPROVED_IDS['Rejected'])
        _publish_subtitles_if_needed(subtitle_language, saved_version)

class TaskSaveDraft(subtitles.workflows.SaveDraft):
    subtitle_visibility = 'private'

class TaskTeamEditorNotes(TeamEditorNotes):
    def __init__(self, team_video, language_code):
        super(TaskTeamEditorNotes, self).__init__(team_video.team,
                                                  team_video.video,
                                                  language_code)
        self.team_video = team_video

    def post(self, user, body):
        note = super(TaskTeamEditorNotes, self).post(user, body)
        email_to = [u for u in self.all_assignees() if u != note.user]
        self.send_messages(note, email_to)
        return note

    def all_assignees(self):
        task_qs = (self.team_video.task_set
                   .filter(language=self.language_code,
                           assignee__isnull=False)
                   .select_related('assignee'))
        return set(task.assignee for task in task_qs)

    def send_messages(self, note, user_list):
        subject = fmt(
            _(u'%(user)s added a note while editing %(title)s'),
            user=unicode(note.user), title=self.video.title_display())

        tasks_url = universal_url('teams:team_tasks', kwargs={
            'slug': self.team.slug,
        })
        filter_query = '?team_video={0}&assignee=anyone&lang={1}'
        filter_query = filter_query.format(self.team_video.pk,
                                           self.language_code)
        data = {
            'note_user': unicode(note.user),
            'body': note.body,
            'tasks_url': tasks_url + filter_query,
            'video': self.video.title_display(),
            'language': translation.get_language_label(self.language_code),
        }
        email_template = ("messages/email/"
                          "task-team-editor-note-notifiction.html")
        message_template = 'messages/task-team-editor-note.html'

        for user in user_list:
            send_templated_email(user, subject, email_template, data,
                                 fail_silently=not settings.DEBUG)

            Message.objects.create(
                user=user, subject=subject, message_type="S",
                content=render_to_string(message_template, data))

class TaskTeamSubtitlesWorkflow(TeamSubtitlesWorkflow):
    def get_work_mode(self, user, language_code):
        task = self.team_video.get_task_for_editor(language_code)
        if task is not None:
            if task.is_approve_task():
                heading = _("Approve")
            elif task.is_review_task():
                heading = _("Review")
            else:
                # get_task_for_editor should only return approve/review tasks
                raise ValueError("Wrong task type: %s" % task)
            help_text = _('Watch the video and verify that the subtitles '
                          'are correct. Click Approve when done, or Save '
                          'Draft to finish later')
            return subtitles.workflows.ReviewWorkMode(heading, help_text)
        else:
            return subtitles.workflows.NormalWorkMode()

    def get_actions(self, user, language_code):
        task = self.team_video.get_task_for_editor(language_code)
        if task is not None:
            # review/approve task
            return [TaskSaveDraft(), SendBack(), Approve()]
        else:
            incomplete_task_qs = (self.team_video.task_set.incomplete()
                                  .filter(language=language_code))
            if incomplete_task_qs.exists():
                # subtitle/translate task
                return [TaskSaveDraft(), Complete()]
            else:
                # post publish edit
                return [subtitles.workflows.Publish()]

    def get_editor_notes(self, user, language_code):
        return TaskTeamEditorNotes(self.team_video, language_code)

    def get_add_language_mode(self, user):
        if self.team_video.team.user_is_member(user):
            return mark_safe(
                fmt(_(
                    '<a class="icon" href="%(url)s">'
                    '<img src="%(static_url)simages/edit-subtitles.png"></a>'
                    'View <a href="%(url)s">tasks for this video</a>.'),
                    url=self.team_video.get_tasks_page_url(),
                    static_url=settings.STATIC_URL))
        else:
            return None

    def action_for_add_subtitles(self, user, language_code, complete):
        tasks = self.team_video.task_set
        if (complete == True and
            tasks.incomplete_subtitle_or_translate().exists()):
            return Complete()
        else:
            return (super(TaskTeamSubtitlesWorkflow, self)
                    .action_for_add_subtitles(user, language_code, complete))

    def delete_subtitles_bullets(self, language_code):
        default_bullets = super(TaskTeamSubtitlesWorkflow,
                                self).delete_subtitles_bullets()
        return default_bullets + [
            _('Any tasks will be deleted'),
        ]

class NonTaskTeamPublish(subtitles.workflows.Publish):
    def perform(self, user, video, subtitle_language, saved_version):
        super(NonTaskTeamPublish, self).perform(
            user, video, subtitle_language, saved_version)
        if saved_version:
            billing_version = saved_version
        else:
            billing_version = subtitle_language.get_tip()
        if billing_version:
            BillingRecord.objects.insert_record(billing_version)

class NonTaskTeamSubtitlesWorkflow(TeamSubtitlesWorkflow):
    def get_actions(self, user, language_code):
        return [subtitles.workflows.SaveDraft(), NonTaskTeamPublish()]
