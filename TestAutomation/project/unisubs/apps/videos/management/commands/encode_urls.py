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

from utils.url_escape import url_escape
from videos.models import VideoUrl
from videos.types.htmlfive import HtmlFiveVideoType
from videos.types.flv import FLVVideoType
from videos.types.mp3 import Mp3VideoType

class Command(BaseCommand):
    help = "Percent-encode Video URLs if needed"

    def handle(self, **options):
        count_processed = 0
        count_changed = 0
        direct_file_types = [HtmlFiveVideoType.abbreviation,
                             FLVVideoType.abbreviation,
                             Mp3VideoType.abbreviation]
        for video_url in VideoUrl.objects.filter(type__in=direct_file_types):
            escaped_url = url_escape(video_url.url)
            if escaped_url != video_url.url:
                video_url.url = escaped_url
                video_url.save()
                count_changed += 1
            count_processed += 1
            if count_processed % 1000 == 0:
                print "processed {} video URLs, converted {}".format(count_processed, count_changed)
        print "processed {} video URLs, converted {}".format(count_processed, count_changed)
