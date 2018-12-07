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

from django.core.management.base import BaseCommand

from utils.chunkedqs import chunkedqs
from videos.models import Video
from videos import tasks

class Command(BaseCommand):
    help = "Download video thumbnails and upload them to s3"

    def handle(self, *args, **options):
        qs = Video.objects.filter(s3_thumbnail='').exclude(thumbnail='')
        for video in chunkedqs(qs):
            print video.video_id
            tasks.save_thumbnail_in_s3.delay(video.id)
