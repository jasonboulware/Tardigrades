# Amara, universalsubtitles.org
#
# Copyright (C) 2015 Participatory Culture Foundation
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

from __future__ import absolute_import

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import redirect, render
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from subtitles.models import SubtitleVersion
from teams import views as old_views, forms as teams_forms
from teams.behaviors import get_main_project
from teams.models import Project, Team
from teams.workflows import TeamWorkflow
from ui import CTA, SplitCTA, Link
from utils.memoize import memoize
from utils.breadcrumbs import BreadCrumb
from utils.chunkedqs import chunkedqs, batch_qs
from utils.pagination import AmaraPaginatorFuture
from utils.translation import get_language_label
from .subtitleworkflows import TeamVideoWorkflow
from videos.behaviors import VideoPageCustomization, SubtitlesPageCustomization

from collections import OrderedDict

NEWEST_MEMBERS_PER_PAGE = 10
NEWEST_VIDEOS_PER_PAGE = 7
MAX_DASHBOARD_VIDEOS = 3
MAX_DASHBOARD_HISTORY = 10

# maximum number of videos we want to check to determine
# which videos to display in the dashboard
# this gets the n most recent videos that have available subtitling work for a team member
MAX_DASHBOARD_VIDEOS_TO_CHECK = 10 

class SimpleDashboardVideoView(object):
    def __init__(self, video, team, cta_languages):
        self.video = video
        self.team = team

        '''
        Pop off the first language in the cta_languages list 
        '''
        if (video.language in cta_languages):
            self.main_cta_language = video.language
            cta_languages.remove(video.language)
            self.other_cta_languages = cta_languages
        else:
            self.main_cta_language = cta_languages.pop(0)
            self.other_cta_languages = cta_languages
        
    def editor_url(self, language=None):
        url = reverse('subtitles:subtitle-editor', kwargs={
            'video_id': self.video.video_id,
            'language_code': language if language else self.main_cta_language,
        })
        return url + '?team={}'.format(self.team.slug)

    def _calc_label_for_cta(self, language):
        if self.video.language == language:
            icon = 'icon-transcribe'
            label =  _('Transcribe [{}]').format(language)
        else:
            icon = 'icon-translate'
            label = _('Translate [{}]').format(language)

        return (icon, label)

    """Get a CTA or SplitCTA for this team video"""
    @memoize
    def cta(self):       
        # for dashboard videos with multiple subtitling work available
        main_icon, main_label = self._calc_label_for_cta(self.main_cta_language)
        if self.other_cta_languages:
            dropdown_items = []
            for language in self.other_cta_languages:
                icon, label = self._calc_label_for_cta(language)
                dropdown_items.append((label, self.editor_url(language)))

            return SplitCTA(main_label, self.editor_url(), main_icon, block=True,
                            main_tooltip=_('Click the dropdown button for more available subtitling work!'),
                            menu_id=self.video.video_id + '_dropdown',
                            dropdown_items = dropdown_items)
        else:
            return CTA(main_label, main_icon, self.editor_url(), block=True)

def render_team_header(request, team):
    return render_to_string('future/header.html', {
        'team': team,
        'brand': 'future/teams/brand.html',
        'brand_url': team.get_absolute_url(),
        'primarynav': 'future/teams/primarynav.html',
    }, request)

'''
priority 1 -- videos with transcription work
priority 2 -- videos with translation work
'''
def _calc_dashboard_video_priority(video_view):
    if (video_view.video.language == video_view.main_cta_language or
        video_view.video.language in video_view.other_cta_languages):
        return 1
    else:
        return 2    

def get_dashboard_videos(team, user, main_project):
    user_languages = user.get_languages()
    available_videos = []
    added_videos = 0

    qs = team.videos.exclude(primary_audio_language_code='').order_by('-created')
    if main_project:
        qs = qs.filter(teamvideo__project=main_project)

    for batch in batch_qs(qs, MAX_DASHBOARD_VIDEOS_TO_CHECK * 2):
        for video in batch:
            cta_languages = [l for l in user_languages if l not in video.complete_or_writelocked_language_codes()]

            if (cta_languages):
                available_videos.append(SimpleDashboardVideoView(video, team, cta_languages))
                added_videos += 1
            '''
            Stop looking for videos to display in the dashboard once we reach the maximum
            '''
            if added_videos == MAX_DASHBOARD_VIDEOS_TO_CHECK:
                break
        if added_videos == MAX_DASHBOARD_VIDEOS_TO_CHECK:
            break

    available_videos.sort(key=lambda v: _calc_dashboard_video_priority(v))
    return available_videos[:MAX_DASHBOARD_VIDEOS]

