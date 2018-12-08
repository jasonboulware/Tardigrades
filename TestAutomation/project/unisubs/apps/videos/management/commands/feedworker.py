#!/usr/bin/env python
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

from optparse import make_option
import logging
import multiprocessing
import signal
import sys
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from externalsites.models import YouTubeAccount
from videos.models import VideoFeed

logger = logging.getLogger(__name__)

def commit():
    connection.cursor().execute('COMMIT')

class Command(BaseCommand):
    """
    Long-running process that updates our video feeds
    """

    def add_arguments(self, parser):
        parser.add_argument('-w', '--workers', default=4, type=int)

    def handle(self, *args, **options):
        self.pool = multiprocessing.Pool(options['workers'], init_worker)
        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)
        self.loop()

    def loop(self):
        while True:
            tasks = self.fetch_tasks()
            while not tasks:
                logger.info('no tasks to run, sleeping for 30 seconds')
                time.sleep(30)
                tasks = self.fetch_tasks()
            seconds_per_task = (float(settings.FEEDWORKER_PASS_DURATION) /
                                len(tasks))
            for task in tasks:
                task.schedule(self.pool)
                time.sleep(seconds_per_task)

    def fetch_tasks(self):
        video_feeds = VideoFeed.objects.values_list('id', flat=True)
        youtube_accounts = (YouTubeAccount.objects
                            .accounts_to_import()
                            .values_list('id', flat=True))
        tasks = []
        tasks.extend(
            Task(update_video_feed, feed_id)
            for feed_id in video_feeds
        )
        tasks.extend(
            Task(update_youtube_account, account_id)
            for account_id in youtube_accounts
        )
        commit()
        return tasks

    def terminate(self, signum, frame):
        logger.info('terminating')
        sys.stdout.flush()
        self.pool.close()
        self.pool.join()
        raise SystemExit(1)

class Task(object):
    """Container for a single task that we perform."""
    def __init__(self, func, *args):
        self.func = func
        self.args = args

    def schedule(self, pool):
        pool.apply_async(self.func, args=self.args)

def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def update_video_feed(feed_id):
    try:
        video_feed = VideoFeed.objects.get(pk=feed_id)
        video_feed.update()
    except VideoFeed.DoesNotExist:
        logger.info('update_video_feed: VideoFeed does not exist. '
                    'ID: %s'.format(feed_id))
    else:
        logger.info('Updated {}'.format(video_feed))
    commit()
    sys.stdout.flush()

def update_youtube_account(account_id):
    try:
        account = YouTubeAccount.objects.get(id=account_id)
        account.import_videos()
    except YouTubeAccount.DoesNotExist:
        logger.info("update_youtube_account: "
              "YouTubeAccount.DoesNotExist ({})".format(account_id))
    else:
        logger.info('Imported {}'.format(account))
    commit()
    sys.stdout.flush()

if __name__ == "__main__":
    main()
