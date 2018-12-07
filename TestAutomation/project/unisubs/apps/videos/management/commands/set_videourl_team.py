# Amara, universalsubtitles.org
#
# Copyright (C) 2017 Participatory Culture Foundation
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

from django.core.management.base import BaseCommand

from django.db import connection

class Command(BaseCommand):
    help = "Update the VideoUrl.team column"

    def handle(self, **options):
        cursor = connection.cursor()
        rows_updated = 0
        # update team videos
        rows_updated += cursor.execute(
            'UPDATE videos_videourl vurl '
            'LEFT JOIN teams_teamvideo tv '
            'ON tv.video_id=vurl.video_id '
            'SET vurl.team_id=tv.team_id '
            'WHERE tv.id IS NOT NULL AND '
            'vurl.team_id != tv.team_id')
        # update non-team videos
        rows_updated += cursor.execute(
            'UPDATE videos_videourl vurl '
            'LEFT JOIN teams_teamvideo tv '
            'ON tv.video_id=vurl.video_id '
            'SET vurl.team_id=0 '
            'WHERE tv.id IS NULL AND '
            'vurl.team_id != 0')
        cursor.execute("COMMIT")
        print('{} rows updated'.format(rows_updated))
