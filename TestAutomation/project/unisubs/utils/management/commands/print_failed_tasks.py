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

from django_rq import get_failed_queue

MAX_JOBS = 100

class Command(BaseCommand):
    """
    Print out info on failed RQ tasks to stdout

    If there are no tasks, then we don't print anything.
    """


    def handle(self, **options):
        failed_jobs = list(get_failed_queue().jobs)
        if failed_jobs:
            print 'You have tasks in the failed queue:'
            print
        for job in failed_jobs[:MAX_JOBS]:
            print job.func_name
        if len(failed_jobs) > MAX_JOBS:
            print
            print '... {} more failed jobs'.format(
                len(failed_jobs) - MAX_JOBS)
