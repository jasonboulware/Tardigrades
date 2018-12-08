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

from videos.models import VideoUrl

class Command(BaseCommand):
    help = "Set the url_hash field for video URLS"

    def handle(self, **options):
        count = 0
        for video_url in VideoUrl.objects.filter(url_hash=''):
            # saving auto-creates the url_hash
            video_url.save()
            count += 1
            if count % 100 == 0:
                print "processed {} video URLs".format(count)
        print "processed {} video URLs ({} left)".format(
            count, VideoUrl.objects.filter(url_hash='').count())
