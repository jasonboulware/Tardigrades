# Amara, universalsubtitles.org
# 
# Copyright (C) 2014 Participatory Culture Foundation
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

"""task_settings -- settings for periodic tasks."""

from datetime import timedelta

# Tasks that we schedule using rq-schedule
REPEATING_JOBS = [
    {
        'job': 'auth.tasks.expire_login_tokens',
        'crontab': dict(minute=10, hour=23),
    },
    {
        'job': 'teams.tasks.add_videos_notification_daily',
        'crontab': dict(minute=0, hour=23),
    },
    {
        'job': 'teams.tasks.add_videos_notification_hourly',
        'crontab': dict(minute=0),
    },
    {
        'job': 'teams.tasks.expire_tasks',
        'crontab': dict(minute=0, hour=7),
    },
    {
        'job': 'videos.tasks.cleanup',
        'crontab': dict(hour=3, day_of_week=1),
    },
    {
        'job': 'externalsites.tasks.retry_failed_sync',
        'period': timedelta(seconds=10),
    },
    {
        'job': 'notifications.tasks.prune_notification_history',
        'crontab': dict(hour=0),
    },
]

__all__ = ['REPEATING_JOBS']
