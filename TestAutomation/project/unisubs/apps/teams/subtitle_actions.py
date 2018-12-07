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

from django.utils.translation import ugettext_lazy

from subtitles.actions import Action, get_actions
from teams.models import Task
from utils.behaviors import DONT_OVERRIDE
from videos.tasks import video_changed_tasks

class Complete(Action):
    """Used when the initial transcriber/translator completes their work """
    name = 'complete'
    label = ugettext_lazy('Complete')
    in_progress_text = ugettext_lazy('Saving')
    visual_class = 'endorse'
    complete = True
    requires_translated_metadata_if_enabled = True

    def handle(self, user, video, language_code, saved_version):
        if saved_version is not None:
            # I think the cleanest way to handle things would be to create the
            # review/approve task now but there is already code in
            # subtitles.pipeline to do that.  It would be nice to move that
            # code out of that app and into here, but maybe we should just
            # leave it and wait to phase the tasks system out
            return
        task = (video.get_team_video().task_set
                .incomplete_subtitle_or_translate()
                .filter(language=language_code).get())
        task.complete()

def _complete_task(user, video, language_code, saved_version, approved):
    team_video = video.get_team_video()
    subtitle_language = video.subtitle_language(language_code)
    task = (team_video.task_set
            .incomplete_review_or_approve()
            .get(language=language_code))
    if task.assignee is None:
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

class Approve(Action):
    name = 'approve'
    label = ugettext_lazy('Approve')
    in_progress_text = ugettext_lazy('Approving')
    visual_class = 'endorse'
    complete = True
    requires_translated_metadata_if_enabled = True

    def handle(self, user, video, language_code, saved_version):
        _complete_task(user, video, language_code, saved_version,
                       Task.APPROVED_IDS['Approved'])

class SendBack(Action):
    name = 'send-back'
    label = ugettext_lazy('Send Back')
    in_progress_text = ugettext_lazy('Sending back')
    visual_class = 'send-back'
    complete = False
    requires_translated_metadata_if_enabled = False

    def handle(self, user, video, language_code, saved_version):
        _complete_task(user, video, language_code, saved_version,
                       Task.APPROVED_IDS['Rejected'])

@get_actions.override
def task_team_get_actions(user, video, language_code):
    team_video = video.get_team_video()
    if team_video is None or not team_video.team.is_tasks_team():
        return DONT_OVERRIDE
    task = team_video.get_task_for_editor(language_code)
    if task is not None:
        # review/approve task
        return [SendBack(), Approve()]
    else:
        # subtitle/translate task
        return [Complete()]
