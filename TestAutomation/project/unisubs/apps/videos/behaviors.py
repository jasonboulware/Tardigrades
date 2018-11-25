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

from collections import namedtuple

from django.utils.translation import ugettext as _

from utils.behaviors import behavior
from ui import CTA

@behavior
def get_video_subtitle(video, metadata):
    return metadata.get('speaker-name')

class VideoPageCustomization(object):
    def __init__(self, sidebar, header, team):
        self.sidebar = sidebar
        self.header = header
        self.team = team

@behavior
def video_page_customize(request, video):
    """Customize the video page.

    Note: this is already overridden by the team.workflows package.  If you
    want to override the page by team, then check out the TeamWorkflow class.
    """
    return VideoPageCustomization(None, None, None)

class SubtitlesPageCustomization(object):
    """
    Base class for customizing the subtitles page.

    To customize the subtitles page, create a subclass of this then make sure
    it gets returned from the subtitles_page_customize() behavior.
    subtitles_page_customize() is already overridden by the team.workflows
    package.  The simplest way to customize the page is probably using the
    TeamWorkflow class.

    Attrs:
        steps: list of SubtitlesStep objects to display in the top-right
            section
        cta: CTA object to display underneath the steps
        due_date: Due date for the CTA
        header: HTML to display in the header
        team: team context to show.  We include activity private to this team
            when showing activity records
        extra_page_controls: Extra links to display in the page control
            area for site admins
    """
    def __init__(self, user, video, subtitle_language, team_slug=None):
        self.steps = None
        self.due_date = None
        self.header = None
        self.team = None
        self.extra_page_controls = []

        workflow = video.get_workflow()
        is_user_able_to_edit_subtitles = workflow.user_can_edit_subtitles(user, subtitle_language.language_code)
        if is_user_able_to_edit_subtitles and team_slug is not None:
            self.cta = CTA(_("Edit Subtitles"), 'icon-edit',
                           'subtitles:subtitle-editor',
                           video_id=video.video_id,
                           language_code=subtitle_language.language_code,
                           query={'team': team_slug},)
        elif is_user_able_to_edit_subtitles:
            self.cta = CTA(_("Edit Subtitles"), 'icon-edit',
                           'subtitles:subtitle-editor',
                           video_id=video.video_id,
                           language_code=subtitle_language.language_code,)
        else:
            self.cta = None


@behavior
def subtitles_page_customize(request, video, subtitle_language):
    """Customize the subtitles page.

    """
    try:
        team_slug = request.GET.get('team', None)
    except KeyError:
        team_slug = None

    return SubtitlesPageCustomization(request.user, video, subtitle_language, team_slug)


class SubtitlesStep(object):
    """Represents an item on the subtitle steps list

    These are displayed on the top-right of the subtitles page.  By default,
    we don't display anything.  They are used in more complex workflows like
    the collab model.  To set this up, override the subtitles_page_customize()
    function which can be done from the TeamWorkflow class.

    Attrs:
        label: text that describes the step (Subtitle, Review, Approve, etc).
        status: text that describes the progress on the step (In progress,
           Complete, etc).
        icon: icon that represents the step
        user: user icon to display in the step.  If present, the avatar for
            this user is displayed instead of the icon.
        team: team icon to display in the step.  If present, the icon for
            this team is displayed instead of the icon.
        current: Is this step currently in-progress?
    """
    def __init__(self, label, status, icon=None, user=None, team=None,
                 current=False):
        self.label = label
        self.status = status
        self.icon = icon
        self.user = user
        self.team = team
        self.current = current
        self.member = team.get_member(user) if (team and user) else None

Button = namedtuple('Button', 'url label')
