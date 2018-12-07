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
"""Data creation and retrieval functions for the video tests."""

from babelsubs.storage import SubtitleLine
from auth.models import CustomUser as User
from videos.models import Video
from subtitles import pipeline
from subtitles.models import SubtitleLanguage
from teams.models import Team, TeamMember, TeamVideo, Workflow
from teams.permissions_const import (
    ROLE_OWNER, ROLE_ADMIN, ROLE_MANAGER, ROLE_CONTRIBUTOR
)
from utils.factories import *

# Normal Users ----------------------------------------------------------------
def get_user(n=1):
    username = 'test_user_%s' % n
    email = "test_user_%s@example.com" % n
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User.objects.create(
            username=username, email=email,
            is_active=True, is_superuser=False, is_staff=False,
            password="sha1$6b3dc$72c6a16f127d2c217f72009632c745effef7eb3f",
        )
        user.set_password('password')
        user.save()
    return user


# Site Admins -----------------------------------------------------------------
def get_site_admin(n=1):
    username = 'test_admin_%s' % n
    email = "test_admin_%s@example.com" % n
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User.objects.create(
            username=username, email=email,
            is_active=True, is_superuser=True, is_staff=True,
            password="sha1$6b3dc$72c6a16f127d2c217f72009632c745effef7eb3f",
        )
    return user


# Videos ----------------------------------------------------------------------
VIDEO_URLS = ('http://youtu.be/heKK95DAKms',
              'http://youtu.be/e4MSN6IImpI',
              'http://youtu.be/i_0DXxNeaQ0',)

def get_video(n=1, user=None, url=None):
    if not url:
        url = VIDEO_URLS[n]
    return Video.add(url, user)[0]

# Subtitle Languages ----------------------------------------------------------
def make_subtitle_language(video, language_code):
    sl = SubtitleLanguage(video=video, language_code=language_code)
    sl.save()
    return sl


# Subtitle Versions -----------------------------------------------------------
def make_subtitle_lines(count, is_synced=True):
    lines = []
    for line_num in xrange(0, count):
        lines.append(SubtitleLine(
            line_num * 1000 if is_synced else None,
            line_num * 1000 + 900 if is_synced else None,
            "%s" % line_num,
            {}
        ))
    return lines

def make_subtitle_version(subtitle_language, subtitles=[], author=None,
                          parents=None, committer=None, complete=None,
                          title=None, description=None, created=None,note=None):
    committer = committer or author
    return pipeline.add_subtitles(subtitle_language.video,
                                  subtitle_language.language_code,
                                  subtitles,
                                  author=author,
                                  parents=parents,
                                  committer=committer,
                                  complete=complete,
                                  title=title,
                                  created=created,
                                  note=note,
                                  description=description)

def make_rollback_to(subtitle_language, version_number):
    return pipeline.rollback_to(subtitle_language.video,
                                subtitle_language.language_code,
                                version_number)


# Teams -----------------------------------------------------------------------
def get_team(n=1, reviewers='', approvers=''):
    slug = 'test_team_%s' % n
    try:
        team = Team.objects.get(slug=slug)
    except Team.DoesNotExist:
        team = Team.objects.create(name='Test Team %s' % n,
                                   slug=slug)

        if reviewers or approvers:
            reviewers = reviewers.rstrip('s')
            approvers = approvers.rstrip('s')

            review = {'peer': 10, 'manager': 20, 'admin': 30}.get(reviewers, 00)
            approve = {'manager': 10, 'admin': 20}.get(approvers, 00)

            Workflow.objects.create(team=team, review_allowed=review,
                                    approve_allowed=approve)

            team.workflow_enabled = True
            team.save()

    return team

def get_team_member(user, team, role='contributor'):
    try:
        tm = TeamMember.objects.get(user=user, team=team)
    except TeamMember.DoesNotExist:
        role = {
            'contributor': ROLE_CONTRIBUTOR,
            'manager': ROLE_MANAGER,
            'admin': ROLE_ADMIN,
            'owner': ROLE_OWNER,
        }.get(role)
        tm = TeamMember.objects.create(user=user, team=team, role=role)

    return tm

def get_team_video(video, team, user):
    try:
        tv = TeamVideo.objects.get(video=video, team=team)
    except TeamVideo.DoesNotExist:
        tv = TeamVideo.objects.create(video=video, team=team, added_by=user)

    return tv
