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

from django.core.management.base import BaseCommand

from videos.models import Video
import time

class Command(BaseCommand):
    help = "Recalculate the search index for all videos"
    def add_arguments(self, parser):
        parser.add_argument('-b', '--batch-size', dest='batch-size', default=100,
                    help='Set amount of videos to update at once'),
        parser.add_argument('-l', '--rate-limit', dest='rate-limit', metavar='COUNT',
                    help='Only update COUNT videos per second')

    def handle(self, **options):
        batch_size = options['batch-size']
        if options['rate-limit']:
            rate_limit = float(options['rate-limit'])
        else:
            rate_limit = None
        start_time = time.time()
        last_id = -1
        count = 0
        while True:
            if last_id:
                qs = Video.objects.filter(id__gt=last_id)
            else:
                qs = Video.objects.all()
            qs = qs.order_by('id')[:batch_size]
            videos = list(qs)
            if not videos:
                break
            for video in videos:
                video.update_search_index()
                last_id = max(last_id, video.id)
                count += 1
            current_time = time.time()
            rate = count / (current_time - start_time)
            self.stdout.write('indexed {} videos ({:.2f} videos/sec last_id: {})\n'.format(
                count, rate, last_id))
            self.stdout.flush()
            if rate_limit is not None and rate > rate_limit:
                time.sleep((count / rate_limit) - (current_time - start_time))
