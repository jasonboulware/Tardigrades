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

from optparse import make_option
import sys

from django.core.management.base import BaseCommand

from teams.models import Team
from videos.models import Video
import time

class Command(BaseCommand):
    help = "Recreate thumbnails for videos"

    def add_arguments(self, parser):
        parser.add_argument('target', help='Team, Video ID, or "all"')

    def handle(self, **options):
        for video in self.lookup_videos(options['target']):
            try:
                video.s3_thumbnail.recreate_all_thumbnails()
                print video.title_display()
            except:
                print '* {}'.format(video.title_display())

    def lookup_videos(self, target):
        if target == 'all':
            return Video.objects.all()
        try:
            # First try looking up videos by team slug
            team = Team.objects.get(slug=target)
            return team.videos.all()
        except Team.DoesNotExist:
            # Fall back to Video ID
            return Video.objects.filter(video_id=target)
