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

"""
teams.stats -- Track team stats

We use redis to count various team stats like videos added, subtitles added,
members added, etc.  For each stat, we track a per-day count.  This lets us
add up days to get counts for yesterday, last week, last month, etc.

Each team gets a hash that maps stat names/dates to counts.  We also store a
set containing all hashes stored.

Periodically, we call cleanup_counters() to cleanup counts older than 45 days.
"""

from collections import namedtuple, defaultdict
from datetime import datetime, timedelta

from django.core.cache import cache
from django_redis import get_redis_connection

from utils import dates

DAYS_TO_STORE = 45

class StatSums(object):
    def __init__(self, today=0, yesterday=0, last_week=0, last_month=0):
        self.today = today
        self.yesterday = yesterday
        self.last_week = last_week
        self.last_month = last_month

    def __repr__(self):
        return u'StatSums({}, {}, {}, {})'.format(self.today, self.yesterday, self.last_week,
                                              self.last_month)

    def __eq__(self, other):
        return (
            self.today == other.today and
            self.yesterday == other.yesterday and
            self.last_week == other.last_week and
            self.last_month == other.last_month)

TRACKING_SET_KEY = 'teamstats:keys'
def calc_hash_name(team):
    return 'teamstats:{}'.format(team.id)

def calc_hash_key(name, dt):
    return '{}:{}-{}-{}'.format(name, dt.year, dt.month, dt.day)

def cache_key(team):
    return 'teamstats:{}'.format(team.id)

def parse_hash_key(key):
    """
    Convert a hash key into a (stat_name, datetime) tuple
    """
    name, _, datestr = key.partition(':')
    return name, datetime(*(int(part) for part in datestr.split('-')))

def increment(team, name):
    """
    Increment a team stat.
    """
    r = get_redis_connection('storage')
    hash_name = calc_hash_name(team)
    hash_key = calc_hash_key(name, dates.now())

    pipe = r.pipeline()
    pipe.hincrby(hash_name, hash_key, 1)
    pipe.sadd(TRACKING_SET_KEY, hash_name)
    pipe.execute()

def get_stats(team):
    """
    Get all current stats for a team

    Returns: dict mapping stat names to Counts objects
    """


    cached = cache.get(cache_key(team))
    if cached:
        return cache_deserialize(cached)

    now = dates.now()
    stats = defaultdict(StatSums)
    r = get_redis_connection('storage')

    all_counts = r.hgetall(calc_hash_name(team))
    for key, count in all_counts.items():
        count = int(count)
        name, dt = parse_hash_key(key)
        date_delta = now - dt
        # note that we're still in the process of recording stats for today,
        # so stats get offset by 1.  "last_week" means "between 1 and 8 days
        # ago"
        if date_delta.days == 0:
            stats[name].today += count
        elif date_delta.days == 1:
            stats[name].yesterday += count
            stats[name].last_week += count
            stats[name].last_month += count
        elif date_delta.days < 8:
            stats[name].last_week += count
            stats[name].last_month += count
        elif date_delta.days < 31:
            stats[name].last_month += count

    stats = dict(stats) # convert defaultdict to a normal dict
    cache.set(cache_key(team), cache_seralize(stats), cache_timeout(now))
    return stats

def cache_seralize(stats):
    return {
        name: (sums.today, sums.yesterday, sums.last_week, sums.last_month)
        for name, sums in stats.items()
    }

def cache_deserialize(cached):
    return {
        name: StatSums(*sums)
        for name, sums in cached.items()
    }

def cache_timeout(now):
    next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0,
                                                 microsecond=0)
    return (next_day - now).total_seconds()

def cleanup_counters():
    now = dates.now()
    r = get_redis_connection('storage')
    for hash_name in r.sscan_iter(TRACKING_SET_KEY):
        cleanup_counter(r, hash_name, now)

def cleanup_counter(r, hash_name, now):
    all_keys = r.hkeys(hash_name)
    cutoff = now - timedelta(days=DAYS_TO_STORE)

    # delete old keys from the hash
    pipe = r.pipeline()
    for key in all_keys:
        name, dt = parse_hash_key(key)
        if dt < cutoff:
            pipe.hdel(hash_name, key)
    pipe.execute()

    # If we deleted all keys from the hash, then redis deletes the hash key.
    # If it did that, also delete the key from our tracking set.  Use a lua
    # script to make this all atomic.
    r.eval("if redis.call('exists', KEYS[2]) == 0 then redis.call('srem', KEYS[1], KEYS[2]) end",
           2, TRACKING_SET_KEY, hash_name)

__all__ = [
    'increment', 'get_stats', 'cleanup_counters', 'StatSums',
]
