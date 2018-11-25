# Amara, universalsubtitles.org
#
# Copyright (C) 2018 Participatory Culture Foundation
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

import pytest

from subtitles import pipeline
from teams import experience
from teams.models import TeamSubtitlesCompleted
from utils.factories import *
from utils.test_utils import *

@pytest.fixture
def team():
    return TeamFactory()

@pytest.fixture
def member(team):
    return TeamMemberFactory(team=team)

@pytest.fixture
def video(team):
    return VideoFactory(team=team)

def test_add_subtitles_completed(team, video, member):
    pipeline.add_subtitles(video, 'en', SubtitleSetFactory(),
                           author=member.user)

    subtitles_completed = experience.get_subtitles_completed([member])
    assert subtitles_completed == [1]

def test_same_subtitles(team, video, member):
    # editing the same subtitle set twice should only result in a count of 1
    pipeline.add_subtitles(video, 'en', SubtitleSetFactory(),
                           author=member.user)
    pipeline.add_subtitles(video, 'en', SubtitleSetFactory(),
                           author=member.user)
    subtitles_completed = experience.get_subtitles_completed([member])
    assert subtitles_completed == [1]

def test_multiple_users(team, video, member):
    member2 = TeamMemberFactory(team=team)
    member3 = TeamMemberFactory(team=team)
    pipeline.add_subtitles(video, 'en', SubtitleSetFactory(),
                           author=member.user)
    pipeline.add_subtitles(video, 'en', SubtitleSetFactory(),
                           author=member2.user)
    subtitles_completed = experience.get_subtitles_completed(
        [member, member2, member3])
    assert subtitles_completed == [1, 1, 0]


def test_invalidate_cache(team, video, member):
    # get_subtitles_completed() is cached.  Test that we invalidate the cache
    # correctly when the user creates more subtitles
    pipeline.add_subtitles(video, 'en', SubtitleSetFactory(),
                           author=member.user)
    subtitles_completed = experience.get_subtitles_completed([member])

    pipeline.add_subtitles(video, 'fr', SubtitleSetFactory(),
                           author=member.user)
    # get_subtitles_completed() will still be 1 if we didn't clear the cache
    member = reload_obj(member)
    subtitles_completed = experience.get_subtitles_completed([member])
    assert subtitles_completed == [2]