def dashboard(request, team):
    member = team.get_member(request.user)
    main_project = get_main_project(team)
    if not member:
        raise PermissionDenied()

    video_qs = team.videos.all().order_by('-created')
    if main_project:
        video_qs = video_qs.filter(teamvideo__project=main_project)

    newest_members = (team.members.all()
                      .order_by('-created')
                      .select_related('user')[:NEWEST_MEMBERS_PER_PAGE])

    top_languages = [
        (get_language_label(lc), count)
        for lc, count in team.get_completed_language_counts() if count > 0
    ]
    top_languages.sort(key=lambda pair: pair[1], reverse=True)

    member_history = team.new_workflow.fetch_member_history(request.user)
    member_history = member_history[:MAX_DASHBOARD_HISTORY]

    context = {
        'team': team,
        'team_nav': 'dashboard',
        'projects': Project.objects.for_team(team),
        'selected_project': main_project,
        'top_languages': top_languages,
        'newest_members': [m.user for m in newest_members],
        'videos': video_qs[:NEWEST_VIDEOS_PER_PAGE],
        'more_video_count': max(0, video_qs.count() - NEWEST_VIDEOS_PER_PAGE),
        'video_search_form': teams_forms.VideoFiltersForm(team),
        'member_profile_url': member.get_absolute_url(),
        'member_history': member_history,
        'member_history_template': team.new_workflow.member_history_template,
        'no_languages_yet': (False if request.user.is_anonymous 
                             else len(request.user.get_languages()) == 0),
        'dashboard_videos': get_dashboard_videos(team, request.user, main_project),
    }
    
    return render(request, 'future/teams/simple/dashboard.html', context)

class SimpleVideoPageCustomization(VideoPageCustomization):
    def __init__(self, team, request, video):
        self.team = team
        self.request = request
        self.sidebar = None
        self.setup_header()

    def setup_header(self):
        if self.team:
            self.header = render_team_header(self.request, self.team)
        else:
            self.header = None

class SimpleSubtitlesPageCustomization(SubtitlesPageCustomization):
    def __init__(self, request, video, subtitle_language, team):
        super(SimpleSubtitlesPageCustomization, self).__init__(
            request.user, video, subtitle_language, team.slug)
        self.request = request
        self.team = team
        self.setup_header()

    def setup_header(self):
        if self.team:
            self.header = render_team_header(self.request, self.team)
        else:
            self.header = None

class SimpleTeamWorkflow(TeamWorkflow):
    """Workflow for basic public/private teams

    This class implements a basic workflow for teams:  Members can edit any
    subtitles, non-members can't edit anything.
    """

    type_code = 'S'
    label = _('Simple')
    api_slug = 'simple'
    
    dashboard_view = staticmethod(dashboard)

    def get_subtitle_workflow(self, team_video):
        """Get the SubtitleWorkflow for a video with this workflow.  """
        return TeamVideoWorkflow(team_video)

    # simple teams don't have a workflow settings page anymore
    def workflow_settings_view(self, request, team):
        raise Http404

    def video_page_customize(self, request, video):
        team = self.find_team_for_page(request)
        return SimpleVideoPageCustomization(team, request, video)

    def subtitles_page_customize(self, request, video, subtitle_language):
        team = self.find_team_for_page(request)
        return SimpleSubtitlesPageCustomization(request, video, subtitle_language, team)

    def find_team_for_page(self, request):
        slug = request.GET.get('team')
        if slug == self.team.slug:
            team = self.team
        else:
            try:
                team = Team.objects.get(slug=slug)
            except Team.DoesNotExist:
                return None
        return team
