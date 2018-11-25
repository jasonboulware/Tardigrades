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

from django.core.management.base import BaseCommand
from django.db import connection

SQL_STATEMENT = """\
INSERT INTO teams_teamsubtitlescompleted (video_id, member_id, language_code)
SELECT video.id, member.id, version.language_code
FROM subtitles_subtitleversion AS version
JOIN videos_video AS video ON video.id=version.video_id
JOIN teams_teammember AS member ON member.user_id=version.author_id
ON DUPLICATE KEY UPDATE teams_teamsubtitlescompleted.language_code=teams_teamsubtitlescompleted.language_code
"""

class Command(BaseCommand):
    """
    Add missing member experience
    """

    def handle(self, **options):
        with connection.cursor() as cursor:
            cursor.execute(SQL_STATEMENT)

